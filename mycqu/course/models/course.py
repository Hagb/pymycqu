from __future__ import annotations
from typing import Any, Dict, Optional, Union

from ..._lib_wrapper.dataclass import dataclass
from .cqu_session import CQUSession


__all__ = ['Course']

@dataclass
class Course:
    """与具体行课时间无关的课程信息
    """
    name: Optional[str]
    """课程名称"""
    code: Optional[str]
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

        instructor_name = None
        if data.get("instructorName") is not None:
            instructor_name = data.get("instructorName")
        elif data.get("instructorNames") is not None:
            instructor_name = data.get("instructorNames")
        elif data.get('classTimetableInstrVOList') is not None:
            instructor_name = ', '.join(instructor.get('instructorName')
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
