from __future__ import annotations

from datetime import date
from typing import Optional, Any, List

from requests import Session

from .cqu_session import CQUSession
from ...exception import MycquUnauthorized
from ..._lib_wrapper.dataclass import dataclass
from ...utils.datetimes import date_from_str
from ...utils.request_transformer import Request, RequestTransformer

CUR_SESSION_URL = "https://my.cqu.edu.cn/api/resourceapi/session/cur-active-session"
ALL_SESSIONSINFO_URL = "https://my.cqu.edu.cn/api/resourceapi/session/list"


__all__ = ['CQUSessionInfo']

@dataclass
class CQUSessionInfo:
    """某学期的一些额外信息
    """
    session: CQUSession
    """对应的学期"""
    begin_date: Optional[date]
    """学期的开始日期"""
    end_date: Optional[date]
    """学期的结束日期"""

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CQUSessionInfo:
        """从反序列化的（一个）学期信息 json 中获取学期信息

        :param data: json 反序列化得到的字典
        :type data: dict[str, Any]
        :return: 学期信息对象
        :rtype: CQUSessionInfo
        """
        return CQUSessionInfo(
            session=CQUSession(year=data["year"],
                               is_autumn=data["term"] == "秋"),
            begin_date=date_from_str(data["beginDate"]),
            end_date=date_from_str(data["endDate"])
        )

    @staticmethod
    @RequestTransformer.register()
    def _fetch_all(session: Request) -> List[CQUSessionInfo]:
        resp = yield session.get(ALL_SESSIONSINFO_URL)
        if resp.status_code == 401:
            raise MycquUnauthorized()
        cqusesions: List[CQUSessionInfo] = []
        for data in resp.json()['sessionVOList']:
            if not data['beginDate']:
                break
            cqusesions.append(CQUSessionInfo.from_dict(data))
        return cqusesions

    @staticmethod
    def fetch_all(session: Session) -> List[CQUSessionInfo]:
        """获取所有学期信息

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
        :type session: Session
        :return: 按时间降序排序的学期（最新学期可能尚未到来，其信息准确度也无法保障！）
        :rtype: List[CQUSessionInfo]
        """
        return CQUSessionInfo._fetch_all.sync_request(session)

    @staticmethod
    async def async_fetch_all(session: Request) -> List[CQUSessionInfo]:
        """
        异步的获取所有学期信息

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
        :type session: Session
        :return: 按时间降序排序的学期（最新学期可能尚未到来，其信息准确度也无法保障！）
        :rtype: List[CQUSessionInfo]
        """
        return await CQUSessionInfo._fetch_all.async_request(session)

    @staticmethod
    @RequestTransformer.register()
    def _fetch(session: Request) -> CQUSessionInfo:
        resp = yield session.get(CUR_SESSION_URL)
        if resp.status_code == 401:
            raise MycquUnauthorized()
        return CQUSessionInfo.from_dict(resp.json()["data"])

    @staticmethod
    def fetch(session: Session) -> CQUSessionInfo:
        """从 my.cqu.edu.cn 上获取当前学期的学期信息，需要登录并认证了 mycqu 的会话

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
        :type session: Session
        :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 认证
        :return: 本学期信息对象
        :rtype: CQUSessionInfo
        """
        return CQUSessionInfo._fetch.sync_request(session)

    @staticmethod
    async def async_fetch(session: Request) -> CQUSessionInfo:
        """
        异步的从 my.cqu.edu.cn 上获取当前学期的学期信息，需要登录并认证了 mycqu 的会话

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
        :type session: Session
        :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 认证
        :return: 本学期信息对象
        :rtype: CQUSessionInfo
        """
        return await CQUSessionInfo._fetch.async_request(session)
