from functools import wraps
from inspect import isgeneratorfunction
from enum import Enum
from typing import Callable, Protocol, Any, Generator, Optional, Literal

from ..exception import RequestTransformerException


__all__ = ['RequestParams', 'RequestTransformer', 'Response',
           'RequestParamsMapper', 'RequestsParamsMapper', 'HttpxParamsMapper']

REQUEST_METHOD = Literal['delete', 'get', 'head', 'options', 'patch', 'post', 'put']


class Response(Protocol):
    """
    具有`__await__`、`ok`、`status_code`、`url`、`content`、`text`、`json`属性的对象
    """
    def __await__(self): ...

    @property
    def ok(self) -> bool: ...

    @property
    def status_code(self) -> int: ...

    @property
    def url(self) -> str: ...

    @property
    def content(self) -> bytes: ...

    @property
    def text(self) -> str: ...

    @property
    def json(self, **kwargs: Any) -> Any: ...

class Request(Protocol):
    """
    具有request，返回一个`Response`对象
    """
    def request(*args, **kwargs) -> Response: ...

class RequestParamsMapper(Protocol):
    """
    至少具有method、url、allow_redirects属性的对象

    `RequestParams`的as_request方法基于满足此协议的枚举生成请求参数字典
    `RequestParams`对象传入的参数应当在对应枚举类中全部声明
    可以参考`RequestsParamsMapper`的实现
    """
    @property
    def method(self) -> Enum: ...

    @property
    def url(self) -> Enum: ...

    @property
    def allow_redirects(self) -> Enum: ...


class RequestsParamsMapper(Enum):
    """
    适用于requests库的ParamsMapper
    """
    method = 'method'
    url = 'url'
    params = 'params'
    data = 'data'
    json = 'json'
    headers = 'headers'
    allow_redirects = 'allow_redirects'

class HttpxParamsMapper(Enum):
    """
    适用于httpx库的ParamsMapper
    """
    method = 'method'
    url = 'url'
    params = 'params'
    data = 'data'
    json = 'json'
    headers = 'headers'
    allow_redirects = 'follow_redirects'

class RequestParams:
    """
    调用了`RequestTransformer`中register方法的函数均应通过yield返回此类以支持对不同请求库的参数映射
    """
    def __init__(self, method: REQUEST_METHOD, url: str, *, allow_redirects: bool = True, **kwargs):
        """


        :param method: 请求方式，'delete', 'get', 'head', 'options', 'patch', 'post', 'put'中的某一个
        :param url: 请求url
        :param allow_redirects: 运行自动重定向
        """
        self.method = method
        self.url = url
        self.allow_redirects = allow_redirects
        self.other_params = kwargs

    def as_request(self, param_mapper: RequestParamsMapper = RequestsParamsMapper):
        """
        通过`RequestParamsMapper`类将请求参数映射为不同请求库需求的参数字典
        """
        result = {}
        result.update({param_mapper.method.value: self.method})
        result.update({param_mapper.url.value: self.url})
        result.update({param_mapper.allow_redirects.value: self.allow_redirects})
        for k, v in self.other_params.items():
            param_key: Optional[Enum] = getattr(param_mapper, k, None)
            if param_key is None:
                raise RequestTransformerException('请求参数未在RequestsParamsMapper中给出')
            result.update({param_key.value: v})
        return result

class RequestTransformer:
    def __init__(self, generator: Callable[..., Generator[RequestParams, Any, Any]],
                 sync_request_param_mapper: RequestParamsMapper = RequestsParamsMapper,
                 async_request_param_mapper: RequestParamsMapper = HttpxParamsMapper):
        """
        拓展按照一定格式书写的生成器函数以同时支持同步/异步发出请求
        直接调用该类实例则默认以同步的方式执行此函数

        :param sync_request_param_mapper: 用于发出同步请求时使用的参数转换库，默认为`RequestsParamsMapper`
        :param async_request_param_mapper: 用于发出异步请求时使用的参数转换库，默认为`HttpxParamsMapper`
        """
        if not isgeneratorfunction(generator):
            raise RequestTransformerException('注册为Request Transformer的函数应当为生成器函数')
        self.generator = generator
        self.sync_request_param_mapper = sync_request_param_mapper
        self.async_request_param_mapper = async_request_param_mapper

    def __call__(self, request: Request, *args, **kwargs):
        self.sync_request(*args, **kwargs)

    @property
    def sync_request(self) -> Callable[[Request, Any, ...], Any]:
        """
        将生成器函数以同步的方式执行，返回同步函数
        """
        @wraps(self.generator)
        def inner_function(request: Request, *args, **kwargs):
            try:
                generator = self.generator(*args, **kwargs)
                res = None
                while True:
                    params: RequestParams = generator.send(res)
                    res = request.request(**params.as_request(self.sync_request_param_mapper))
            except StopIteration as e:
                return e.value

        return inner_function

    @property
    def async_request(self) -> Callable[[Request, Any, ...], Any]:
        """
        将生成器函数以异步的方式执行，返回async function
        """
        @wraps(self.generator)
        async def inner_function(request: Request, *args, **kwargs):
            try:
                generator = self.generator(*args, **kwargs)
                res = None
                while True:
                    params: RequestParams = generator.send(res)
                    res = await request.request(**params.as_request(self.async_request_param_mapper))
            except StopIteration as e:
                return e.value

        return inner_function


    @classmethod
    def register(cls, sync_request_param_mapper: RequestParamsMapper = RequestsParamsMapper,
                 async_request_param_mapper: RequestParamsMapper = HttpxParamsMapper):
        """
        将按照一定格式书写的同步函数包装成`RequestTransformer`对象

        :param sync_request_param_mapper: 用于发出同步请求时使用的参数转换库，默认为`RequestsParamsMapper`
        :param async_request_param_mapper: 用于发出异步请求时使用的参数转换库，默认为`HttpxParamsMapper`
        """
        def wrapped_function(func: Callable[..., Generator[RequestParams, Any, Any]]):
            return cls(func, sync_request_param_mapper, async_request_param_mapper)

        return wrapped_function
