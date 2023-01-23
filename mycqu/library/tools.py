"""图书馆相关模块"""

from __future__ import annotations

import json
from html.parser import HTMLParser
from typing import Any, Dict, List

from requests import Session

from mycqu.auth import access_service

__all__ = ['access_library', 'get_curr_books_raw', 'get_history_books_raw']

LIB_LOGIN_URL = "http://authserver.cqu.edu.cn/authserver/login?service=http://lib.cqu.edu.cn/caslogin"
CURR_BOOKS_URL = "http://lib.cqu.edu.cn/api/v1/user/getcurrentborrowlist"
HISTORY_BOOKS_URL = "http://lib.cqu.edu.cn/api/v1/user/GetHistoryBorrowList"


class LibPageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._starttag: int = 0
        self.user_id: str = ""
        self.user_key: str = ""

    def handle_starttag(self, tag, attrs):
        if self._starttag != 2 and tag == 'input' and ('id', 'hfldUserId') in attrs:
            self._starttag = self._starttag + 1
            for key, val in attrs:
                if key == "value":
                    self.user_id = val
                    break

        if self._starttag != 2 and tag == 'input' and ('id', 'hfldUserKey') in attrs:
            self._starttag = self._starttag + 1
            for key, val in attrs:
                if key == "value":
                    self.user_key = val
                    break


def access_library(session: Session) -> Dict[str, Any]:
    """
    通过统一身份认证登陆图书馆页面，返回UserID和UserKey用于查询

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    :return: 图书馆账号特有的UserID和UserKey
    :rtype: Dict[str, Any]
    """
    res = access_service(session, "http://lib.cqu.edu.cn/caslogin")
    res1 = session.get(url="http://lib.cqu.edu.cn" + res.headers['Location'], allow_redirects=False)
    parser = LibPageParser()
    parser.feed(res1.text)
    data = {
        "UserID": parser.user_id,
        "UserKey": parser.user_key,
    }

    return data


def get_curr_books_raw(session: Session, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    获取当前借阅书籍

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    :param data: 调用 :func `access_library`后获取的用户信息
    :type data: Dict[str, Any]
    :return: 反序列化的书籍信息json
    :rtype: List[Dict[str, Any]]
    """
    res = session.get(CURR_BOOKS_URL, params={"query": json.dumps(data)})
    return res.json()['result']['borrowBookList']


def get_history_books_raw(session: Session, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    获取历史借阅书籍

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    :param data: 调用 :func `access_library`后获取的用户信息
    :type data: Dict[str, Any]
    :return: 反序列化的书籍信息json
    :rtype: List[Dict[str, Any]]
    """
    res = session.get(HISTORY_BOOKS_URL, params={"query": json.dumps(data)})
    return res.json()['result']['borrowBookList']
