from __future__ import annotations

from typing import List, Dict, Optional

from .enroll_course_timetable import EnrollCourseTimetable
from ..tools import get_enroll_detail_raw
from ..._lib_wrapper.dataclass import dataclass
from ...course import Course

from requests import Session


__all__ = ['EnrollCourseItem']

@dataclass
class EnrollCourseItem:
    """
    可选具体课程，包含课程上课时间、上课教师、教室可容纳学生等信息
    """
    id: Optional[str]
    """可选具体课程id，每个可选具体课程具有唯一id，部分从属课程该值为`None`"""
    session_id: Optional[str]
    """可选具体课程所在学期ID，部分从属课程该值为`None`"""
    checked: Optional[bool]
    """是否已经选择该课程，部分从属课程该值为`None`"""
    course_id: Optional[str]
    """该具体课程所属课程ID，部分从属课程该值为`None`"""
    course: Course
    """课程信息"""
    type: str
    """具体课程类别，如：理论、实验"""
    selected_num: Optional[int]
    """已选课程学生，部分从属课程该值为`None`"""
    capacity: Optional[int]
    """该课程容量上限，部分从属课程该值为`None`"""
    children: Optional[List[EnrollCourseItem]]
    """该课程从属课程列表，一般为理论课程的实验课"""
    campus: Optional[str]
    """所属校区，如D区，部分从属课程该值为`None`"""
    parent_id: Optional[str]
    """所从属具体课程id，如果不存在从属关系，该值为None"""
    timetable: List[EnrollCourseTimetable]

    @staticmethod
    def from_dict(data: Dict) -> EnrollCourseItem:
        """
        从反序列化的可选具体课程字典中返回`EnrollCourseItem`
        :param data: 反序列化成字典的可选具体课程
        :type data: Dict[str, Any]
        :return: 对应的可选具体课程列表
        :rtype: EnrollCourseItem
        """
        return EnrollCourseItem(
            id=data['id'],
            session_id=data['sessionId'],
            checked=data['checked'],
            course_id=data['courseId'],
            course=Course.from_dict(data),
            type=data['classType'],
            selected_num=data['selectedNum'],
            capacity=data['stuCapacity'],
            children=[EnrollCourseItem.from_dict(item) for item in data['childrenList']]
                     if data['childrenList'] else None,
            campus=data['campusShortName'],
            parent_id=data['parentClassId'],
            timetable=EnrollCourseTimetable.from_str(data['classTime']) if data['classTime'] is not None else []
        )

    @staticmethod
    def fetch(session: Session, id: str, is_major: bool = True) -> List[EnrollCourseItem]:
        """从 my.cqu.edu.cn 上获取学生可选具体课程

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
        :type session: Session
        :param id: 需要获取的课程id（非Course Code）
        :type id: str
        :param is_major: 是否获取主修可选课程，为`False`时查询辅修可选课程
        :type is_major: bool
        :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 进行认证
        :return: 获取的可选具体课程对象的列表
        :rtype: List[EnrollCourseItem]
        """
        res = get_enroll_detail_raw(session, id, is_major)
        return [EnrollCourseItem.from_dict(item) for item in res]