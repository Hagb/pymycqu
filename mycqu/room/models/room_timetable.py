from typing import Union, Optional, List, Dict, Any

from requests import Session

from ...course.models import CQUSession
from ..._lib_wrapper.dataclass import dataclass
from .room import Room
from .room_course import RoomCourse
from .room_exam import RoomExam
from .room_temp_activity import RoomTempActivity
from ..tools import get_room_timetable_raw, async_get_room_timetable_raw
from ...utils.request_transformer import Request

__all__ = ['RoomTimetable']


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
            course_timetable=[RoomCourse.from_dict(temp) for temp in data['classTimetableVOList']] \
            if data['classTimetableVOList'] is not None else [],
            exam_timetable=[RoomExam.from_dict(temp) for temp in data['roomExamTimeTableVOList']] \
            if data['roomExamTimeTableVOList'] is not None else [],
            temp_activity_timetable=[RoomTempActivity.from_dict(temp) for temp in data['tempActivityTimetableVOList']] \
            if data['tempActivityTimetableVOList'] is not None else []
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

    @staticmethod
    async def async_fetch(session: Request, room: Union[Room, str], cqu_session: Optional[Union[CQUSession, str]] = None):
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
        return RoomTimetable.from_dict(await async_get_room_timetable_raw(session, room, cqu_session))
