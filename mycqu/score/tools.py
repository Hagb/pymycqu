"""
成绩相关模块
"""
from __future__ import annotations

import json
from typing import Dict, Union
from requests import Session, get

from ..exception import CQUWebsiteError, MycquUnauthorized

__all__ = ("get_score_raw", "get_gpa_ranking_raw")


def get_score_raw(auth: Union[Session, str], is_minor_boo: bool):
    """
    获取学生原始成绩

    :param auth: 登陆后获取的authorization或者调用过mycqu.access_mycqu的session
    :type auth: Union[Session, str]
    :param is_minor_boo: 是否获取辅修成绩
    :type is_minor_boo: bool
    :return: 反序列化获取的score列表
    :rtype: Dict
    """
    url = 'https://my.cqu.edu.cn/api/sam/score/student/score' + ('?isMinorBoo=true' if is_minor_boo else '')
    if isinstance(auth, Session):
        res = auth.get(url)
    else:
        authorization = auth
        headers = {
            'Referer': 'https://my.cqu.edu.cn/sam/home',
            'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0)',
            'Authorization': authorization
        }
        res = get(
            url, headers=headers)

    content = json.loads(res.content)
    if res.status_code == 401:
        raise MycquUnauthorized()
    if content['status'] == 'error':
        raise CQUWebsiteError(content['msg'])
    return content['data']


def get_gpa_ranking_raw(auth: Union[Session, str]):
    """
    获取学生绩点排名

    :param auth: 登陆后获取的authorization或者调用过mycqu.access_mycqu的session
    :type auth: Union[Session, str]
    :return: 反序列化获取的绩点、排名
    :rtype: Dict
    """
    if isinstance(auth, Session):
        res = auth.get('https://my.cqu.edu.cn/api/sam/score/student/studentGpaRanking')
    else:
        authorization = auth
        headers = {
            'Referer': 'https://my.cqu.edu.cn/sam/home',
            'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0)',
            'Authorization': authorization
        }
        res = get(
            'https://my.cqu.edu.cn/api/sam/score/student/studentGpaRanking', headers=headers)

    content = json.loads(res.content)
    if res.status_code == 401:
        raise MycquUnauthorized()
    if content['status'] == 'error':
        raise CQUWebsiteError(content['msg'])
    return content['data']
