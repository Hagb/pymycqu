from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple, List, Union, ClassVar

from requests import Session, get
from datetime import date, datetime

from ..tools import get_curr_books_raw, get_history_books_raw
from ...utils.datetimes import date_from_str, datetime_from_str
from ..._lib_wrapper.dataclass import dataclass

RENEW_BOOK_URL = "http://lib.cqu.edu.cn/api/v1/user/renew"

__all__ = ['BookInfo']


@dataclass
class BookInfo:
    """
    图书馆书籍相关信息
    """
    id: int
    """书籍id"""
    title: str
    """书籍名称"""
    call_no: str
    """书籍检索号"""
    library_name: str
    """所属图书馆（如虎溪图书馆自然科学阅览室等）"""
    borrow_time: datetime
    """借出时间"""
    should_return_time: Optional[date]
    """应归还日期"""
    is_return: bool
    """是否被归还"""
    return_time: Optional[date]
    """归还时间"""
    renew_count: int
    """续借次数"""
    can_renew: bool
    """是否可被续借"""

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> BookInfo:
        """从反序列化的一个图书信息 json 中生成图书对象

        :param data: 反序列化成字典的图书信息 json
        :type data: Dict[str, Any]
        :return: 图书对象
        :rtype: BookInfo
        """
        return BookInfo(
            id=int(data['bookId']),
            title=data['title'],
            call_no=data['callNo'],
            library_name=data['libraryName'],
            borrow_time=datetime_from_str(data.get('borrowTime')) if data.get('borrowTime') else None,
            should_return_time=date_from_str(data.get('shouldReturnTime')) if data.get('shouldReturnTime') else None,
            is_return=bool(data['cq']),
            return_time=date_from_str(data.get('returnTime')) if data.get('returnTime') else None,
            renew_count=data['renewCount'],
            can_renew=data['renewflag'],
        )

    @staticmethod
    def fetch(session: Session, data: Dict[str, Any], is_get_curr: bool) -> List[BookInfo]:
        """
        获取当前/历史借阅书籍

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu和lib.cqu.edu.cn 进行了认证（:func:`.mycqu.access_mycqu` :func:`.library.access_library`）的 requests 会话
        :type session: Session
        :param data: 调用 :func:`access_library`后获取的用户信息
        :type data: Dict[str, Any]
        :param is_get_curr: 是否获取当前借阅书籍（为否则获取历史借阅书籍）
        :type is_get_curr: bool
        :return: 图书对象组成的列表
        :rtype: List[BookInfo]
        """
        if is_get_curr:
            return [BookInfo.from_dict(book) for book in get_curr_books_raw(session, data)]
        else:
            return [BookInfo.from_dict(book) for book in get_history_books_raw(session, data)]

    @staticmethod
    def renew_book(session: Session, data, book_id: str) -> str:
        data['BookId'] = book_id
        res = session.get(RENEW_BOOK_URL, params={'query': json.dumps(data)})
        return res.json()['result']