import json
import datetime

from requests import Session

from ._help import _get_ticket, _get_synjones_auth, _get_fee_data, _CardPageParser, _get_hall_ticket
from ..exception import CQUWebsiteError
from ..auth import access_service, async_access_service
from ..utils.datetimes import TIMEZONE
from ..utils.request_transformer import Request, RequestTransformer

# 缴费大厅页面的不同缴费项目的id不同，虎溪和老校区不同
FEE_ITEM_ID = {'Huxi': '182',
               'Old': '181'}

LOGIN_URL = 'http://card.cqu.edu.cn:7280/ias/prelogin?sysid=FWDT'

__all__ = ['get_fees_raw', 'get_card_raw', 'get_bill_raw', 'access_card',
           'async_get_fees_raw', 'async_get_card_raw', 'async_get_bill_raw', 'async_access_card']


def access_card(session: Request):
    """用登陆了统一身份认证的会话在 card.cqu.edu.cn 进行认证

    :param session: 登陆了统一身份认证的会话
    :type session: Session
    """
    res = access_service(session, LOGIN_URL)
    res = session.get(res.headers["Location"])

    parser = _CardPageParser()
    parser.feed(res.text)
    ssoticket_id = parser.ssoticket_id
    _get_hall_ticket.sync_request(session, ssoticket_id)

async def async_access_card(session: Request):
    """
    异步的用登陆了统一身份认证的会话在 card.cqu.edu.cn 进行认证

    :param session: 登陆了统一身份认证的会话
    :type session: Session
    """
    res = await async_access_service(session, LOGIN_URL)
    res = await session.get(res.headers["Location"])

    parser = _CardPageParser()
    parser.feed(res.text)
    ssoticket_id = parser.ssoticket_id
    await _get_hall_ticket.async_request(session, ssoticket_id)

@RequestTransformer.register()
def _get_fees_raw(session: Request, is_huxi: bool, room: str):
    ticket = yield _get_ticket
    synjones_auth = yield _get_synjones_auth, {'ticket': ticket}
    return (yield _get_fee_data, {'synjones_auth': synjones_auth, 'room': room,
                                  'fee_item_id': FEE_ITEM_ID['Huxi'] if is_huxi else FEE_ITEM_ID['Old']})

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
    return _get_fees_raw.sync_request(session, is_huxi, room)

async def async_get_fees_raw(session: Request, is_huxi: bool, room: str):
    """
    异步的从card.cqu.edu.cn获取水电费详情

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
    return await _get_fees_raw.async_request(session, is_huxi, room)

@RequestTransformer.register()
def _get_card_raw(session: Request):
    url = "http://card.cqu.edu.cn/NcAccType/GetCurrentAccountList"

    res = yield session.post(url)
    result = json.loads(json.loads(res.text))
    if result['respCode'] != "0000":
        raise CQUWebsiteError(error_msg=result['respInfo'])

    return result['objs'][0]

def get_card_raw(session: Session):
    """
    从card.cqu.edu.cn获取校园卡信息

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 card.cqu.edu.cn 进行了认证（:func:`.card.access_card`）的 requests 会话
    :type session: Session
    :raises CQUWebsiteError: 当网页获取状态码不为0000时抛出
    :return: 获取的校园卡信息
    :rtype: dict
    """
    return _get_card_raw.sync_request(session)

async def async_get_card_raw(session: Session):
    """
    异步的从card.cqu.edu.cn获取校园卡信息

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 card.cqu.edu.cn 进行了认证（:func:`.card.access_card`）的 requests 会话
    :type session: Session
    :raises CQUWebsiteError: 当网页获取状态码不为0000时抛出
    :return: 获取的校园卡信息
    :rtype: dict
    """
    return await _get_card_raw.async_request(session)

@RequestTransformer.register()
def _get_bill_raw(session: Session, account: int, duration: int):
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

    res = yield session.post(url=url, data=data)
    result = json.loads(res.text)

    return result['rows']

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
    return _get_bill_raw.sync_request(session, account, duration)

async def async_get_bill_raw(session: Session, account: int, duration: int):
    """
    异步的从card.cqu.edu.cn获取校园卡账单

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 card.cqu.edu.cn 进行了认证（:func:`.card.access_card`）的 requests 会话
    :type session: Session
    :param account: 校园卡卡号
    :type account: int
    :param duration: 查询时间间隔(默认为30天)
    :type duration: int
    :return: 获取的校园卡账单信息
    :rtype: dict
    """
    return await _get_bill_raw.async_request(session, account, duration)
