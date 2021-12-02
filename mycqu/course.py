"""课程相关的模块
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, List, Union, ClassVar
# from pydantic.dataclasses import dataclass
import re
from datetime import date
from requests import Session, get
from ._lib_wrapper.dataclass import dataclass
from .utils.datetimes import parse_period_str, parse_weeks_str, parse_weekday_str, date_from_str
from .mycqu import MycquUnauthorized

__all__ = ("CQUSession", "CQUSessionInfo",
           "CourseTimetable", "CourseDayTime", "Course")


CQUSESSIONS_URL = "https://my.cqu.edu.cn/api/timetable/optionFinder/session?blankOption=false"
CUR_SESSION_URL = "https://my.cqu.edu.cn/api/resourceapi/session/cur-active-session"
TIMETABLE_URL = "https://my.cqu.edu.cn/api/timetable/class/timetable/student/table-detail"


@dataclass(order=True)
class CQUSession:
    """重大的某一学期
    """
    year: int
    """主要行课年份"""
    is_autumn: bool
    """是否为秋冬季学期"""
    SESSION_RE: ClassVar = re.compile("^([0-9]{4})年?(春|秋)$")
    CQUSESSION_MIN: ClassVar[CQUSession]
    """my.cqu.edu.cn 支持的最早学期"""

    def __post_init_post_parse__(self):
        if hasattr(CQUSession, "CQUSESSION_MIN"):
            if self < CQUSession.CQUSESSION_MIN:
                raise ValueError(
                    f"session should not be earlier than {CQUSession.CQUSESSION_MIN}")

    def get_id(self) -> int:
        """获取该学期在 my.cqu.edu.cn 中的 id

        >>> CQUSession(2021, True).get_id()
        1038

        :return: 学期的 id
        :rtype: int
        """
        return (self.year-1503)*2 + int(self.is_autumn) + 1

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
            try:
                session_list.append(CQUSession.from_str(session["name"]))
            except ValueError:
                pass
        return session_list


CQUSession.CQUSESSION_MIN = CQUSession(2020, True)


@dataclass
class CQUSessionInfo:
    """某学期的一些额外信息，目前只找到获取当个学期这些信息的 web api
    """
    session: CQUSession
    """对应的学期"""
    begin_date: date
    """学期的开始日期"""
    end_date: date
    """学期的结束日期"""

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
        data = resp.json()["data"]
        return CQUSessionInfo(
            session=CQUSession(year=data["year"],
                               is_autumn=data["term"] == "秋"),
            begin_date=date_from_str(data["beginDate"]),
            end_date=date_from_str(data["endDate"])
        )


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
    dept: str
    """开课学院"""
    credit: Optional[float]
    """学分，无法获取到则为 :obj:`None`（如在考表 :class:`.exam.Exam` 中）"""
    instructor: Optional[str]
    """教师"""
    session: Optional[CQUSession]
    """学期，无法获取时则为 :obj:`None`"""

    @ staticmethod
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
        return Course(
            name=data["courseName"],
            code=data["courseCode"],
            course_num=data.get("classNbr"),
            dept=data.get(
                "courseDepartmentName") or data["courseDeptShortName"],
            credit=data.get("credit"),
            instructor=data.get("instructorName"),
            session=session,
        )


@dataclass
class CourseTimetable:
    """课表对象，一个对象存储有相同课程、相同行课节次和相同星期的一批行课安排
    """
    course: Course
    """对应的课程"""
    stu_num: int
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
            stu_num=data["selectedStuNum"],
            classroom=data["roomName"],
            weeks=parse_weeks_str(data.get("weeks")
                                  or data.get("teachingWeekFormat")),  # type: ignore
            day_time=CourseDayTime.from_dict(data),
            whole_week=bool(data["wholeWeekOccupy"])
        )

    @staticmethod
    def fetch(session: Session, id_: str, cqu_session: Optional[Union[CQUSession, str]] = None) -> List[CourseTimetable]:
        """从 my.cqu.edu.cn 上获取学生或老师的课表

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
        :type session: Session
        :param id_: 学生或教师的学工号
        :type id_: str
        :param cqu_session: 需要获取课表的学期，留空获取当前年级的课表
        :type cqu_session: Optional[Union[CQUSession, str]], optional
        :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 进行认证
        :return: 获取的课表对象的列表
        :rtype: List[CourseTimetable]
        """
        if cqu_session is None:
            cqu_session = CQUSessionInfo.fetch(session).session
        elif isinstance(cqu_session, str):
            cqu_session = CQUSession.from_str(cqu_session)
        resp = session.post(TIMETABLE_URL,
                            params={"sessionId": cqu_session.get_id()},
                            json=[id_],
                            )
        if resp.status_code == 401:
            raise MycquUnauthorized()
        return [CourseTimetable.from_dict(timetable) for timetable in resp.json()["classTimetableVOList"]
                if timetable["teachingWeekFormat"]
                ]
