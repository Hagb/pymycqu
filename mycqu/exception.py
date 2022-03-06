from typing import Dict, Optional, Callable
from requests import Response


class TicketGetError(Exception):
    """
    当未能从网页对应位置中获取到ticket时抛出
    """


class ParseError(Exception):
    """
    当从返回数据解析所需值失败时抛出
    """


class CQUWebsiteError(Exception):
    def __init__(self, error_msg='No error info'):
        super().__init__('CQU website return error: ' + error_msg)


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


class MultiSessionConflict(Exception):
    """当前用户启用单处登录，并且存在其他登录会话时抛出"""

    def __init__(self, kick: Callable[[], Response], cancel: Callable[[], Response]):
        super().__init__("单处登录 enabled, kick other sessions of the user or cancel")
        self.kick: Callable[[], Response] = kick
        """踢掉其他会话并登录"""
        self.cancel: Callable[[], Response] = cancel
        """取消登录"""


class MycquUnauthorized(Exception):
    def __init__(self):
        super().__init__("Unauthorized in mycqu, auth.login firstly and then mycqu.access_mycqu")

