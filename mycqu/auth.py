"""统一身份认证相关的模块
"""
from typing import Dict, Optional, Callable
import random
import re
from base64 import b64encode, b64decode
from html.parser import HTMLParser
from requests import Session, Response
from ._lib_wrapper.encrypt import pad16, aes_cbc_encryptor, pad8, des_ecb_encryptor
from .exception import NotAllowedService, NeedCaptcha, InvaildCaptcha, IncorrectLoginCredentials, \
    UnknownAuthserverException, NotLogined, MultiSessionConflict, ParseError

__all__ = ("is_sso_logined", "is_authserver_logined", 'is_logined',
           "logout_sso", "logout_authserver", 'logout',
           "access_sso_service", "access_authserver_service", 'access_service',
           "login_sso", "login_authserver", 'login')


AUTHSERVER_URL = "http://authserver.cqu.edu.cn/authserver/login"
AUTHSERVER_CAPTCHA_DETERMINE_URL = "http://authserver.cqu.edu.cn/authserver/needCaptcha.html"
AUTHSERVER_CAPTCHA_IMAGE_URL = "http://authserver.cqu.edu.cn/authserver/captcha.html"
AUTHSERVER_LOGOUT_URL = "http://authserver.cqu.edu.cn/authserver/logout"
SSO_ROOT_URL = "https://sso.cqu.edu.cn"
SSO_LOGIN_URL = "https://sso.cqu.edu.cn/login"
SSO_LOGOUT_URL = "https://sso.cqu.edu.cn/logout"
_CHAR_SET = 'ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678'
_SSO_CAPTCHA_ERROR_CODE = 1320007
_SSO_ERROR_CODES = {1030027: '用户名或密码错误，请确认后重新输入',
                    1030031: '用户名或密码错误，请确认后重新输入',
                    1410041: '当前用户名已失效',
                    1410040: '当前用户名已失效',
                    1320007: '验证码有误，请确认后重新输入'}


def _random_str(length: int) -> str:
    return ''.join(random.choices(_CHAR_SET, k=length))


class _AuthPageParser(HTMLParser):
    _SALT_RE: re.Pattern = re.compile('var pwdDefaultEncryptSalt = "([^"]+)"')

    def __init__(self):
        super().__init__()
        self.input_data: Dict[str, Optional[str]] = \
            {'lt': None, 'dllt': None,
                'execution': None, '_eventId': None, 'rmShown': None}
        """几个关键的标签数据"""
        self.salt: Optional[str] = None
        """加密所用的盐"""
        self._js_start: bool = False
        self._js_end: bool = False
        self._error: bool = False
        self._error_head: bool = False

    def handle_starttag(self, tag, attrs):
        if tag == 'input':
            name: Optional[str] = None
            value: Optional[str] = None
            for attr in attrs:
                if attr[0] == 'name':
                    if attr[1] in self.input_data:
                        name = attr[1]
                    else:
                        break
                elif attr[0] == 'value':
                    value = attr[1]
            if name:
                self.input_data[name] = value
        elif tag == 'script' and attrs and attrs[0] == ("type", "text/javascript"):
            self._js_start = True
        elif tag == "div" and attrs == [("id", "msg"), ("class", "errors")]:
            self._error = True
        elif tag == 'h2' and self._error:
            self._error_head = True

    def handle_data(self, data):
        if self._js_start and not self._js_end:
            match = self._SALT_RE.search(data)
            if match:
                self.salt = match[1]
            self._js_end = True
        elif self._error_head:
            error_str = data.strip()
            if error_str == "应用未注册":
                raise NotAllowedService(error_str)
            raise UnknownAuthserverException(
                "Error message before login: "+error_str)


class _SSOPageParser(HTMLParser):
    _SALT_RE: re.Pattern = re.compile('var pwdDefaultEncryptSalt = "([^"]+)"')

    class _AllValuesGot(Exception):
        pass

    def __init__(self):
        super().__init__()
        self.data: Dict[str, Optional[str]] = {
            'login-croypto': None, 'login-page-flowkey': None, 'captcha-url': None}
        self._opened_tag: Optional[str] = None
        self._count = len(self.data)

    def parse(self, page: str) -> Dict[str, str]:
        try:
            self.feed(page)
        except self._AllValuesGot:
            pass
        assert not self._count
        return self.data  # type: ignore

    def handle_starttag(self, tag, attrs):
        if tag == 'p':
            for attr in attrs:
                if attr[0] == 'id':
                    if attr[1] in self.data:
                        self._opened_tag = attr[1]
                        assert self.data[attr[1]] is None
                    return

    def handle_data(self, data):
        if self._opened_tag is not None:
            self.data[self._opened_tag] = data.strip()
            self._opened_tag = None
            self._count -= 1
            if not self._count:
                raise self._AllValuesGot


class _SSOErrorParser(HTMLParser):
    class _ErrorGot(Exception):
        pass

    def __init__(self):
        super().__init__()
        self._error_code_str: str = ""
        self._error_div_opened: bool = False

    def parse(self, page: str) -> Optional[int]:
        try:
            self.feed(page)
        except self._ErrorGot:
            return int(self._error_code_str.strip())
        return None

    def handle_starttag(self, tag, attrs):
        if tag == 'div':
            if ("id", "login-error-msg") in attrs:
                self._error_div_opened = True

    def handle_endtag(self, tag):
        if self._error_div_opened and tag == 'div':
            raise self._ErrorGot

    def handle_data(self, data):
        if self._error_div_opened:
            self._error_code_str += data


class _LoginedPageParser(HTMLParser):
    MSG_ATTRS = [("id", "msg"), ("class", "login_auth_error")]
    KICK_TABLE_ATTRS = [("class", "kick_table")]
    KICK_POST_ATTRS = [('method', 'post'), ('id', 'continue')]
    CANCEL_POST_ATTRS = [('method', 'post'), ('id', 'cancel')]

    def __init__(self, status_code: int):
        super().__init__()
        self._msg: bool = False
        self._kick: bool = False
        self._waiting_kick_excution: bool = False
        self._kick_execution: str = ""
        self._waiting_cancel_excution: bool = False
        self._cancel_execution: str = ""
        self.status_code: int = status_code

    def handle_starttag(self, tag, attrs):
        if tag == "span" and attrs == self.MSG_ATTRS:
            self._msg = True
        elif tag == "table" and attrs == self.KICK_TABLE_ATTRS:
            self._kick = True
        elif tag == "form" and attrs == self.CANCEL_POST_ATTRS:
            self._waiting_cancel_excution = True
        elif tag == "form" and attrs == self.KICK_POST_ATTRS:
            self._waiting_kick_excution = True
        elif tag == "input" and ("name", "execution") in attrs:
            if self._waiting_kick_excution:
                for key, value in attrs:
                    if key == "value":
                        self._kick_execution = value
                        self._waiting_kick_excution = False
            elif self._waiting_cancel_excution:
                for key, value in attrs:
                    if key == "value":
                        self._cancel_execution = value
                        self._waiting_cancel_excution = False

    def handle_data(self, data):
        if self._msg:
            error_str = data.strip()
            if error_str == "无效的验证码":
                raise InvaildCaptcha()
            elif error_str == "您提供的用户名或者密码有误":
                raise IncorrectLoginCredentials()
            else:
                raise UnknownAuthserverException(
                    f"status code {self.status_code} is got (302 expected)"
                    f" when sending login post, {error_str}"
                )


def _get_formdata(html: str, username: str, password: str) -> Dict[str, Optional[str]]:
    # from https://github.com/CQULHW/CQUQueryGrade
    parser = _AuthPageParser()
    parser.feed(html)
    salt = parser.salt
    if not salt:
        ParseError("无法获取盐")
    assert salt
    passwd_pkcs7 = pad16((_random_str(64)+str(password)).encode())
    encryptor = aes_cbc_encryptor(salt.encode(), _random_str(16).encode())
    passwd_encrypted = b64encode(encryptor(passwd_pkcs7)).decode()
    parser.input_data['username'] = username
    parser.input_data['password'] = passwd_encrypted
    return parser.input_data


def is_authserver_logined(session: Session) -> bool:
    """判断是否处于统一身份认证（authserver）登陆状态

    :param session: 会话
    :type session: Session
    :return: :obj:`True` 如果处于登陆状态，:obj:`False` 如果处于未登陆或登陆过期状态
    :rtype: bool
    """
    return session.get(AUTHSERVER_URL, allow_redirects=False).status_code == 302


def is_sso_logined(session: Session) -> bool:
    """判断是否处于统一身份认证（sso）登陆状态

    :param session: 会话
    :type session: Session
    :return: :obj:`True` 如果处于登陆状态，:obj:`False` 如果处于未登陆或登陆过期状态
    :rtype: bool
    """
    return session.get(SSO_LOGIN_URL, allow_redirects=False).status_code == 302


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


def logout_authserver(session: Session) -> None:
    """注销统一身份认证登录（authserver）状态

    :param session: 进行过登录的会话
    :type session: Session
    """
    session.get(AUTHSERVER_LOGOUT_URL)


def logout_sso(session: Session) -> None:
    """注销统一身份认证（sso）登录状态

    :param session: 进行过登录的会话
    :type session: Session
    """
    session.get(SSO_LOGOUT_URL)


def logout(session: Session, use_sso: bool = True) -> None:
    """注销统一身份认证登录状态

    :param session: 进行过登录的会话
    :type session: Session
    :param use_sso: 是否使用 sso 而非 authserver, 默认为 :obj::`True`
    :type use_sso: bool, optional
    """
    logout_sso(session) if use_sso else logout_authserver(session)


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
    resp = session.get(SSO_LOGIN_URL,
                       params={"service": service},
                       allow_redirects=False)
    if resp.status_code != 302:
        # TODO
        raise NotLogined()
    return session.get(url=resp.headers['Location'], allow_redirects=False)


def access_authserver_service(session: Session, service: str) -> Response:
    """从登录了统一身份认证（authserver）的会话获取指定服务的许可

    :param session: 登录了统一身份认证的会话
    :type session: Session
    :param service: 服务的 url
    :type service: str
    :raises NotLogined: 统一身份认证未登录时抛出
    :return: 访问服务 url 的 :class:`Response`
    :rtype: Response
    """
    resp = session.get(AUTHSERVER_URL,
                       params={"service": service},
                       allow_redirects=False)
    if resp.status_code != 302:
        _AuthPageParser().feed(resp.text)
        raise NotLogined()
    return session.get(url=resp.headers['Location'], allow_redirects=False)


def access_service(session: Session, service: str, use_sso: bool = True) -> Response:
    """从登录了统一身份认证（authserver）的会话获取指定服务的许可

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


def login_authserver(session: Session,
                     username: str,
                     password: str,
                     service: Optional[str] = None,
                     timeout: int = 10,
                     force_relogin: bool = False,
                     captcha_callback: Optional[
                         Callable[[bytes, str], Optional[str]]] = None,
                     keep_longer: bool = False,
                     kick_others: bool = False
                     ) -> Response:
    """登录统一身份认证（authserver）

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
    :raises UnknownAuthserverException: 未知认证错误
    :raises InvaildCaptcha: 无效的验证码
    :raises IncorrectLoginCredentials: 错误的登陆凭据（如错误的密码、用户名）
    :raises NeedCaptcha: 需要提供验证码，获得验证码文本之后可调用所抛出异常的 :func:`NeedCaptcha.after_captcha` 函数来继续登陆
    :raises MultiSessionConflict: 和其他会话冲突
    :return: 登陆了统一身份认证后所跳转到的地址的 :class:`Response`
    :rtype: Response
    """
    def get_login_page():
        return session.get(
            url=AUTHSERVER_URL,
            params=None if service is None else {"service": service},
            allow_redirects=False,
            timeout=timeout)
    login_page = get_login_page()
    if login_page.status_code == 302:
        if not force_relogin:
            return login_page
        else:
            logout_authserver(session)
            login_page = get_login_page()
    elif login_page.status_code != 200:
        raise UnknownAuthserverException()
    try:
        formdata = _get_formdata(login_page.text, username, password)
    except ParseError:
        logout_authserver(session)
        formdata = _get_formdata(get_login_page().text, username, password)
    if keep_longer:
        formdata['rememberMe'] = 'on'

    def after_captcha(captcha_str: Optional[str]):
        if captcha_str is None:
            if "captchaResponse" in formdata:
                del formdata["captchaResponse"]
        else:
            formdata["captchaResponse"] = captcha_str
        login_resp = session.post(
            url=AUTHSERVER_URL, data=formdata, allow_redirects=False)

        def redirect_to_service():
            return session.get(url=login_resp.headers['Location'], allow_redirects=False)

        if login_resp.status_code != 302:
            parser = _LoginedPageParser(login_resp.status_code)
            parser.feed(login_resp.text)

            if parser._kick:  # pylint: ignore disable=protected-access
                def kick():
                    nonlocal login_resp
                    # pylint: ignore disable=protected-access
                    login_resp = session.post(
                        url=AUTHSERVER_URL,
                        data={"execution": parser._kick_execution,
                              "_eventId": "continue"},
                        allow_redirects=False,
                        timeout=timeout)
                    return redirect_to_service()

                if kick_others:
                    return kick()
                else:
                    def cancel():
                        # pylint: ignore disable=protected-access
                        return session.post(
                            url=AUTHSERVER_URL,
                            data={"execution": parser._cancel_execution,
                                  "_eventId": "cancel"},
                            allow_redirects=False,
                            timeout=timeout)
                    raise MultiSessionConflict(kick=kick, cancel=cancel)
            raise UnknownAuthserverException(
                f"status code {login_resp.status_code} is got (302 expected) when sending login post, "
                "but can not find the element span.login_auth_error#msg")
        return redirect_to_service()

    captcha_str = None
    if session.get(AUTHSERVER_CAPTCHA_DETERMINE_URL, params={"username": username}).text == "true":
        captcha_img_resp = session.get(AUTHSERVER_CAPTCHA_IMAGE_URL)
        if captcha_callback is None:
            raise NeedCaptcha(captcha_img_resp.content,
                              captcha_img_resp.headers["Content-Type"],
                              after_captcha)
        captcha_str = captcha_callback(
            captcha_img_resp.content, captcha_img_resp.headers["Content-Type"])
        if captcha_str is None:
            raise NeedCaptcha(captcha_img_resp.content,
                              captcha_img_resp.headers["Content-Type"],
                              after_captcha)
    return after_captcha(captcha_str)


def login_sso(session: Session,
              username: str,
              password: str,
              service: Optional[str] = None,
              timeout: int = 10,
              force_relogin: bool = False,
              last_resp: Optional[Response] = None,
              captcha: Optional[str] = None
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
    :param last_resp: 上次登录未成功的 :class:`Response`
    :type last_resp: Optional[Response], optional
    :param captcha: 登录验证码，需结合 last_resp 参数使用
    :type captcha: Optional[str], optional
    :raises InvaildCaptcha: 无效的验证码
    :raises IncorrectLoginCredentials: 错误的登陆凭据（如错误的密码、用户名）
    :raises NeedCaptcha: 需要提供验证码，获得验证码文本之后可调用所抛出异常的 :func:`NeedCaptcha.after_captcha` 函数来继续登陆
    :return: 登陆了统一身份认证后所跳转到的地址的 :class:`Response`
    :rtype: Response
    """
    resp: Response
    if last_resp is None:
        resp = session.get(SSO_LOGIN_URL,
                           params=service and {"service": service},
                           allow_redirects=False,
                           timeout=timeout)
        if resp.status_code == 302:
            if force_relogin:
                logout_sso(session)
                resp = session.get(SSO_LOGIN_URL, timeout=timeout)
            else:
                return session.get(resp.headers['Location'], allow_redirects=False, timeout=timeout)
        assert resp.status_code == 200
    else:
        resp = last_resp
    page_data = _SSOPageParser().parse(resp.text)
    if page_data['captcha-url'] and not captcha:
        captcha_img_resp = session.get(
            f"{SSO_ROOT_URL}/{page_data['captcha-url']}", timeout=timeout)
        print(page_data['captcha-url'], captcha_img_resp.url, captcha_img_resp.headers)
        raise NeedCaptcha(
            captcha_img_resp.content,
            captcha_img_resp.headers["content-type"],
            lambda captcha: login_sso(
                session, username, password, service, timeout, force_relogin, resp, captcha)
        )

    # there do be a typo `croypto` in sso.cqu.edu.cn api
    croypto = page_data['login-croypto']
    passwd_encrypted = b64encode(
        des_ecb_encryptor(b64decode(croypto))(pad8(password.encode())))
    request_data = {'username': username,
                    'type': 'UsernamePassword',
                    '_eventId': 'submit',
                    'geolocation': '',
                    'execution': page_data['login-page-flowkey'],
                    'croypto': croypto,
                    'password': passwd_encrypted}
    if captcha is not None:
        request_data['captcha_code'] = [captcha, captcha]
    login_resp = session.post(SSO_LOGIN_URL,
                              params=service and {"service": service},
                              data=request_data,
                              allow_redirects=False,
                              timeout=timeout)
    if login_resp.status_code == 302:
        return session.get(login_resp.headers['Location'], allow_redirects=False, timeout=timeout)
    elif login_resp.status_code == 401:
        raise IncorrectLoginCredentials()
    elif login_resp.status_code == 200:
        error_code: Optional[int] = _SSOErrorParser().parse(login_resp.text)
        if error_code == _SSO_CAPTCHA_ERROR_CODE:
            return InvaildCaptcha()
        elif error_code is None:
            raise UnknownAuthserverException("No error code")
        else:
            raise UnknownAuthserverException(
                f"{error_code}: {_SSO_ERROR_CODES.get(error_code, '')}")


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
    if use_sso:
        try:
            return login_sso(session, username, password, service, timeout, force_relogin)
        except NeedCaptcha as e:
            if captcha_callback is None:
                raise e
            else:
                captcha_str = captcha_callback(e.image, e.image_type)
                if captcha_str is None:
                    raise InvaildCaptcha()
                else:
                    return e.after_captcha(captcha_str)
    else:
        return login_authserver(session, username, password, service, timeout, force_relogin, captcha_callback, keep_longer, kick_others)
