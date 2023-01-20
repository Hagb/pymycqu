"""
成绩相关模块
"""
from __future__ import annotations

import json
from typing import Dict, Union, Optional, Generic

import requests

from ..exception import CQUWebsiteError, MycquUnauthorized
from ..utils.request_transformer import Request, RequestTransformer

__all__ = ("get_score_raw", "async_get_score_raw", "get_gpa_ranking_raw", "async_get_gpa_ranking_raw")


def _launch_authorized_header(authorization: str) -> Dict:
    return {
        'Referer': 'https://my.cqu.edu.cn/sam/home',
        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0)',
        'Authorization': authorization
    }

@RequestTransformer.register()
def _get_score_raw(request: Request, is_minor_boo: bool, headers: Optional[Dict] = None):
    url = 'https://my.cqu.edu.cn/api/sam/score/student/score' + ('?isMinorBoo=true' if is_minor_boo else '')
    res = yield request.get(url, headers=headers)

    content = json.loads(res.content)
    if res.status_code == 401:
        raise MycquUnauthorized()
    if content['status'] == 'error':
        raise CQUWebsiteError(content['msg'])
    return content['data']


def get_score_raw(auth: Union[Generic[Request], str], is_minor_boo: bool = False) -> Dict:
    """
    获取学生原始成绩

    :param auth: 登陆后获取的authorization或者调用过mycqu.access_mycqu的session
    :type auth: Union[Session, str]
    :param is_minor_boo: 是否获取辅修成绩
    :type is_minor_boo: bool
    :return: 反序列化获取的score列表
    :rtype: Dict
    """
    if not isinstance(auth, str):
        return _get_score_raw.sync_request(auth, is_minor_boo)
    else:
        return _get_score_raw.sync_request(requests, is_minor_boo, _launch_authorized_header(auth))

async def async_get_score_raw(session: Generic[Request], is_minor_boo: bool = False):
    """
    异步的获取学生原始成绩

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    :param is_minor_boo: 是否获取辅修成绩
    :type is_minor_boo: bool
    :return: 反序列化获取的score列表
    :rtype: Dict
    """
    return await _get_score_raw.async_request(session, is_minor_boo)

@RequestTransformer.register()
def _get_gpa_ranking_raw(request: Request, headers: Optional[Dict] = None):
    res = yield request.get('https://my.cqu.edu.cn/api/sam/score/student/studentGpaRanking', headers=headers)

    content = json.loads(res.content)
    if res.status_code == 401:
        raise MycquUnauthorized()
    if content['status'] == 'error':
        raise CQUWebsiteError(content['msg'])
    return content['data']


def get_gpa_ranking_raw(auth: Union[Generic[Request], str]):
    """
    获取学生绩点排名

    :param auth: 登陆后获取的authorization或者调用过mycqu.access_mycqu的session
    :type auth: Union[Session, str]
    :return: 反序列化获取的绩点、排名
    :rtype: Dict
    """
    if not isinstance(auth, str):
        return _get_gpa_ranking_raw.sync_request(auth)
    else:
        headers = _launch_authorized_header(auth)
        return _get_gpa_ranking_raw.sync_request(headers)

async def async_get_gpa_ranking_raw(session: Generic[Request]):
    """
    异步的获取学生绩点排名

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Union[Session, str]
    :return: 反序列化获取的绩点、排名
    :rtype: Dict
    """
    return await _get_gpa_ranking_raw.async_request(session)
