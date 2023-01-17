from __future__ import annotations

from typing import List, Dict, Any, Optional

from ..tools import get_enroll_list_raw
from ..._lib_wrapper.dataclass import dataclass
from ...course import Course

from requests import Session

__all__ = ['EnrollCourseInfo']

@dataclass
class EnrollCourseInfo:
    """
    可选课程信息
    """
    id: str
    """可选课程id"""
    course: Course
    """可选课程信息"""
    category: str
    """可选课程类型，如：公共基础课，主修专业课，非限制选修课等"""
    type: str
    """课程类别，如：主修专业课，通识教育课程等"""
    enroll_sign: Optional[str]
    """选课标识，如：已选，已选满等，当为 :obj:`None` 时标识无相关标记"""
    course_nature: str
    """课程属性，如必修，选修等"""
    campus: List[str]
    """可选课程可选校区，如['D区'], ['A区', 'D区']等"""

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> EnrollCourseInfo:
        """
        从反序列化的选课列表中返回``EnrollCourseInfo``
        :param data: 反序列化成字典的选课列表
        :type data: Dict[str, Any]
        :return: 对应的可选课程列表
        :rtype: EnrollCourseInfo
        """
        return EnrollCourseInfo(
            id=data['id'],
            course=Course(name=data['name'], code=data['codeR'], dept=data['departmentName'],
                          credit=float(data['credit']), course_num=None, instructor=None, session=None),
            category=data['courseCategory'],
            type=data['selectionArea'],
            enroll_sign=data['courseEnrollSign'],
            course_nature=data['courseNature'],
            campus=data['campusShortNameSet']
        )

    @staticmethod
    def fetch(session: Session, is_major: bool = True) -> Dict[str, list[EnrollCourseInfo]]:
        """从 my.cqu.edu.cn 上获取学生可选课程

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
        :type session: Session
        :param is_major: 是否获取主修可选课程，为`False`时查询辅修可选课程
        :type is_major: bool
        :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 进行认证
        :return: 获取的可选课程对象的列表
        :rtype: List[EnrollCourseInfo]
        """
        res = get_enroll_list_raw(session, is_major)
        result = {}
        for key, value in res.items():
            result[key] = [EnrollCourseInfo.from_dict(item) for item in value]

        return result