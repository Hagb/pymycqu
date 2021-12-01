from typing import Dict, Optional, Callable, Union
import random
import re
from base64 import b64encode
from requests import Session, Response
from bs4 import BeautifulSoup
try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad
except ModuleNotFoundError:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    from Crypto import version_info
    if version_info[0] == 2:
        # pylint: ignore disable=raise-missing-from
        raise ModuleNotFoundError(
            'Need either `pycryptodome` or `pycryptodomex`!')
__all__ = ("NotAllowedService", "NeedCaptcha", "InvaildCaptcha",
           "IncorrectLoginCredentials", "UnknownAuthserverException", "NotLogined",
           "is_logined", "logout", "access_service", "login")

AUTHSERVER_URL = "http://authserver.cqu.edu.cn/authserver/login"
AUTHSERVER_CAPTCHA_DETERMINE_URL = "http://authserver.cqu.edu.cn/authserver/needCaptcha.html"
AUTHSERVER_CAPTCHA_IMAGE_URL = "http://authserver.cqu.edu.cn/authserver/captcha.html"
AUTHSERVER_LOGOUT_URL = "http://authserver.cqu.edu.cn/authserver/logout"
_CHAR_SET = 'ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678'


def _random_str(n):
    return ''.join(random.choices(_CHAR_SET, k=n))


_SALT_RE: re.Pattern = re.compile('var pwdDefaultEncryptSalt = "([^"]+)"')


class NotAllowedService(Exception):
    pass


class NeedCaptcha(Exception):
    def __init__(self, image: bytes, image_type: str, after_captcha: Callable[[str], Response]):
        super().__init__("captcha is needed")
        self.image = image
        self.image_type = image_type
        self.after_captcha = after_captcha


class InvaildCaptcha(Exception):
    def __init__(self):
        super().__init__("invaild captcha")


class IncorrectLoginCredentials(Exception):
    def __init__(self):
        super().__init__("incorrect username or password")


class UnknownAuthserverException(Exception):
    pass


class NotLogined(Exception):
    def __init__(self):
        super().__init__("not in logined status")

# from https://github.com/CQULHW/CQUQueryGrade
def get_formdata(html: str, username: str, password: str) -> Dict[str, Union[str, bytes]]:
    soup = BeautifulSoup(html, 'html.parser')

    errors = soup.find("div", {"id": "msg", "class": "errors"})
    if not (errors is None):
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
    return session.get(AUTHSERVER_URL, allow_redirects=False).status_code == 302


def logout(session: Session) -> None:
    session.get("http://authserver.cqu.edu.cn/authserver/logout")


def access_service(session: Session, service: str) -> Response:
    resp = session.get(AUTHSERVER_URL,
                       params={"service": service},
                       allow_redirects=False)
    if resp.status_code != 302:
        errors = BeautifulSoup(resp.text).find(
            "div", {"id": "msg", "class": "errors"})
        if not (errors is None):
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
                        f"status code {login_resp.status_code} is got (302 expected) when sending login post, {error_str}"
                    )
        return session.get(url=login_resp.headers['Location'], allow_redirects=False)

    captcha_str = None
    if(session.get(AUTHSERVER_CAPTCHA_DETERMINE_URL, params={"username": username}).text == "true"):
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
