from functools import wraps
from inspect import isgeneratorfunction
from typing import Callable, Any, Generator

from ...exception import RequestTransformerException
from ..config import ConfigManager
from .models import RequestReturns, RequestProtocol, Request


__all__ = ['RequestTransformer', ]


class RequestTransformer:
    def __init__(self, generator: Callable[..., Generator[RequestReturns, Any, Any]]):
        """
        拓展按照一定格式书写的生成器函数以同时支持同步/异步发出请求
        直接调用该类实例则默认以同步的方式执行此函数

        :param sync_request_param_mapper: 用于发出同步请求时使用的参数转换库，默认为`RequestsParamsMapper`
        :param async_request_param_mapper: 用于发出异步请求时使用的参数转换库，默认为`HttpxParamsMapper`
        """
        if not isgeneratorfunction(generator):
            raise RequestTransformerException('注册为Request Transformer的函数应当为生成器函数')
        self.generator = generator

    @property
    def sync_request(self) -> Callable[[RequestProtocol, Any, ...], Any]:
        """
        将生成器函数以同步的方式执行，返回同步函数
        """
        @wraps(self.generator)
        def inner_function(*args, **kwargs):
            try:
                request = args[0]
                args = args[1:]
                generator = self.generator(Request(request), *args, **kwargs)
                res = None
                while True:
                    request_returns: RequestReturns = generator.send(res)
                    res = request_returns[0].request(
                        **request_returns[1].to_param_dict(
                            ConfigManager().config['request']['sync_request_params_mapper']
                        )
                    )
            except StopIteration as e:
                return e.value

        return inner_function

    @property
    def async_request(self) -> Callable[[RequestProtocol, Any, ...], Any]:
        """
        将生成器函数以异步的方式执行，返回async function
        """
        @wraps(self.generator)
        async def inner_function(*args, **kwargs):
            try:
                request = args[0]
                args = args[1:]
                generator = self.generator(Request(request), *args, **kwargs)
                res = None
                while True:
                    request_returns: RequestReturns = generator.send(res)
                    res = await request_returns[0].request(
                        **request_returns[1].to_param_dict(
                            ConfigManager().config['request']['async_request_params_mapper']
                        )
                    )
            except StopIteration as e:
                return e.value

        return inner_function


    @classmethod
    def register(cls):
        """
        将按照一定格式书写的同步函数包装成`RequestTransformer`对象
        """
        def wrapped_function(func: Callable[..., Generator[RequestReturns, Any, Any]]):
            return cls(func)

        return wrapped_function
