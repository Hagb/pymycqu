from abc import ABC, abstractmethod
from typing import Optional, Callable, Dict
from functools import partial

from requests import Session, Response

from ..exception import NeedCaptcha, InvaildCaptcha, NotLogined


class Authorizer(ABC):
    """
    SSO 和 Authorizer 登陆验证流程均为：获取登陆信息->判断是否需要填写验证码
    ->需要填写，抛出:class:`NeedCaptcha`异常
    ->无需填写，依靠登陆信息进行登陆
    该类要求子类实现获取登陆信息、判断是否需要填写验证码、获取验证码后应当如何修改登陆信息、使用登陆信息进行登陆四个函数，
    组合上述四个方法实现了通用的login、logout、is_logined、access_service方法
    """
    def __init__(
            self,
            session: Session,
            username: str,
            password: str,
            service: Optional[str] = None,
            timeout: int = 10,
            force_relogin: bool = False,
            keep_longer: bool = False,
            kick_others: bool = False
    ):
        self.session = session
        self.username = username
        self.password = password
        self.service = service
        self.timeout = timeout
        self.force_relogin = force_relogin
        self.keep_longer = keep_longer
        self.kick_others = kick_others

    LOGIN_URL = ''
    LOGOUT_URL = ''

    @abstractmethod
    def _get_request_data(self) -> Dict:
        """
        获取请求所需的相关参数
        """
        pass

    @abstractmethod
    def _need_captcha(self) -> Optional[str]:
        """
        是否需要验证码，如果需要，则返回验证码目标url
        """
        pass

    @abstractmethod
    def _need_captcha_handler(self, captcha: str, request_data: Dict):
        """
        拥有验证码之后应该如何修改请求参数
        """
        pass

    @abstractmethod
    def _login(self, request_data: Dict) -> Response:
        """
        通过获取的请求参数进行登陆
        """
        pass

    def _raise_need_captcha(self, url: str, after_captcha: Callable[[str], Response], timeout: int = 10):
        """
        抛出`NeedCaptcha`异常
        """
        captcha_img = self.session.get(url, timeout=timeout)
        raise NeedCaptcha(captcha_img.content,
                          captcha_img.headers["Content-Type"],
                          after_captcha)


    @classmethod
    def _base_login(cls,
                    session: Session,
                    username: str,
                    password: str,
                    service: Optional[str] = None,
                    timeout: int = 10,
                    force_relogin: bool = False,
                    keep_longer: bool = False,
                    kick_others: bool = False
                    ) -> Response:
        """
        组合登陆流程
        """
        authorizer = cls(session, username, password, service, timeout, force_relogin, keep_longer, kick_others)
        request_data = authorizer._get_request_data()
        is_need_captcha = authorizer._need_captcha()
        if is_need_captcha is not None:
            request_data_changer = partial(authorizer._need_captcha_handler, request_data=request_data)
            after_captcha = lambda captcha: authorizer._login(request_data_changer(captcha))
            authorizer._raise_need_captcha(is_need_captcha, after_captcha, authorizer.timeout)
        return authorizer._login(request_data)


    @classmethod
    def login(
            cls,
            session: Session,
            username: str,
            password: str,
            service: Optional[str] = None,
            timeout: int = 10,
            force_relogin: bool = False,
            captcha_callback: Optional[Callable[[bytes, str], Optional[str]]] = None,
            keep_longer: bool = False,
            kick_others: bool = False
    ) -> Response:
        """
        登录统一身份认证

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
        try:
            return cls._base_login(session, username, password, service, timeout, force_relogin, keep_longer,
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

    @classmethod
    def is_logined(cls, session: Session) -> bool:
        """
        判断是否处于统一身份认证登陆状态

        :param session: 会话
        :type session: Session
        :return: :obj:`True` 如果处于登陆状态，:obj:`False` 如果处于未登陆或登陆过期状态
        :rtype: bool
        """
        assert cls.LOGIN_URL != '', '子类未重写`IS_LOGINED_URL`'
        return session.get(cls.LOGIN_URL, allow_redirects=False).status_code == 302

    @classmethod
    def access_service(cls, session: Session, service: str) -> Response:
        """
        从登录了统一身份认证的会话获取指定服务的许可

        :param session: 登录了统一身份认证的会话
        :type session: Session
        :param service: 服务的 url
        :type service: str
        :raises NotLogined: 统一身份认证未登录时抛出
        :return: 访问服务 url 的 :class:`Response`
        :rtype: Response
        """
        assert cls.LOGIN_URL != '', '子类未重写`ACCESS_SERVICE_URL`'
        resp = session.get(cls.LOGIN_URL,
                           params={"service": service},
                           allow_redirects=False)
        if resp.status_code != 302:
            # TODO
            raise NotLogined()
        return session.get(url=resp.headers['Location'], allow_redirects=False)

    @classmethod
    def logout(cls, session: Session) -> None:
        """注销统一身份认证（sso）登录状态

        :param session: 进行过登录的会话
        :type session: Session
        """
        assert cls.LOGOUT_URL != '', '子类未重写`LOGOUT_URL`'
        session.get(cls.LOGOUT_URL)

