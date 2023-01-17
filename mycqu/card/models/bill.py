from __future__ import annotations

import datetime
from typing import Any

from ...utils.datetimes import TIMEZONE
from ..._lib_wrapper.dataclass import dataclass


__all__ = ['Bill']


@dataclass
class Bill:
    """
    某次消费账单信息
    """
    tran_name: str
    """交易名称"""
    tran_date: datetime.datetime
    """交易时间"""
    tran_place: str
    """交易地点"""
    tran_amount: float
    """交易金额"""
    acc_amount: float
    """账户余额"""

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Bill:
        """
        从反序列化的（一个）账单 json 中获取账单信息

        :param data: json 反序列化得到的字典
        :type data: dict[str, Any]
        :return: 账单对象
        :rtype: Bill
        """
        return Bill(
            tran_name=data['tranName'],
            tran_date=datetime.datetime.strptime(
                data['tranDt'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=TIMEZONE),
            tran_place=data['mchAcctName'],
            tran_amount=float(data['tranAmt'] / 100),
            acc_amount=float(int(data['acctAmt']) / 100)
        )
