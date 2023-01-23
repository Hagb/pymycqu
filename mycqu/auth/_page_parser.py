import random
import re
from base64 import b64encode
from html.parser import HTMLParser
from typing import Dict, Optional

from .._lib_wrapper.encrypt import pad16, aes_cbc_encryptor
from mycqu.exception import NotAllowedService, InvaildCaptcha, IncorrectLoginCredentials, \
    UnknownAuthserverException, ParseError

_CHAR_SET = 'ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678'


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

def _random_str(length: int) -> str:
    return ''.join(random.choices(_CHAR_SET, k=length))

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
