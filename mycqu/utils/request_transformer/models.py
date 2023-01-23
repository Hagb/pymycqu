from enum import Enum
from typing import NewType, Tuple, Optional, Dict, Protocol, Any, Literal, TypeVar

from .params_mapper import RequestParamsMapper


__all__ = ['ResponseProtocol', 'RequestProtocol', 'RequestReturns', 'RequestParams', 'Requestable', 'Request', 'Response']

REQUEST_METHOD = Literal['delete', 'get', 'head', 'options', 'patch', 'post', 'put']


class ResponseProtocol(Protocol):
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

    @property
    def headers(self) -> Any: ...

class RequestProtocol(Protocol):
    """
    具有网络请求相关方法，所有请求方法均返回一个满足`Response`协议的对象
    """
    def request(*args, **kwargs) -> ResponseProtocol: ...

    def get(*args, **kwargs) -> ResponseProtocol: ...

    def post(*args, **kwargs) -> ResponseProtocol: ...

    def put(*args, **kwargs) -> ResponseProtocol: ...

    def patch(*args, **kwargs) -> ResponseProtocol: ...

    def delete(*args, **kwargs) -> ResponseProtocol: ...
    def options(*args, **kwargs) -> ResponseProtocol: ...

    def head(*args, **kwargs) -> ResponseProtocol: ...

Request = TypeVar('Request', bound=RequestProtocol)
Response = TypeVar('Response', bound=ResponseProtocol)

class RequestParams:
    """
    调用了`RequestTransformer`中register方法的函数均应通过yield返回此类以支持对不同请求库的参数映射
    """
    def __init__(self, *, method: REQUEST_METHOD, url: str, allow_redirects: bool = True, **kwargs):
        """
        :param method: 请求方式，'delete', 'get', 'head', 'options', 'patch', 'post', 'put'中的某一个
        :param url: 请求url
        :param allow_redirects: 运行自动重定向
        """
        self.method = method
        self.url = url
        self.allow_redirects = allow_redirects
        self.other_params = kwargs

    def to_param_dict(self, param_mapper: RequestParamsMapper) -> Dict:
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
                raise Exception('请求参数未在RequestsParamsMapper中给出')
            result.update({param_key.value: v})
        return result

RequestReturns = NewType('RequestReturns', Tuple[RequestProtocol, RequestParams])

class Requestable:
    def __init__(self, requestable: RequestProtocol):
        self.requestable = requestable
    def request(self, method: REQUEST_METHOD, url: str, *, allow_redirects: bool = True, **kwargs) -> RequestReturns:
        return RequestReturns((self.requestable, RequestParams(url=url, method=method, allow_redirects=allow_redirects,
                                                               **kwargs)))

    def get(self, url: str, *, allow_redirects: bool = True, **kwargs) -> RequestReturns:
        return self.request('get', url, allow_redirects=allow_redirects, **kwargs)

    def post(self, url: str, *, allow_redirects: bool = True, **kwargs) -> RequestReturns:
        return self.request('post', url, allow_redirects=allow_redirects, **kwargs)

    def put(self, url: str, *, allow_redirects: bool = True, **kwargs) -> RequestReturns:
        return self.request('put', url, allow_redirects=allow_redirects, **kwargs)

    def patch(self, url: str, *, allow_redirects: bool = True, **kwargs) -> RequestReturns:
        return self.request('patch', url, allow_redirects=allow_redirects, **kwargs)

    def delete(self, url: str, *, allow_redirects: bool = True, **kwargs) -> RequestReturns:
        return self.request('delete', url, allow_redirects=allow_redirects, **kwargs)

    def options(self, url: str, *, allow_redirects: bool = True, **kwargs) -> RequestReturns:
        return self.request('options', url, allow_redirects=allow_redirects, **kwargs)

    def head(self, url: str, *, allow_redirects: bool = True, **kwargs) -> RequestReturns:
        return self.request('head', url, allow_redirects=allow_redirects, **kwargs)