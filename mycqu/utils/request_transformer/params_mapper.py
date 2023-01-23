from enum import Enum
from typing import Protocol


__all__ = ['RequestParamsMapper', 'RequestsParamsMapper', 'HttpxParamsMapper']


class RequestParamsMapper(Protocol):
    """
    至少具有method、url、allow_redirects属性的对象

    `RequestParams`的to_param_dict方法基于满足此协议的枚举生成请求参数字典
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
    cookies = 'cookies'
    timeout = 'timeout'
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
    cookies = 'cookies'
    timeout = 'timeout'
    allow_redirects = 'follow_redirects'