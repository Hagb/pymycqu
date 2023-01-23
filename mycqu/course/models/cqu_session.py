from __future__ import annotations

import re
from typing import ClassVar, Tuple, List, Optional
from functools import lru_cache

import requests
from requests import Session

from ..._lib_wrapper.dataclass import dataclass
from ...utils.request_transformer import Request, RequestTransformer

CQUSESSIONS_URL = "https://my.cqu.edu.cn/api/timetable/optionFinder/session?blankOption=false"


__all__ = ['CQUSession']

@dataclass(order=True, frozen=True)
class CQUSession:
    """重大的某一学期
    """
    year: int
    """主要行课年份"""
    is_autumn: bool
    """是否为秋冬季学期"""
    SESSION_RE: ClassVar = re.compile("^([0-9]{4})年?(春|秋)$")
    _SPECIAL_IDS: ClassVar[Tuple[int, ...]] = (
        239259, 102, 101, 103, 1028, 1029, 1030, 1032)  # 2015 ~ 2018

    @lru_cache(maxsize=32)  # type: ignore
    def __new__(cls, year: int, is_autumn: bool):  # pylint: disable=unused-argument
        return super(CQUSession, cls).__new__(cls)

    def __str__(self):
        return str(self.year) + ('秋' if self.is_autumn else '春')

    def get_id(self) -> int:
        """获取该学期在 my.cqu.edu.cn 中的 id

        >>> CQUSession(2021, True).get_id()
        1038

        :return: 学期的 id
        :rtype: int
        """
        if self.year >= 2019:
            return (self.year - 1503) * 2 + int(self.is_autumn) + 1
        elif 2015 <= self.year <= 2018:
            return self._SPECIAL_IDS[(self.year - 2015) * 2 + int(self.is_autumn)]
        else:
            return (2015 - self.year) * 2 - int(self.is_autumn)

    @staticmethod
    def from_str(string: str) -> CQUSession:
        """从学期字符串中解析学期

        >>> CQUSession.from_str("2021春")
        CQUSession(year=2021, is_autumn=False)
        >>> CQUSession.from_str("2020年秋")
        CQUSession(year=2020, is_autumn=True)

        :param string: 学期字符串，如“2021春”、“2020年秋”
        :type string: str
        :raises ValueError: 字符串不是一个预期中的学期字符串时抛出
        :return: 对应的学期
        :rtype: CQUSession
        """
        match = CQUSession.SESSION_RE.match(string)
        if match:
            return CQUSession(
                year=match[1],
                is_autumn=match[2] == "秋"
            )
        else:
            raise ValueError(f"string {string} is not a session")

    @staticmethod
    @RequestTransformer.register()
    def _fetch(request: Request) -> List[CQUSession]:
        session_list = []
        for session in (yield request.get(CQUSESSIONS_URL)).json():
            session_list.append(CQUSession.from_str(session["name"]))
        return session_list

    @staticmethod
    def fetch(session: Optional[Session] = None) -> List[CQUSession]:
        """从 my.cqu.edu.cn 上获取各个学期

        :return: 各个学期组成的列表
        :rtype: List[CQUSession]
        """
        return CQUSession._fetch.sync_request(requests if session is None else session)

    @staticmethod
    async def async_fetch(session: Request) -> List[CQUSession]:
        """
        异步的从 my.cqu.edu.cn 上获取各个学期

        :return: 各个学期组成的列表
        :rtype: List[CQUSession]
        """
        return await CQUSession._fetch.async_request(session)
