from base64 import b64encode, b64decode
from typing import Optional, Dict, Generic

from requests import Session

from ..utils.request_transformer import RequestTransformer, Request, Response
from ..exception import IncorrectLoginCredentials, InvaildCaptcha, UnknownAuthserverException
from .._lib_wrapper.encrypt import des_ecb_encryptor, pad8
from ._page_parser import _SSOPageParser, _SSOErrorParser
from ._authorizer import Authorizer

_SSO_CAPTCHA_ERROR_CODE = 1320007
_SSO_ERROR_CODES = {1030027: '用户名或密码错误，请确认后重新输入',
                    1030031: '用户名或密码错误，请确认后重新输入',
                    1410041: '当前用户名已失效',
                    1410040: '当前用户名已失效',
                    1320007: '验证码有误，请确认后重新输入'}

__all__ = ['is_sso_logined', 'logout_sso', 'access_sso_service', 'login_sso',
           'async_is_sso_logined', 'async_logout_sso', 'async_access_sso_service', 'async_login_sso']

def is_sso_logined(session: Session) -> bool:
    """判断是否处于统一身份认证（sso）登陆状态

    :param session: 会话
    :type session: Session
    :return: :obj:`True` 如果处于登陆状态，:obj:`False` 如果处于未登陆或登陆过期状态
    :rtype: bool
    """
    return SSOAuthorizer[Session].is_logined(session)

async def async_is_sso_logined(session: Request) -> bool:
    """
    异步的判断是否处于统一身份认证（sso）登陆状态

    :param session: 会话
    :type session: Session
    :return: :obj:`True` 如果处于登陆状态，:obj:`False` 如果处于未登陆或登陆过期状态
    :rtype: bool
    """
    return await SSOAuthorizer.async_is_logined(session)

def logout_sso(session: Session) -> None:
    """注销统一身份认证（sso）登录状态

    :param session: 进行过登录的会话
    :type session: Session
    """
    return SSOAuthorizer[Session].logout(session)

async def async_logout_sso(session: Request) -> None:
    """
    异步的注销统一身份认证（sso）登录状态

    :param session: 进行过登录的会话
    :type session: Session
    """
    return await SSOAuthorizer.async_logout(session)

def access_sso_service(session: Session, service: str) -> Response:
    """从登录了统一身份认证（sso）的会话获取指定服务的许可

    :param session: 登录了统一身份认证的会话
    :type session: Session
    :param service: 服务的 url
    :type service: str
    :raises NotLogined: 统一身份认证未登录时抛出
    :return: 访问服务 url 的 :class:`Response`
    :rtype: Response
    """
    return SSOAuthorizer[Session].access_service(session, service)

async def async_access_sso_service(session: Request, service: str) -> Response:
    """
    异步的从登录了统一身份认证（sso）的会话获取指定服务的许可

    :param session: 登录了统一身份认证的会话
    :type session: Session
    :param service: 服务的 url
    :type service: str
    :raises NotLogined: 统一身份认证未登录时抛出
    :return: 访问服务 url 的 :class:`Response`
    :rtype: Response
    """
    return await SSOAuthorizer.async_access_service(session, service)


class SSOAuthorizer(Authorizer, Generic[Request]):
    def __init__(self,
                 session: Request,
                 username: str,
                 password: str,
                 service: Optional[str] = None,
                 timeout: int = 10,
                 force_relogin: bool = False,
                 keep_longer: bool = False,
                 kick_others: bool = False):

        super().__init__(session, username, password, service, timeout, force_relogin, keep_longer, kick_others)

        self._login_res = None
        self._page_data = None

    LOGIN_URL = "https://sso.cqu.edu.cn/login"
    LOGOUT_URL = "https://sso.cqu.edu.cn/logout"
    ROOT_URL = "https://sso.cqu.edu.cn"

    @RequestTransformer.register()
    def _get_request_data(self, session: Request) -> Dict:
        resp = yield session.get(
            self.LOGIN_URL,
            params=self.service and {"service": self.service},
            allow_redirects=False,
            timeout=self.timeout
        )
        if resp.status_code == 302:
            if self.force_relogin:
                yield self._logout
                resp = yield session.get(self.LOGIN_URL, timeout=self.timeout)
            else:
                self._login_res = yield session.get(resp.headers['Location'], allow_redirects=False, timeout=self.timeout)
                return {}
        if resp.status_code != 200:
            UnknownAuthserverException(
                f"status code {resp.status_code} is got (302 expected) when sending login post, "
                "but can not find the element span.login_auth_error#msg")

        page_data = _SSOPageParser().parse(resp.text)
        croypto = page_data['login-croypto']
        passwd_encrypted = b64encode(des_ecb_encryptor(b64decode(croypto))(pad8(self.password.encode())))
        passwd_encrypted = str(passwd_encrypted, encoding='utf-8')
        request_data = {
            'username': self.username,
            'type': 'UsernamePassword',
            '_eventId': 'submit',
            'geolocation': '',
            'execution': page_data['login-page-flowkey'],
            'croypto': croypto,
            'password': passwd_encrypted
        }

        return request_data

    @RequestTransformer.register()
    def _need_captcha(self, session: Request) -> Optional[str]:
        if self._page_data is not None:
            return f"{self.ROOT_URL}/{self._page_data['captcha-url']}"

    def _need_captcha_handler(self, captcha: str, request_data: Dict):
        request_data['captcha_code'] = [captcha, captcha]

    @RequestTransformer.register()
    def _login(self, session: Request, request_data: Dict) -> Response:
        if self._login_res is not None:
            return (yield session.get(self._login_res.headers['Location'], allow_redirects=False, timeout=self.timeout))

        login_resp = yield session.post(self.LOGIN_URL,
                                  params=self.service and {"service": self.service},
                                  data=request_data,
                                  allow_redirects=False,
                                  timeout=self.timeout)
        if login_resp.status_code == 302:
            return (yield session.get(login_resp.headers['Location'], allow_redirects=False, timeout=self.timeout))
        elif login_resp.status_code == 401:
            raise IncorrectLoginCredentials()
        elif login_resp.status_code == 200:
            error_code: Optional[int] = _SSOErrorParser().parse(login_resp.text)
            if error_code == _SSO_CAPTCHA_ERROR_CODE:
                raise InvaildCaptcha()
            elif error_code is None:
                raise UnknownAuthserverException("No error code")
            else:
                raise UnknownAuthserverException(
                    f"{error_code}: {_SSO_ERROR_CODES.get(error_code, '')}")


def login_sso(session: Session,
              username: str,
              password: str,
              service: Optional[str] = None,
              timeout: int = 10,
              force_relogin: bool = False
              ):
    """登录统一身份认证（sso）

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
    :raises InvaildCaptcha: 无效的验证码
    :raises IncorrectLoginCredentials: 错误的登陆凭据（如错误的密码、用户名）
    :raises NeedCaptcha: 需要提供验证码，获得验证码文本之后可调用所抛出异常的 :func:`NeedCaptcha.after_captcha` 函数来继续登陆
    :return: 登陆了统一身份认证后所跳转到的地址的 :class:`Response`
    :rtype: Response
    """
    return SSOAuthorizer[Session].login(session, username, password, service, timeout, force_relogin)

async def async_login_sso(session: Request,
              username: str,
              password: str,
              service: Optional[str] = None,
              timeout: int = 10,
              force_relogin: bool = False
              ):
    """
    异步的登录统一身份认证（sso）

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
    :raises InvaildCaptcha: 无效的验证码
    :raises IncorrectLoginCredentials: 错误的登陆凭据（如错误的密码、用户名）
    :raises NeedCaptcha: 需要提供验证码，获得验证码文本之后可调用所抛出异常的 :func:`NeedCaptcha.after_captcha` 函数来继续登陆
    :return: 登陆了统一身份认证后所跳转到的地址的 :class:`Response`
    :rtype: Response
    """
    return await SSOAuthorizer.async_login(session, username, password, service, timeout, force_relogin)
