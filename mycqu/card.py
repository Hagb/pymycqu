"""
校园卡余额、水电费查询相关模块
"""
from __future__ import annotations


import json
import datetime
from typing import Any, List, Optional
from html.parser import HTMLParser
import requests
from requests import Session
from ._lib_wrapper.dataclass import dataclass
from .utils.datetimes import TIMEZONE
from .exception import TicketGetError, ParseError, CQUWebsiteError
from .auth import access_service

__all__ = ("EnergyFees", "Bill", "Card", "access_card")

# 缴费大厅页面的不同缴费项目的id不同，虎溪和老校区不同
FEE_ITEM_ID = {'Huxi': '182',
               'Old': '181'}

LOGIN_URL = 'http://card.cqu.edu.cn:7280/ias/prelogin?sysid=FWDT'


def get_fees_raw(session: Session, is_huxi: bool, room: str):
    """
    从card.cqu.edu.cn获取水电费详情

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
    :return: 反序列化获取水电费信息的json
    :rtype: dict
    """
    ticket = _get_ticket(session)
    synjones_auth = _get_synjones_auth(ticket)
    return get_fee_data(synjones_auth, room, FEE_ITEM_ID['Huxi'] if is_huxi else FEE_ITEM_ID['Old'])


def get_card_raw(session):
    """
    从card.cqu.edu.cn获取校园卡信息

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 card.cqu.edu.cn 进行了认证（:func:`.card.access_card`）的 requests 会话
    :type session: Session
    :raises CQUWebsiteError: 当网页获取状态码不为0000时抛出
    :return: 获取的校园卡信息
    :rtype: dict
    """
    url = "http://card.cqu.edu.cn/NcAccType/GetCurrentAccountList"

    res = session.post(url)
    result = json.loads(json.loads(res.text))
    if result['respCode'] != "0000":
        raise CQUWebsiteError(error_msg=result['respInfo'])

    return result['objs'][0]


def get_bill_raw(session: Session, account: int, duration: int):
    """
    从card.cqu.edu.cn获取校园卡账单

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 card.cqu.edu.cn 进行了认证（:func:`.card.access_card`）的 requests 会话
    :type session: Session
    :param account: 校园卡卡号
    :type account: int
    :param duration: 查询时间间隔(默认为30天)
    :type duration: int
    :return: 获取的校园卡账单信息
    :rtype: dict
    """
    url = 'http://card.cqu.edu.cn/NcReport/GetMyBill'

    end_date = datetime.datetime.now(tz=TIMEZONE)
    start_date = end_date - datetime.timedelta(duration)

    data = {
        'sdate': start_date.strftime('%Y-%m-%d'),
        'edate': end_date.strftime('%Y-%m-%d'),
        'account': account,
        'page': 1,
        'row': 100,
    }

    res = session.post(url=url, data=data)
    result = json.loads(res.text)

    return result['rows']


def access_card(session):
    """用登陆了统一身份认证的会话在 card.cqu.edu.cn 进行认证

    :param session: 登陆了统一身份认证的会话
    :type session: Session
    """
    res = access_service(session, LOGIN_URL)
    res = session.get(res.headers["Location"])

    parser = _CardPageParser()
    parser.feed(res.text)
    ssoticket_id = parser.ssoticket_id
    _get_hall_ticket(session, ssoticket_id)


class _CardPageParser(HTMLParser):
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


# 获取hallticket
def _get_hall_ticket(session, ssoticket_id):
    url = 'http://card.cqu.edu.cn/cassyno/index'
    data = {
        'errorcode': '1',
        'continueurl': 'http://card.cqu.edu.cn/cassyno/index',
        'ssoticketid': ssoticket_id,
    }
    r = session.post(url, data=data)
    if r.status_code != 200:
        raise CQUWebsiteError()
    return session


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


@dataclass
class Card:
    """
    校园卡及其账单信息
    """
    card_id: int
    """校园卡id"""
    amount: float
    """账户余额"""

    @staticmethod
    def fetch(session: Session) -> Card:
        """
        从card.cqu.edu.cn获取校园卡信息

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 card.cqu.edu.cn 进行了认证（:func:`.card.access_card`）的 requests 会话
        :type session: Session
        :raises CQUWebsiteError: 当网页获取状态码不为0000时抛出
        :return: 获取的校园卡信息
        :rtype: Card
        """
        card_info = get_card_raw(session)

        return Card(
            card_id=int(card_info['acctNo']),
            amount=float(card_info['acctAmt'] / 100)
        )

    def fetch_bills(self, session: Session) -> List[Bill]:
        """
        从card.cqu.edu.cn获取校园卡账单

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 card.cqu.edu.cn 进行了认证（:func:`.card.access_card`）的 requests 会话
        :type session: Session
        :return: 获取的校园卡账单信息
        :rtype: dict
        """
        bill_info = get_bill_raw(session, self.card_id, 30)
        bills = []
        for bill in bill_info:
            bills.append(Bill.from_dict(bill))

        return bills


# 利用登录之后的cookie获取一卡通的关键ticket
def _get_ticket(session):
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
        raise CQUWebsiteError()
    ticket_start = r.text.find('ticket=')
    if ticket_start > 0:
        ticket_end = r.text.find("'", ticket_start)
        ticket = r.text[ticket_start + len('ticket='): ticket_end]
        return ticket
    else:
        raise TicketGetError()


# 利用ticket获取一卡通关键cookie
def _get_synjones_auth(ticket):
    url = 'http://card.cqu.edu.cn:8080/blade-auth/token/fwdt'
    data = {'ticket': ticket}
    r = requests.post(url, data=data)
    if r.status_code != 200:
        raise CQUWebsiteError()
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
        raise CQUWebsiteError()
    dic = json.loads(r.text)
    if dic['msg'] == 'success':
        return dic
    else:
        raise CQUWebsiteError(dic['msg'])


# 获取校园卡账号信息
