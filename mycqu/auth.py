"""统一身份认证相关的模块
"""
from typing import Dict, Optional, Callable, Union
import random
import re
from base64 import b64encode
from requests import Session, Response
from bs4 import BeautifulSoup  # type: ignore
from ._lib_wrapper.Crypto import pad, AES

__all__ = ("NotAllowedService", "NeedCaptcha", "InvaildCaptcha",
           "IncorrectLoginCredentials", "UnknownAuthserverException", "NotLogined",
           "is_logined", "logout", "access_service", "login")

AUTHSERVER_URL = "http://authserver.cqu.edu.cn/authserver/login"
AUTHSERVER_CAPTCHA_DETERMINE_URL = "http://authserver.cqu.edu.cn/authserver/needCaptcha.html"
AUTHSERVER_CAPTCHA_IMAGE_URL = "http://authserver.cqu.edu.cn/authserver/captcha.html"
AUTHSERVER_LOGOUT_URL = "http://authserver.cqu.edu.cn/authserver/logout"
_CHAR_SET = 'ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678'


def _random_str(length: int):
    return ''.join(random.choices(_CHAR_SET, k=length))


_SALT_RE: re.Pattern = re.compile('var pwdDefaultEncryptSalt = "([^"]+)"')


class NotAllowedService(Exception):
    """试图认证不允许的服务时抛出
    """


class NeedCaptcha(Exception):
    """登录统一身份认证时需要输入验证码时拋出
    """

    def __init__(self, image: bytes, image_type: str, after_captcha: Callable[[str], Response]):
        super().__init__("captcha is needed")
        self.image: bytes = image
        """验证码图片文件数据"""
        self.image_type: str = image_type
        """验证码图片 MIME 类型"""
        self.after_captcha: Callable[[str], Response] = after_captcha
        """将验证码传入，调用以继续进行登陆"""


class InvaildCaptcha(Exception):
    """登录统一身份认证输入了无效验证码时抛出
    """

    def __init__(self):
        super().__init__("invaild captcha")


class IncorrectLoginCredentials(Exception):
    """使用无效的的登录凭据（如错误的用户、密码）
    """

    def __init__(self):
        super().__init__("incorrect username or password")


class UnknownAuthserverException(Exception):
    """登录或认证服务过程中未知错误
    """


class NotLogined(Exception):
    """未登陆或登陆过期的会话被用于进行需要统一身份认证登陆的操作
    """
    def __init__(self):
        super().__init__("not in logined status")

# from https://github.com/CQULHW/CQUQueryGrade


def get_formdata(html: str, username: str, password: str) -> Dict[str, Union[str, bytes]]:
    soup = BeautifulSoup(html, 'html.parser')

    errors = soup.find("div", {"id": "msg", "class": "errors"})
    if not errors is None:
        error_str = errors.text.strip()
        if error_str == "应用未注册\n不允许使用认证服务来认证您访问的目标应用。":
            raise NotAllowedService(error_str)
        raise UnknownAuthserverException(
            "Error message before login: "+errors)
    lt = soup.find("input", {"name": "lt"})['value']
    dllt = soup.find("input", {"name": "dllt"})['value']
    execution = soup.find("input", {"name": "execution"})['value']
    _event_id = soup.find("input", {"name": "_eventId"})['value']
    rm_shown = soup.find("input", {"name": "rmShown"})['value']
    salt_js = soup.find("script", {"type": "text/javascript"}).string
    assert (match := _SALT_RE.search(salt_js))
    key = match[1]  # 获取盐，被用来加密
    passwd_pkcs7 = pad((_random_str(64)+str(password)
                        ).encode(), 16, style='pkcs7')
    aes = AES.new(key=key.encode(), iv=_random_str(
        16).encode(), mode=AES.MODE_CBC)
    passwd_encrypted = b64encode(aes.encrypt(passwd_pkcs7))
    # 传入数据进行统一认证登录
    return {
        'username': username,
        'password': passwd_encrypted,
        'lt': lt,
        'dllt': dllt,
        'execution': execution,
        '_eventId': _event_id,
        'rmShown': rm_shown
    }


def is_logined(session: Session) -> bool:
    """判断是否处于统一身份认证登陆状态

    :param session: 会话
    :type session: Session
    :return: :obj:`True` 如果处于登陆状态，:obj:`False` 如果处于未登陆或登陆过期状态
    :rtype: bool
    """
    return session.get(AUTHSERVER_URL, allow_redirects=False).status_code == 302


def logout(session: Session) -> None:
    """注销统一身份认证登录状态

    :param session: 进行过登录的会话
    :type session: Session
    """
    session.get("http://authserver.cqu.edu.cn/authserver/logout")


def access_service(session: Session, service: str) -> Response:
    resp = session.get(AUTHSERVER_URL,
                       params={"service": service},
                       allow_redirects=False)
    if resp.status_code != 302:
        errors = BeautifulSoup(resp.text).find(
            "div", {"id": "msg", "class": "errors"})
        if not errors is None:
            raise NotAllowedService(errors.text[:-5].strip())
        raise NotLogined()
    return session.get(url=resp.headers['Location'], allow_redirects=False)


def login(session: Session,
          username: str,
          password: str,
          service: Optional[str] = None,
          timeout: int = 10,
          force_relogin: bool = False,
          captcha_callback: Optional[
              Callable[[bytes, str], Optional[str]]] = None
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
    :raises UnknownAuthserverException: 未知认证错误
    :raises InvaildCaptcha: 无效的验证码
    :raises IncorrectLoginCredentials: 错误的登陆凭据（如错误的密码、用户名）
    :raises NeedCaptcha: 需要提供验证码，获得验证码文本之后可调用所抛出异常的 :func:`NeedCaptcha.after_captcha` 函数来继续登陆
    :return: 登陆了统一身份认证后所跳转到的地址的 :class:`Response`
    :rtype: Response
    """
    login_page = session.get(
        url=AUTHSERVER_URL,
        params=None if service is None else {"service": service},
        allow_redirects=False,
        timeout=timeout)
    if login_page.status_code == 302:
        if not force_relogin:
            try:
                return login_page
            except NotLogined:
                pass
        else:
            logout(session)
    elif login_page.status_code != 200:
        raise UnknownAuthserverException()
    formdata = get_formdata(login_page.text, username, password)

    def after_captcha(captcha_str: Optional[str]):
        if captcha_str is None:
            if "captchaResponse" in formdata:
                del formdata["captchaResponse"]
        else:
            formdata["captchaResponse"] = captcha_str
        login_resp = session.post(
            url=AUTHSERVER_URL, data=formdata, allow_redirects=False)
        if login_resp.status_code != 302:
            soup = BeautifulSoup(login_resp.text, 'html.parser')
            errors = soup.find(
                "span", {"id": "msg", "class": "login_auth_error"})
            if errors is None:
                raise UnknownAuthserverException(
                    f"status code {login_resp.status_code} is got (302 expected) when sending login post, "
                    "but can not find the element span.login_auth_error#msg")
            else:
                error_str = errors.text.strip()
                if error_str == "无效的验证码":
                    raise InvaildCaptcha()
                elif error_str == "您提供的用户名或者密码有误":
                    raise IncorrectLoginCredentials()
                else:
                    raise UnknownAuthserverException(
                        f"status code {login_resp.status_code} is got (302 expected)"
                        f" when sending login post, {error_str}"
                    )
        return session.get(url=login_resp.headers['Location'], allow_redirects=False)

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
