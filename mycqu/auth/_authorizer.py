from abc import ABC, abstractmethod
from typing import Optional, Callable, Dict, NoReturn, Union, Awaitable, Generic
from functools import partial

from ..exception import NeedCaptcha, InvaildCaptcha, NotLogined
from ..utils.request_transformer import Request, Response, RequestTransformer


class Authorizer(ABC, Generic[Request]):
    """
    SSO 和 Authorizer 登陆验证流程均为：获取登陆信息->判断是否需要填写验证码
    ->需要填写，抛出:class:`NeedCaptcha`异常
    ->无需填写，依靠登陆信息进行登陆
    该类要求子类实现获取登陆信息、判断是否需要填写验证码、获取验证码后应当如何修改登陆信息、使用登陆信息进行登陆四个函数，
    组合上述四个方法实现了通用的login、logout、is_logined、access_service方法
    """
    def __init__(
            self,
            session: Request,
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
    def _get_request_data(self, session: Request) -> Dict:
        """
        获取请求所需的相关参数
        """
        pass

    @abstractmethod
    def _need_captcha(self, session: Request) -> Optional[str]:
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
    def _login(self, session: Request, request_data: Dict) -> Response:
        """
        通过获取的请求参数进行登陆
        """
        pass

    def _raise_need_captcha(
            self, url: str,
            after_captcha: Callable[[str], Union[Response, Awaitable[Response]]], timeout: int = 10) -> NoReturn:
        """
        抛出`NeedCaptcha`异常
        """
        captcha_img = self.session.get(url, timeout=timeout)
        raise NeedCaptcha(captcha_img.content,
                          captcha_img.headers["Content-Type"],
                          after_captcha)


    @classmethod
    def login(cls,
              session: Request,
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
        request_data = authorizer._get_request_data.sync_request(authorizer.session)

        is_need_captcha = authorizer._need_captcha.sync_request(authorizer.session)
        if is_need_captcha is not None:
            request_data_changer = partial(authorizer._need_captcha_handler, request_data=request_data)
            after_captcha = lambda captcha: authorizer._login.sync_request(authorizer.session, request_data_changer(captcha))
            authorizer._raise_need_captcha(is_need_captcha, after_captcha, authorizer.timeout)

        return authorizer._login.sync_request(authorizer.session, request_data)

    @classmethod
    async def async_login(
            cls,
            session: Request,
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
        request_data = await authorizer._get_request_data.async_request(authorizer.session)

        is_need_captcha = await authorizer._need_captcha.async_request(authorizer.session)
        if is_need_captcha is not None:
            request_data_changer = partial(authorizer._need_captcha_handler, request_data=request_data)
            after_captcha = lambda captcha: authorizer._login.sync_request(authorizer.session, request_data_changer(captcha))
            authorizer._raise_need_captcha(is_need_captcha, after_captcha, authorizer.timeout)

        return await authorizer._login.async_request(authorizer.session, request_data)

    @classmethod
    @RequestTransformer.register()
    def _is_logined(cls, session: Request) -> bool:
        assert cls.LOGIN_URL != '', '子类未重写`IS_LOGINED_URL`'
        res = yield session.get(cls.LOGIN_URL, allow_redirects=False)
        return res.status_code == 302

    @classmethod
    def is_logined(cls, session: Request) -> bool:
        """
        判断是否处于统一身份认证登陆状态

        :param session: 会话
        :type session: Session
        :return: :obj:`True` 如果处于登陆状态，:obj:`False` 如果处于未登陆或登陆过期状态
        :rtype: bool
        """
        return cls._is_logined.sync_request(session)

    @classmethod
    async def async_is_logined(cls, session: Request) -> bool:
        """
        异步的判断是否处于统一身份认证登陆状态

        :param session: 会话
        :type session: Session
        :return: :obj:`True` 如果处于登陆状态，:obj:`False` 如果处于未登陆或登陆过期状态
        :rtype: bool
        """
        return await cls._is_logined.async_request(session)


    @classmethod
    @RequestTransformer.register()
    def _access_service(cls, session: Request, service: str) -> Response:
        assert cls.LOGIN_URL != '', '子类未重写`ACCESS_SERVICE_URL`'
        resp = yield session.get(cls.LOGIN_URL, params={"service": service}, allow_redirects=False)
        if resp.status_code != 302:
            # TODO
            raise NotLogined()
        res = yield session.get(url=resp.headers['Location'], allow_redirects=False)
        return res

    @classmethod
    def access_service(cls, session: Request, service: str) -> Response:
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
        return cls._access_service.sync_request(session, service)

    @classmethod
    async def async_access_service(cls, session: Request, service: str) -> Response:
        """
        异步的从登录了统一身份认证的会话获取指定服务的许可

        :param session: 登录了统一身份认证的会话
        :type session: Session
        :param service: 服务的 url
        :type service: str
        :raises NotLogined: 统一身份认证未登录时抛出
        :return: 访问服务 url 的 :class:`Response`
        :rtype: Response
        """
        return await cls._access_service.async_request(session, service)

    @classmethod
    @RequestTransformer.register()
    def _logout(cls, session: Request) -> None:
        assert cls.LOGOUT_URL != '', '子类未重写`LOGOUT_URL`'
        yield session.get(cls.LOGOUT_URL)

    @classmethod
    def logout(cls, session: Request) -> None:
        """
        注销统一身份认证（sso）登录状态

        :param session: 进行过登录的会话
        :type session: Session
        """
        cls._logout.sync_request(session)

    @classmethod
    async def async_logout(cls, session: Request) -> None:
        """
        异步的注销统一身份认证（sso）登录状态

        :param session: 进行过登录的会话
        :type session: Session
        """
        await cls._logout.async_request(session)
