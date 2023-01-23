from __future__ import annotations
from typing import Optional, Union

from requests import Session
from .models.cqu_session import CQUSession
from .models.cqu_session_info import CQUSessionInfo
from ..exception import MycquUnauthorized
from ..utils.request_transformer import Request, RequestTransformer

TIMETABLE_URL = "https://my.cqu.edu.cn/api/timetable/class/timetable/student/table-detail"

__all__ = ['get_course_raw', 'async_get_course_raw']


@RequestTransformer.register()
def _get_course_raw(session: Request, code: str, cqu_session: Optional[Union[CQUSession, str]] = None):
    if cqu_session is None:
        cqu_session = (yield CQUSessionInfo._fetch).session
    elif isinstance(cqu_session, str):
        cqu_session = CQUSession.from_str(cqu_session)
    assert isinstance(cqu_session, CQUSession)
    resp = yield session.post(TIMETABLE_URL,
                        params={"sessionId": cqu_session.get_id()},
                        json=[code],
                        )
    if resp.status_code == 401:
        raise MycquUnauthorized()
    return resp.json()['classTimetableVOList']

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
    return _get_course_raw.sync_request(session, code, cqu_session)

async def async_get_course_raw(session: Request, code: str, cqu_session: Optional[Union[CQUSession, str]] = None):
    """
    异步的从 my.cqu.edu.cn 上获取学生或老师的课表

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
    return await _get_course_raw.async_request(session, code, cqu_session)
