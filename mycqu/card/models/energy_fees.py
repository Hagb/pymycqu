from __future__ import annotations

from typing import Optional, Any

from requests import Session

from ..tools import get_fees_raw
from ..._lib_wrapper.dataclass import dataclass


__all__ = ['EnergyFees']


@dataclass
class EnergyFees:
    """
    某宿舍的水电费相关信息
    """
    balance: float
    """账户余额"""
    electricity_subsidy: Optional[float]
    """电剩余补助（仅虎溪校区拥有）"""
    water_subsidy: Optional[float]
    """水剩余补助（仅虎溪校区拥有）"""
    subsidies: Optional[float]
    """补助余额（仅老校区拥有）"""

    @staticmethod
    def from_dict(data: dict[str, Any], is_huxi: bool) -> EnergyFees:
        """从反序列化的（一个）水电费 json 中获取水电费信息

        :param data: json 反序列化得到的字典
        :type data: dict[str, Any]
        :param is_huxi: 目标寝室是否在虎溪校区
        :type is_huxi: bool
        :return: 学期信息对象
        :rtype: EnergyFees
        """
        if is_huxi:
            return EnergyFees(
                balance=data["剩余金额"],
                electricity_subsidy=data["电剩余补助"],
                water_subsidy=data["水剩余补助"],
                subsidies=None,
            )
        else:
            return EnergyFees(
                balance=data["现金余额"],
                electricity_subsidy=None,
                water_subsidy=None,
                subsidies=data["补贴余额"],
            )

    @staticmethod
    def fetch(session: Session, is_huxi: bool, room: str) -> EnergyFees:
        """从 card.cqu.edu.cn 上获取当前水电费信息，需要登录了统一身份认证的会话

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 card.cqu.edu.cn 进行了认证（:func:`.card.access_card`）的 requests 会话
        :type session: Session
        :param is_huxi: 房间号是否为虎溪校区的房间
        :type is_huxi: bool
        :param room: 需要获取水电费详情的宿舍
        :type room: str
        :raises NetworkError: 当访问相关网页时statue code不为200时抛出
        :raises TicketGetError: 当未能从网页对应位置中获取到ticket时抛出
        :raises ParseError: 当从返回数据解析所需值失败时抛出
        :raises CQUWebsiteError: 当网页获取水电费状态码不为success时抛出
        :return: 返回相关宿舍的水电费信息
        :rtype: EnergyFees
        """
        return EnergyFees.from_dict(get_fees_raw(session, is_huxi, room)["map"]["showData"], is_huxi)
