from __future__ import annotations

import json
import re
from typing import List, Dict, Any, Optional, ClassVar, Tuple

from ._lib_wrapper.dataclass import dataclass
from .course import Course, CourseDayTime

from requests import Session

from .utils.datetimes import parse_weekday_str, parse_period_str, parse_weeks_str

__all__ = ('EnrollCourseInfo', 'EnrollCourseTimetable', 'EnrollCourseItem')

ENROLLMENT_COURSE_LIST_URL = "https://my.cqu.edu.cn/api/enrollment/enrollment/course-list?selectionSource="
ENROLLMENT_COURSE_DETAIL_URL = "https://my.cqu.edu.cn/api/enrollment/enrollment/courseDetails/"


def get_enroll_list_raw(session: Session, is_major: bool = True) -> Dict[str: List]:
    """

    从 my.cqu.edu.cn 上获取学生可选课程

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    :param is_major: 是否查询主修专业可选课程(为false时查询辅修专业可选课程)
    :type is_major: bool
    :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 进行认证
    :return: 反序列化获取可选课程的的json
    :rtype: Dict[str, List]
    """

    url = ENROLLMENT_COURSE_LIST_URL + ("主修" if is_major else "辅修")
    res = session.get(url)
    content = json.loads(res.text)
    assert content["status"] == "success"

    result = {}
    for data in content["data"]:
        result[data["selectionArea"]] = data["courseVOList"]

    return result


def get_enroll_detail_raw(session: Session, course_id: str, is_major: bool = True) -> List:
    """
    从 my.cqu.edu.cn 上获取某可选课程详情

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    :param course_id: 待查询课程参数
    :type course_id: str
    :param is_major: 待查询课程是否为主修课程(为false时表示查询辅修可选课程)
    :type is_major: bool
    :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 进行认证
    :return: 反序列化查询到当可选课程的的json
    :rtype: List
    """
    url = ENROLLMENT_COURSE_DETAIL_URL + course_id + "?selectionSource=" + ("主修" if is_major else "辅修")
    res = session.get(url)
    content = json.loads(res.text)
    return content['selectCourseListVOs'][0]['selectCourseVOList']


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


@dataclass
class EnrollCourseTimetable:
    """
    可选具体课程上课时间、上课地点信息
    """
    weeks: List[Tuple[int, int]]
    """上课周数"""
    time: Optional[CourseDayTime]
    """上课时间"""
    pos: Optional[str]
    """上课地点"""

    WEEKS_RE: ClassVar = re.compile("^(.*)周")
    PERIOD_RE: ClassVar = re.compile("星期. [0-9]-[0-9]小节")
    POS_RE: ClassVar = re.compile("&(.*)$")

    @staticmethod
    def from_str(data: str) -> List[EnrollCourseTimetable]:
        """从字符串中生成具体待选课程上课时间信息
        示例字符串"1-5,7-9周 星期二 6-7小节 &D1144 ;1-5,7-9周 星期五 3-4小节 &D1143 "

        :param data: 需提取信息的字符串
        :type data: str
        :return: 返回待选课程上课时间信息当列表
        :rtype: List[EnrollCourseTimetable]
        """
        items = data.split(';')
        result = []

        for item in items:
            pos_str = EnrollCourseTimetable.POS_RE.search(item)
            pos = None
            if pos_str:
                pos = pos_str.group().strip()[1:]

            period_str = EnrollCourseTimetable.PERIOD_RE.search(item)
            timetable = None
            if period_str:
                period_str = period_str.group()
                timetable = CourseDayTime(
                    weekday=parse_weekday_str(period_str[:3]),
                    period=parse_period_str(period_str[4:-2])
                )

            result.append(
                EnrollCourseTimetable(
                    weeks=parse_weeks_str(EnrollCourseTimetable.WEEKS_RE.search(item).group()[:-1]),
                    time=timetable,
                    pos=pos
                )
            )

        return result


@dataclass
class EnrollCourseItem:
    """
    可选具体课程，包含课程上课时间、上课教师、教室可容纳学生等信息
    """
    id: str
    """可选具体课程id，每个可选具体课程具有唯一id"""
    session_id: str
    """可选具体课程所在学期ID"""
    checked: bool
    """是否已经选择该课程"""
    course_id: str
    """该具体课程所属课程ID"""
    course: Course
    """课程信息"""
    type: str
    """具体课程类别，如：理论、实验"""
    selected_num: int
    """已选课程学生"""
    capacity: int
    """该课程容量上限"""
    children: Optional[List[EnrollCourseItem]]
    """该课程从属课程列表，一般为理论课程的实验课"""
    campus: str
    """所属校区，如D区"""
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
            timetable=EnrollCourseTimetable.from_str(data['classTime'])
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
