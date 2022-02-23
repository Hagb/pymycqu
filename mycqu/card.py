"""
校园卡余额、水电费查询相关模块
"""
from __future__ import annotations

import requests
from requests import Session
import json
from typing import Any, Dict, Optional, Tuple, List, Union, ClassVar
from ._lib_wrapper.dataclass import dataclass
from html.parser import HTMLParser

__all__ = ("EnergyFees",)

LOGIN_URL = 'http://authserver.cqu.edu.cn/authserver/login?service=http://card.cqu.edu.cn:7280/ias/prelogin?sysid=FWDT'

# 缴费大厅页面的不同缴费项目的id不同，虎溪和老校区不同
FEE_ITEM_ID = {'Huxi': '182',
               'Old': '181'}


class NetworkError(Exception):
    """
    当访问相关网页时statue code不为200时抛出
    """


class TicketGetError(Exception):
    """
    当未能从网页对应位置中获取到ticket时抛出
    """


class ParseError(Exception):
    """
    当从返回数据解析所需值失败时抛出
    """


class FeeAcquisitionFailed(Exception):
    """
    当网页获取水电费状态码不为success时抛出
    """
    def __init__(self, error_msg):
        super().__init__("获取水电费发生异常，返回状态：" + error_msg)


class CardPageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._starttag: bool = False
        self.ssoticket_id: str = ""

    def handle_starttag(self, tag, attrs):
        if not self._starttag and tag == 'input' and ('name', 'ssoticketid') in attrs:
            self._starttag = True
            for key, val in attrs:
                if key == "value":
                    self.ssoticket_id = val
                    break


def get_fees_info_raw(session: Session, isHuxi: bool, room: str):
    """ 从card.cqu.edu.cn获取水电费详情

    :param session: 登录了统一身份认证（:func:`.auth.login`）的 requests 会话
    :type session: Session
    :param isHuxi: 房间号是否为虎溪校区的房间
    :type isHuxi: bool
    :param room: 需要获取水电费详情的宿舍
    :type room: str
    :raises NetworkError: 当访问相关网页时statue code不为200时抛出
    :raises TicketGetError: 当未能从网页对应位置中获取到ticket时抛出
    :raises ParseError: 当从返回数据解析所需值失败时抛出
    :raises FeeAcquisitionFailed: 当网页获取水电费状态码不为success时抛出
    :return: 反序列化获取水电费信息的json
    :rtype: dict
    """
    res = session.get(LOGIN_URL)

    # 获取ssoticketid
    parser = CardPageParser()
    parser.feed(res.text)
    ssoticket_id = parser.ssoticket_id
    get_hall_ticket(session, ssoticket_id)
    ticket = get_ticket(session)
    synjones_auth = get_synjones_auth(ticket)
    return get_fee_data(synjones_auth, room, FEE_ITEM_ID['Huxi'] if isHuxi else FEE_ITEM_ID['Old'])


@dataclass
class EnergyFees:
    """
    某宿舍的水电费相关信息
    """
    balance: float
    """账户余额"""
    electricity_subsidy: float
    """电剩余补助"""
    water_subsidy: float
    """水剩余补助"""

    @staticmethod
    def from_dict(data: dict[str, Any]) -> EnergyFees:
        """从反序列化的（一个）水电费 json 中获取水电费信息

        :param data: json 反序列化得到的字典
        :type data: dict[str, Any]
        :return: 学期信息对象
        :rtype: EnergyFees
        """
        return EnergyFees(
            balance=data["剩余金额"],
            electricity_subsidy=data["电剩余补助"],
            water_subsidy=data["水剩余补助"]
        )

    @staticmethod
    def fetch(session: Session, isHuxi: bool, room: str) -> EnergyFees:
        """从 card.cqu.edu.cn 上获取当前水电费信息，需要登录了统一身份认证的会话

        :param session: 登录了统一身份认证（:func:`.auth.login`）的 requests 会话
        :type session: Session
        :raises NetworkError: 当访问相关网页时statue code不为200时抛出
        :raises TicketGetError: 当未能从网页对应位置中获取到ticket时抛出
        :raises ParseError: 当从返回数据解析所需值失败时抛出
        :raises FeeAcquisitionFailed: 当网页获取水电费状态码不为success时抛出
        :return: 返回相关宿舍的水电费信息
        :rtype: EnergyFees
        """
        return EnergyFees.from_dict(get_fees_info_raw(session, isHuxi, room)["map"]["showData"])


# 获取hallticket
def get_hall_ticket(session, ssoticket_id):
    url = 'http://card.cqu.edu.cn/cassyno/index'
    data = {
        'errorcode': '1',
        'continueurl': 'http://card.cqu.edu.cn/cassyno/index',
        'ssoticketid': ssoticket_id,
    }
    r = session.post(url, data=data)
    if r.status_code != 200:
        raise NetworkError()
    return session


# 利用登录之后的cookie获取一卡通的关键ticket
def get_ticket(session):
    url = 'http://card.cqu.edu.cn/Page/Page'
    data = {
        'EMenuName': '电费、网费',
        'MenuName': '电费、网费',
        'Url': 'http%3a%2f%2fcard.cqu.edu.cn%3a8080%2fblade-auth%2ftoken%2fthirdToToken%2ffwdt',
        'apptype': '4',
        'flowID': '10002'
    }
    r = session.post(url, data=data)
    if r.status_code != 200:
        raise NetworkError()
    ticket_start = r.text.find('ticket=')
    if ticket_start > 0:
        ticket_end = r.text.find("'", ticket_start)
        ticket = r.text[ticket_start + len('ticket='): ticket_end]
        return ticket
    else:
        raise TicketGetError()


# 利用ticket获取一卡通关键cookie
def get_synjones_auth(ticket):
    url = 'http://card.cqu.edu.cn:8080/blade-auth/token/fwdt'
    data = {'ticket': ticket}
    r = requests.post(url, data=data)
    if r.status_code != 200:
        raise NetworkError()
    try:
        dic = json.loads(r.text)
        token = dic['data']['access_token']
    except:
        raise ParseError()
    else:
        return 'bearer ' + token


# 利用关键cookie获取水电费dic
def get_fee_data(synjones_auth, room, fee_item_id):
    url = "http://card.cqu.edu.cn:8080/charge/feeitem/getThirdData"
    data = {
        'feeitemid': fee_item_id,
        'json': 'true',
        'level': '2',
        'room': room,
        'type': 'IEC',
    }
    cookie = {'synjones-auth': synjones_auth}
    r = requests.post(url, data=data, cookies=cookie)
    if r.status_code != 200:
        raise NetworkError()
    dic = json.loads(r.text)
    if dic['msg'] == 'success':
        return dic
    else:
        raise FeeAcquisitionFailed(dic['msg'])

