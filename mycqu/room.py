"""教室相关信息模块"""

from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, List, Union, ClassVar

from requests import Session, get
from datetime import date
from ._lib_wrapper.dataclass import dataclass
from .course import CQUSession, CQUSessionInfo
from .utils.datetimes import parse_period_str, parse_weeks_str, parse_weekday_str, date_from_str
from .exception import MycquUnauthorized, InvalidRoom

__all__ = ('Room', 'RoomTimetable')

ROOM_TIMETABLE_URL = "https://my.cqu.edu.cn/api/timetable/class/timetable/room/table-detail?sessionId=1039"
ROOM_ID_URL = "https://my.cqu.edu.cn/api/resourceapi/room/roomName-filter"


def get_room_info_raw(session: Session, name: str):
    """
    依据教室名字查询教室（支持模糊查询）

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    :param name: 教室名称
    :type name: str
    :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 进行认证
    :return: 教室对象组成的列表
    :rtype: dict
    """
    res = session.get(ROOM_ID_URL, params={'roomName': name})
    if res.status_code == 401:
        raise MycquUnauthorized

    return res.json()


def get_room_timetable_raw(session: Session, room: Union[Room, str],
                           cqu_session: Optional[Union[CQUSession, str]] = None):
    """
    获取某教室活动详情

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    :param room: 教室信息（为Room对象或需要获取的教室名称）
    :type room: Union[Room, str]
    :param cqu_session: 需要获取课表的学期，留空获取当前年级的课表
    :type cqu_session: Optional[Union[CQUSession, str]], optional
    :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 进行认证
    :raises InvalidName: 若教室名称不为准确教室名称时
    :return: 反序列化获取教室活动的json
    :rtype: dict
    """
    if cqu_session is None:
        cqu_session = CQUSessionInfo.fetch(session).session
    elif isinstance(cqu_session, str):
        cqu_session = CQUSession.from_str(cqu_session)
    assert isinstance(cqu_session, CQUSession)
    if isinstance(room, str):
        temp = Room.fetch(session, room)
        if len(temp) == 0 or temp[0].name != room:
            raise InvalidRoom
        else:
            room = temp[0]
    assert isinstance(room, Room)
    res = session.post(ROOM_TIMETABLE_URL, json=[str(room.id)])
    if res.status_code == 401:
        raise MycquUnauthorized

    return res.json()


@dataclass
class Room:
    """教室对象，储存了某个教室的相关信息"""
    id: int
    """教室id"""
    name: str
    """教室名称，如D1345"""
    capacity: int
    """教室容量"""
    building_name: str
    """教室所属建筑名称"""
    campus_name: str
    """教室所属校区"""
    room_type: str
    """教室类型"""

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Room:
        """从反序列化的一个教室信息 json 中生成教室对象

        :param data: 反序列化成字典的教室 json
        :type data: Dict[str, Any]
        :return: 教室对象
        :rtype: Room
        """
        return Room(
            id=int(data['id']),
            name=data['name'],
            capacity=int(data['capacity']),
            building_name=data['buildingName'],
            campus_name=data['campusName'],
            room_type=data['roomClassificationName']
        )

    @staticmethod
    def fetch(session: Session, name: str) -> List[Room]:
        """
        依据教室名字查询教室（支持模糊查询）

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
        :type session: Session
        :param name: 教室名称
        :type name: str
        :return: 教室对象组成的列表
        :rtype: List[Room]
        """
        return [Room.from_dict(room) for room in get_room_info_raw(session, name)]


@dataclass
class RoomActivityInfo:
    """教室活动的公有属性"""
    period: Tuple[int, int]
    """占用节数"""
    weeks: List[Tuple[int, int]]
    """行课周数，列表中每个元组 (a,b) 代表一个周数范围 a~b（包含 a, b），在单独的一周则有 b=a"""
    weekday: int
    """星期，0 为周一，6 为周日，此与 :attr:`datetime.date.day` 一致"""

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        """从反序列化的一个活动信息 json 中生成RoomActivityInfo对象

        :param data: 反序列化成字典的活动 json
        :type data: Dict[str, Any]
        :return: 教室活动
        :rtype: RoomActivityInfo
        """
        return RoomActivityInfo(
            period=parse_period_str(data['periodFormat']),
            weeks=parse_weeks_str(data['teachingWeekFormat']),
            weekday=int(data['weekDay']) - 1
        )


@dataclass
class RoomExamInvigilator:
    """教室考试活动监考员信息"""
    name: str
    """姓名"""
    type: str
    """监考类型，如副监考、巡考等"""
    dept_name: str
    """所在部门名称"""

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        """从反序列化的一个教室考试监考员信息 json 中生成RoomExamInvigilator对象

        :param data: 反序列化成字典的教室考试监考员信息 json
        :type data: Dict[str, Any]
        :return: 教室考试活动监考员对象
        :rtype: RoomExamInvigilator
        """
        return RoomExamInvigilator(
            name=data['name'],
            type=data['invigilatorType'],
            dept_name=data['deptName']
        )


@dataclass
class RoomExam:
    """教室中考试活动相关信息"""
    activity_info: RoomActivityInfo
    """基础信息"""
    course_name: str
    """考试课程名称"""
    stu_capacity: int
    """考试学生数量"""
    time_range: str
    """持续时间"""
    invigilators: List[RoomExamInvigilator]
    """监考员信息"""

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        """从反序列化的一个教室考试信息 json 中生成RoomExam对象

        :param data: 反序列化成字典的教室考试 json
        :type data: Dict[str, Any]
        :return: 教室考试
        :rtype: RoomExam
        """
        return RoomExam(
            activity_info=RoomActivityInfo.from_dict(data),
            course_name=data['courseName'],
            stu_capacity=int(data['stuCapacity']),
            time_range=data['timeIn'],
            invigilators=[RoomExamInvigilator.from_dict(temp) for temp in data['invigilatorVOList']]
        )


@dataclass
class RoomTempActivity:
    """教室临时活动"""
    activity_info: RoomActivityInfo
    """基础信息"""
    content: str
    """临时活动名称"""
    department: str
    """申请学院"""
    type: str
    """临时活动类型，如上课、开会等"""
    time_range: str
    """活动持续时间"""
    date: List[date]
    """活动举办日期"""

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        """从反序列化的一个教室临时活动信息 json 中生成RoomTempActivity对象

        :param data: 反序列化成字典的教室临时活动 json
        :type data: Dict[str, Any]
        :return: 教室临时活动
        :rtype: RoomTempActivity
        """
        return RoomTempActivity(
            activity_info=RoomActivityInfo.from_dict(data),
            content=data['actContent'],
            department=data['actDepartment'],
            type=data['tempActType'],
            time_range=data['timeIn'],
            date=[date_from_str(date) for date in data['dateStr'].split(',')]
        )


@dataclass
class RoomCourse:
    """教室课程活动"""
    activity_info: RoomActivityInfo
    """基础信息"""
    class_number: str
    """教学班号"""
    course_code: str
    """课程代码"""
    course_name: str
    """课程名称"""
    department: str
    """开课学院"""
    stu_num: int
    """选课学生数"""
    credit: float
    """课程学分"""
    instructor_name: str
    """教师姓名"""

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        """从反序列化的一个教室课程信息 json 中生成RoomCourse对象

        :param data: 反序列化成字典的教室课程 json
        :type data: Dict[str, Any]
        :return: 教室课程
        :rtype: RoomCourse
        """
        return RoomCourse(
            activity_info=RoomActivityInfo.from_dict(data),
            class_number=data['classNbr'],
            course_code=data['courseCode'],
            course_name=data['courseName'],
            department=data['courseDepartmentName'],
            stu_num=int(data['selectedStuNum']),
            credit=float(data['credit']),
            instructor_name=data['instructorName'],
        )


@dataclass
class RoomTimetable:
    course_timetable: List[RoomCourse]
    exam_timetable: List[RoomExam]
    temp_activity_timetable: List[RoomTempActivity]

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        """从反序列化的一个教室信息 json 中生成RoomTimetable对象

        :param data: 反序列化成字典的教室信息 json
        :type data: Dict[str, Any]
        :return: 教室活动信息
        :rtype: RoomTimetable
        """
        return RoomTimetable(
            course_timetable=[RoomCourse.from_dict(temp) for temp in data['classTimetableVOList']],
            exam_timetable=[RoomExam.from_dict(temp) for temp in data['roomExamTimeTableVOList']],
            temp_activity_timetable=[RoomTempActivity.from_dict(temp) for temp in data['tempActivityTimetableVOList']]
        )

    @staticmethod
    def fetch(session: Session, room: Union[Room, str], cqu_session: Optional[Union[CQUSession, str]] = None):
        """
        获取某教室活动详情

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
        :type session: Session
        :param room: 教室信息（为Room对象或需要获取的教室名称）
        :type room: Union[Room, str]
        :param cqu_session: 需要获取课表的学期，留空获取当前年级的课表
        :type cqu_session: Optional[Union[CQUSession, str]], optional
        :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 进行认证
        :raises InvalidName: 若教室名称不为准确教室名称时
        :return: 教室活动信息对象
        :rtype: RoomTimetable
        """

        return RoomTimetable.from_dict(get_room_timetable_raw(session, room, cqu_session))
