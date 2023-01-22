"""
统一身份认证相关的模块
"""

from typing import Optional, Callable, Generic
from requests import Session, Response

from ._authserver import *
from ._sso import *
from ..exception import NeedCaptcha, InvaildCaptcha
from ..utils.request_transformer import Request


__all__ = ['is_logined', 'logout', 'access_service', 'login',
           'async_is_logined', 'async_logout', 'async_access_service', 'async_login']


def is_logined(session: Session, use_sso: bool = True) -> bool:
    """判断是否处于统一身份认证登陆状态

    :param session: 会话
    :type session: Session
    :param use_sso: 是否使用 sso 而非 authserver, 默认为 :obj::`True`
    :type use_sso: bool, optional
    :return: :obj:`True` 如果处于登陆状态，:obj:`False` 如果处于未登陆或登陆过期状态
    :rtype: bool
    """
    return is_sso_logined(session) if use_sso else is_authserver_logined(session)

async def async_is_logined(session: Generic[Request], use_sso: bool = True) -> bool:
    """
    异步的判断是否处于统一身份认证登陆状态

    :param session: 会话
    :type session: Session
    :param use_sso: 是否使用 sso 而非 authserver, 默认为 :obj::`True`
    :type use_sso: bool, optional
    :return: :obj:`True` 如果处于登陆状态，:obj:`False` 如果处于未登陆或登陆过期状态
    :rtype: bool
    """
    return await async_is_sso_logined(session) if use_sso else await async_is_authserver_logined(session)


def logout(session: Session, use_sso: bool = True) -> None:
    """注销统一身份认证登录状态

    :param session: 进行过登录的会话
    :type session: Session
    :param use_sso: 是否使用 sso 而非 authserver, 默认为 :obj::`True`
    :type use_sso: bool, optional
    """
    logout_sso(session) if use_sso else logout_authserver(session)

async def async_logout(session: Generic[Request], use_sso: bool = True) -> None:
    """
    异步的注销统一身份认证登录状态

    :param session: 进行过登录的会话
    :type session: Session
    :param use_sso: 是否使用 sso 而非 authserver, 默认为 :obj::`True`
    :type use_sso: bool, optional
    """
    await async_logout_sso(session) if use_sso else await async_logout_authserver(session)


def access_service(session: Session, service: str, use_sso: bool = True) -> Response:
    """从登录了统一身份认证的会话获取指定服务的许可

    :param session: 登录了统一身份认证的会话
    :type session: Session
    :param service: 服务的 url
    :type service: str
    :param use_sso: 是否使用 sso 而非 authserver, 默认为 :obj::`True`
    :type use_sso: bool, optional
    :raises NotLogined: 统一身份认证未登录时抛出
    :return: 访问服务 url 的 :class:`Response`
    :rtype: Response
    """
    return access_sso_service(session, service) if use_sso else access_authserver_service(session, service)

async def async_access_service(session: Generic[Request], service: str, use_sso: bool = True) -> Response:
    """
    异步的从登录了统一身份认证的会话获取指定服务的许可

    :param session: 登录了统一身份认证的会话
    :type session: Session
    :param service: 服务的 url
    :type service: str
    :param use_sso: 是否使用 sso 而非 authserver, 默认为 :obj::`True`
    :type use_sso: bool, optional
    :raises NotLogined: 统一身份认证未登录时抛出
    :return: 访问服务 url 的 :class:`Response`
    :rtype: Response
    """
    return await async_access_sso_service(session, service) if use_sso else await async_access_authserver_service(session, service)


def login(session: Session,
          username: str,
          password: str,
          service: Optional[str] = None,
          timeout: int = 10,
          force_relogin: bool = False,
          captcha_callback: Optional[
              Callable[[bytes, str], Optional[str]]] = None,
          keep_longer: bool = False,
          kick_others: bool = False,
          use_sso: bool = True
          ) -> Response:
    """登录统一身份认证

    :param session: 用于登录统一身份认证的会话
    :type session: Session
    :param username: 统一身份认证号或学工号
    :type username: str
    :param password: 统一身份认证密码
    :type password: str
    :param service: 需要登录的服务，默认（:obj:`None`）则先不登陆任何服务
    :type service: Optional[str], optional
    :param timeout: 连接超时时限，默认为 10（单位秒）
    :type timeout: int, optional
    :param force_relogin: 强制重登，当会话中已经有有效的登陆 cookies 时依然重新登录，默认为 :obj:`False`
    :type force_relogin: bool, optional
    :param captcha_callback: 需要输入验证码时调用的回调函数，默认为 :obj:`None` 即不设置回调；
                             当需要输入验证码，但回调没有设置或回调返回 :obj:`None` 时，抛出异常 :class:`NeedCaptcha`；
                             该函数接受一个 :class:`bytes` 型参数为验证码图片的文件数据，一个 :class:`str` 型参数为图片的 MIME 类型，
                             返回验证码文本或 :obj:`None`。
    :type captcha_callback: Optional[Callable[[bytes, str], Optional[str]]], optional
    :param keep_longer: 保持更长时间的登录状态（保持一周）
    :type keep_longer: bool
    :param kick_others: 当目标用户开启了“单处登录”并有其他登录会话时，踢出其他会话并登录单前会话；若该参数为 :obj:`False` 则抛出
                       :class:`MultiSessionConflict`
    :type kick_others: bool
    :param use_sso: 是否使用 sso 而非 authserver, 默认为 :obj::`True`
    :type use_sso: bool, optional
    :raises UnknownAuthserverException: 未知认证错误
    :raises InvaildCaptcha: 无效的验证码
    :raises IncorrectLoginCredentials: 错误的登陆凭据（如错误的密码、用户名）
    :raises NeedCaptcha: 需要提供验证码，获得验证码文本之后可调用所抛出异常的 :func:`NeedCaptcha.after_captcha` 函数来继续登陆
    :raises MultiSessionConflict: 和其他会话冲突
    :return: 登陆了统一身份认证后所跳转到的地址的 :class:`Response`
    :rtype: Response
    """
    try:
        return login_sso(session, username, password, service, timeout, force_relogin) \
            if use_sso else login_authserver(session, username, password, service, timeout, force_relogin, keep_longer,
                                             kick_others)
    except NeedCaptcha as e:
        if captcha_callback is None:
            raise e
        else:
            captcha_str = captcha_callback(e.image, e.image_type)
            if captcha_str is None:
                raise InvaildCaptcha()
            else:
                return e.after_captcha(captcha_str)

async def async_login(session: Generic[Request],
          username: str,
          password: str,
          service: Optional[str] = None,
          timeout: int = 10,
          force_relogin: bool = False,
          captcha_callback: Optional[
              Callable[[bytes, str], Optional[str]]] = None,
          keep_longer: bool = False,
          kick_others: bool = False,
          use_sso: bool = True
          ) -> Response:
    """
    异步的登录统一身份认证

    :param session: 用于登录统一身份认证的会话
    :type session: Session
    :param username: 统一身份认证号或学工号
    :type username: str
    :param password: 统一身份认证密码
    :type password: str
    :param service: 需要登录的服务，默认（:obj:`None`）则先不登陆任何服务
    :type service: Optional[str], optional
    :param timeout: 连接超时时限，默认为 10（单位秒）
    :type timeout: int, optional
    :param force_relogin: 强制重登，当会话中已经有有效的登陆 cookies 时依然重新登录，默认为 :obj:`False`
    :type force_relogin: bool, optional
    :param captcha_callback: 需要输入验证码时调用的回调函数，默认为 :obj:`None` 即不设置回调；
                             当需要输入验证码，但回调没有设置或回调返回 :obj:`None` 时，抛出异常 :class:`NeedCaptcha`；
                             该函数接受一个 :class:`bytes` 型参数为验证码图片的文件数据，一个 :class:`str` 型参数为图片的 MIME 类型，
                             返回验证码文本或 :obj:`None`。
    :type captcha_callback: Optional[Callable[[bytes, str], Optional[str]]], optional
    :param keep_longer: 保持更长时间的登录状态（保持一周）
    :type keep_longer: bool
    :param kick_others: 当目标用户开启了“单处登录”并有其他登录会话时，踢出其他会话并登录单前会话；若该参数为 :obj:`False` 则抛出
                       :class:`MultiSessionConflict`
    :type kick_others: bool
    :param use_sso: 是否使用 sso 而非 authserver, 默认为 :obj::`True`
    :type use_sso: bool, optional
    :raises UnknownAuthserverException: 未知认证错误
    :raises InvaildCaptcha: 无效的验证码
    :raises IncorrectLoginCredentials: 错误的登陆凭据（如错误的密码、用户名）
    :raises NeedCaptcha: 需要提供验证码，获得验证码文本之后可调用所抛出异常的 :func:`NeedCaptcha.after_captcha` 函数来继续登陆
    :raises MultiSessionConflict: 和其他会话冲突
    :return: 登陆了统一身份认证后所跳转到的地址的 :class:`Response`
    :rtype: Response
    """
    try:
        return await async_login_sso(session, username, password, service, timeout, force_relogin) \
            if use_sso else await async_login_authserver(session, username, password, service, timeout, force_relogin, keep_longer,
                                             kick_others)
    except NeedCaptcha as e:
        if captcha_callback is None:
            raise e
        else:
            captcha_str = captcha_callback(e.image, e.image_type)
            if captcha_str is None:
                raise InvaildCaptcha()
            else:
                return e.after_captcha(captcha_str)
