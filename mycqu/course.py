"""课程相关的模块
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, List, Union, ClassVar
# from pydantic.dataclasses import dataclass
import re
from datetime import date
from functools import lru_cache
from requests import Session, get
from ._lib_wrapper.dataclass import dataclass
from .utils.datetimes import parse_period_str, parse_weeks_str, parse_weekday_str, date_from_str
from .exception import MycquUnauthorized

__all__ = ("CQUSession", "CQUSessionInfo",
           "CourseTimetable", "CourseDayTime", "Course")

CQUSESSIONS_URL = "https://my.cqu.edu.cn/api/timetable/optionFinder/session?blankOption=false"
CUR_SESSION_URL = "https://my.cqu.edu.cn/api/resourceapi/session/cur-active-session"
ALL_SESSIONSINFO_URL = "https://my.cqu.edu.cn/api/resourceapi/session/list"
TIMETABLE_URL = "https://my.cqu.edu.cn/api/timetable/class/timetable/student/table-detail"


def get_course_raw(session: Session, code: str, cqu_session: Optional[Union[CQUSession, str]] = None):
    """从 my.cqu.edu.cn 上获取学生或老师的课表

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    :param code: 学生或教师的学工号
    :type code: str
    :param cqu_session: 需要获取课表的学期，留空获取当前年级的课表
    :type cqu_session: Optional[Union[CQUSession, str]], optional
    :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 进行认证
    :return: 反序列化获取课表的json
    :rtype: dict
    """
    if cqu_session is None:
        cqu_session = CQUSessionInfo.fetch(session).session
    elif isinstance(cqu_session, str):
        cqu_session = CQUSession.from_str(cqu_session)
    assert isinstance(cqu_session, CQUSession)
    resp = session.post(TIMETABLE_URL,
                        params={"sessionId": cqu_session.get_id()},
                        json=[code],
                        )
    if resp.status_code == 401:
        raise MycquUnauthorized()
    return resp.json()['classTimetableVOList']


@dataclass(order=True, frozen=True)
class CQUSession:
    """重大的某一学期
    """
    year: int
    """主要行课年份"""
    is_autumn: bool
    """是否为秋冬季学期"""
    SESSION_RE: ClassVar = re.compile("^([0-9]{4})年?(春|秋)$")
    _SPECIAL_IDS: ClassVar[Tuple[int, ...]] = (
        239259, 102, 101, 103, 1028, 1029, 1030, 1032)  # 2015 ~ 2018

    @lru_cache(maxsize=32)  # type: ignore
    def __new__(cls, year: int, is_autumn: bool):  # pylint: disable=unused-argument
        return super(CQUSession, cls).__new__(cls)

    def __str__(self):
        return str(self.year) + ('秋' if self.is_autumn else '春')

    def get_id(self) -> int:
        """获取该学期在 my.cqu.edu.cn 中的 id

        >>> CQUSession(2021, True).get_id()
        1038

        :return: 学期的 id
        :rtype: int
        """
        if self.year >= 2019:
            return (self.year - 1503) * 2 + int(self.is_autumn) + 1
        elif 2015 <= self.year <= 2018:
            return self._SPECIAL_IDS[(self.year - 2015) * 2 + int(self.is_autumn)]
        else:
            return (2015 - self.year) * 2 - int(self.is_autumn)

    @staticmethod
    def from_str(string: str) -> CQUSession:
        """从学期字符串中解析学期

        >>> CQUSession.from_str("2021春")
        CQUSession(year=2021, is_autumn=False)
        >>> CQUSession.from_str("2020年秋")
        CQUSession(year=2020, is_autumn=True)

        :param string: 学期字符串，如“2021春”、“2020年秋”
        :type string: str
        :raises ValueError: 字符串不是一个预期中的学期字符串时抛出
        :return: 对应的学期
        :rtype: CQUSession
        """
        match = CQUSession.SESSION_RE.match(string)
        if match:
            return CQUSession(
                year=match[1],
                is_autumn=match[2] == "秋"
            )
        else:
            raise ValueError(f"string {string} is not a session")

    @staticmethod
    def fetch() -> List[CQUSession]:
        """从 my.cqu.edu.cn 上获取各个学期

        :return: 各个学期组成的列表
        :rtype: List[CQUSession]
        """
        session_list = []
        for session in get(CQUSESSIONS_URL).json():
            session_list.append(CQUSession.from_str(session["name"]))
        return session_list


@dataclass
class CQUSessionInfo:
    """某学期的一些额外信息
    """
    session: CQUSession
    """对应的学期"""
    begin_date: date
    """学期的开始日期"""
    end_date: date
    """学期的结束日期"""

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CQUSessionInfo:
        """从反序列化的（一个）学期信息 json 中获取学期信息

        :param data: json 反序列化得到的字典
        :type data: dict[str, Any]
        :return: 学期信息对象
        :rtype: CQUSessionInfo
        """
        return CQUSessionInfo(
            session=CQUSession(year=data["year"],
                               is_autumn=data["term"] == "秋"),
            begin_date=date_from_str(data["beginDate"]),
            end_date=date_from_str(data["endDate"])
        )

    @staticmethod
    def fetch_all(session: Session) -> List[CQUSessionInfo]:
        """获取所有学期信息

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
        :type session: Session
        :return: 按时间降序排序的学期（最新学期可能尚未到来，其信息准确度也无法保障！）
        :rtype: List[CQUSessionInfo]
        """
        resp = session.get(ALL_SESSIONSINFO_URL)
        if resp.status_code == 401:
            raise MycquUnauthorized()
        cqusesions: List[CQUSessionInfo] = []
        for data in resp.json()['sessionVOList']:
            if not data['beginDate']:
                break
            cqusesions.append(CQUSessionInfo.from_dict(data))
        return cqusesions

    @staticmethod
    def fetch(session: Session) -> CQUSessionInfo:
        """从 my.cqu.edu.cn 上获取当前学期的学期信息，需要登录并认证了 mycqu 的会话

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
        :type session: Session
        :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 认证
        :return: 本学期信息对象
        :rtype: CQUSessionInfo
        """
        resp = session.get(CUR_SESSION_URL)
        if resp.status_code == 401:
            raise MycquUnauthorized()
        return CQUSessionInfo.from_dict(resp.json()["data"])


@dataclass
class CourseDayTime:
    """课程一次的星期和节次
    """
    weekday: int
    """星期，0 为周一，6 为周日，此与 :attr:`datetime.date.day` 一致"""
    period: Tuple[int, int]
    """节次，第一个元素为开始节次，第二个元素为结束节次（该节次也包括在范围内）。
    只有一节课时，两个元素相同。
    """

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Optional[CourseDayTime]:
        """从反序列化的（一个）课表 json 中获取课程的星期和节次

        :param data: 反序列化成字典的课表 json
        :type data: Dict[str, Any]
        :return: 若其中有课程的星期和节次则返回相应对象，否则返回 :obj:`None`
        :rtype: Optional[CourseDayTime]
        """
        if data.get("periodFormat") and data.get("weekDayFormat"):
            return CourseDayTime(
                weekday=parse_weekday_str(data["weekDayFormat"]),
                period=parse_period_str(data["periodFormat"])
            )
        return None


@dataclass
class Course:
    """与具体行课时间无关的课程信息
    """
    name: str
    """课程名称"""
    code: str
    """课程代码"""
    course_num: Optional[str]
    """教学班号，在无法获取时（如考表 :class:`.exam.Exam` 中）设为 :obj:`None`"""
    dept: Optional[str]
    """开课学院， 在无法获取时（如成绩 :class:`.score.Score`中）设为 :obj:`None`"""
    credit: Optional[float]
    """学分，无法获取到则为 :obj:`None`（如在考表 :class:`.exam.Exam` 中）"""
    instructor: Optional[str]
    """教师"""
    session: Optional[CQUSession]
    """学期，无法获取时则为 :obj:`None`"""

    @staticmethod
    def from_dict(data: Dict[str, Any],
                  session: Optional[Union[str, CQUSession]] = None) -> Course:
        """从反序列化的（一个）课表或考表 json 中返回课程

        :param data: 反序列化成字典的课表或考表 json
        :type data: Dict[str, Any]
        :param session: 学期字符串或学期对象，留空则尝试从 ``data`` 中获取
        :type session: Optional[Union[str, CQUSession]], optional
        :return: 对应的课程对象
        :rtype: Course
        """
        if session is None and not data.get("session") is None:
            session = CQUSession.from_str(data["session"])
        if isinstance(session, str):
            session = CQUSession.from_str(session)
        assert isinstance(session, CQUSession) or session is None

        instructor_name = data.get("instructorName") if data.get("instructorName") is not None else \
            ', '.join(instructor.get('instructorName')
                      for instructor in data.get('classTimetableInstrVOList'))

        return Course(
            name=data["courseName"],
            code=data["courseCode"],
            course_num=data.get("classNbr"),
            dept=data.get(
                "courseDepartmentName") or data.get("courseDeptShortName"),
            credit=data.get("credit") or data.get("courseCredit"),
            instructor=instructor_name,
            session=session,
        )


@dataclass
class CourseTimetable:
    """课表对象，一个对象存储有相同课程、相同行课节次和相同星期的一批行课安排
    """
    course: Course
    """对应的课程"""
    stu_num: Optional[int]
    """学生数"""
    classroom: Optional[str]
    """行课地点，无则为 :obj:`None`"""
    weeks: List[Tuple[int, int]]
    """行课周数，列表中每个元组 (a,b) 代表一个周数范围 a~b（包含 a, b），在单独的一周则有 b=a"""
    day_time: Optional[CourseDayTime]
    """行课的星期和节次，若时间是整周（如真实地占用整周的军训和某些实习、虚拟地使用一周的思修实践）
    则为 :obj:`None`"""
    whole_week: bool
    """是否真实地占用整周（如军训和某些实习是真实地占用、思修实践是“虚拟地占用”）"""
    classroom_name: Optional[str]
    """行课教室名称"""
    expr_projects: List[str]
    """实验课各次实验内容"""

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> CourseTimetable:
        """从反序列化的一个课表 json 中获取课表

        :param data: 反序列化成字典的课表 json
        :type data: Dict[str, Any]
        :return: 课表对象
        :rtype: CourseTimetable
        """
        return CourseTimetable(
            course=Course.from_dict(data),
            stu_num=data.get("selectedStuNum"),
            classroom=data.get("position"),
            weeks=parse_weeks_str(data.get("weeks")
                                  or data.get("teachingWeekFormat")),  # type: ignore
            day_time=CourseDayTime.from_dict(data),
            whole_week=bool(data["wholeWeekOccupy"]),
            classroom_name=data["roomName"],
            expr_projects=(data["exprProjectName"] or '').split(',')
        )

    @staticmethod
    def fetch(session: Session, code: str, cqu_session: Optional[Union[CQUSession, str]] = None) \
            -> List[CourseTimetable]:
        """从 my.cqu.edu.cn 上获取学生或老师的课表

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
        :type session: Session
        :param code: 学生或教师的学工号
        :type code: str
        :param cqu_session: 需要获取课表的学期，留空获取当前年级的课表
        :type cqu_session: Optional[Union[CQUSession, str]], optional
        :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 进行认证
        :return: 获取的课表对象的列表
        :rtype: List[CourseTimetable]
        """
        resp = get_course_raw(session, code, cqu_session)
        return [CourseTimetable.from_dict(timetable) for timetable in resp
                if timetable["teachingWeekFormat"]
                ]
