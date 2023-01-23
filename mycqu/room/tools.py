"""教室相关信息模块"""

from __future__ import annotations
from typing import Optional, Union

from requests import Session
from ..course import CQUSession, CQUSessionInfo
from .models.room import Room
from ..exception import MycquUnauthorized, InvalidRoom
from ..utils.request_transformer import Request, RequestTransformer

ROOM_TIMETABLE_URL = "https://my.cqu.edu.cn/api/timetable/class/timetable/room/table-detail?sessionId=1039"

__all__ = ['get_room_timetable_raw', 'async_get_room_timetable_raw']


@RequestTransformer.register()
def _get_room_timetable_raw(session: Session, room: Union[Room, str],
                            cqu_session: Optional[Union[CQUSession, str]] = None):
    if cqu_session is None:
        cqu_session = (yield CQUSessionInfo._fetch).session
    elif isinstance(cqu_session, str):
        cqu_session = CQUSession.from_str(cqu_session)
    assert isinstance(cqu_session, CQUSession)

    if isinstance(room, str):
        temp = yield Room._fetch, {'name': room}
        if len(temp) == 0 or temp[0].name != room:
            raise InvalidRoom
        else:
            room = temp[0]
    assert isinstance(room, Room)

    res = yield session.post(ROOM_TIMETABLE_URL, json=[str(room.id)])
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
    return _get_room_timetable_raw.sync_request(session, room, cqu_session)

async def async_get_room_timetable_raw(session: Request, room: Union[Room, str],
                                       cqu_session: Optional[Union[CQUSession, str]] = None):
    """
    异步的获取某教室活动详情

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
    return await _get_room_timetable_raw.async_request(session, room, cqu_session)
