from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, List, Union

from requests import Session

from .course import Course
from .course_day_time import CourseDayTime
from ..tools import get_course_raw, async_get_course_raw
from ..._lib_wrapper.dataclass import dataclass
from .cqu_session import CQUSession
from ...utils.datetimes import parse_weeks_str
from ...utils.request_transformer import Request


__all__ = ['CourseTimetable']

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

    @staticmethod
    async def async_fetch(session: Request, code: str, cqu_session: Optional[Union[CQUSession, str]] = None) \
            -> List[CourseTimetable]:
        """
        异步的从 my.cqu.edu.cn 上获取学生或老师的课表

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
        resp = await async_get_course_raw(session, code, cqu_session)
        return [CourseTimetable.from_dict(timetable) for timetable in resp
                if timetable["teachingWeekFormat"]
                ]
