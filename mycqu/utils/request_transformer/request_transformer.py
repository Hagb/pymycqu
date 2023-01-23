from functools import wraps, partial
from inspect import isgeneratorfunction, isgenerator
from typing import Callable, Any, Generator, Tuple

from ..config import ConfigManager
from .models import RequestReturns, RequestProtocol, Requestable, Request, Response


__all__ = ['RequestTransformer', ]


class RequestTransformer:
    def __init__(self, generator: Callable[..., Generator[RequestReturns, Any, Any]]):
        """
        拓展按照一定格式书写的生成器函数以同时支持同步/异步发出请求
        直接调用该类实例则默认以同步的方式执行此函数

        :param sync_request_param_mapper: 用于发出同步请求时使用的参数转换库，默认为`RequestsParamsMapper`
        :param async_request_param_mapper: 用于发出异步请求时使用的参数转换库，默认为`HttpxParamsMapper`
        """
        if not (isgeneratorfunction(generator) or isgenerator(generator)):
            self.without_request = True
        else:
            self.without_request = False
        self.generator = generator
        self.instance = None

    def __get__(self, instance, owner):
        self.instance = instance if instance is not None else owner
        return self


    @property
    def sync_request(self) -> Callable[[RequestProtocol, Any, ...], Any]:
        """
        将生成器函数以同步的方式执行，返回同步函数
        """
        if self.without_request:
            if self.instance is not None:
                return partial(self.generator, self.instance)
            else:
                return self.generator

        @wraps(self.generator)
        def inner_function(request: Request, *args, **kwargs) -> Response:
            try:
                if self.instance is not None:
                    generator = self.generator(self.instance, Requestable(request), *args, **kwargs)
                else:
                    generator = self.generator(Requestable(request), *args, **kwargs)
                res = None
                while True:
                    request_returns: RequestReturns = generator.send(res)
                    if isinstance(request_returns, RequestTransformer):
                        request_returns = (request_returns, {})
                    if isinstance(request_returns[0], RequestTransformer):
                        res = request_returns[0].sync_request(request, **request_returns[1])
                    else:
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
        if self.without_request:
            @wraps(self.generator)
            async def return_function(*args, **kwargs):
                if self.instance is not None:
                    return self.generator(self.instance, *args, **kwargs)
                else:
                    return self.generator(*args, **kwargs)
            return return_function
        @wraps(self.generator)
        async def inner_function(request: Request, *args, **kwargs) -> Response:
            try:
                if self.instance is not None:
                    generator = self.generator(self.instance, Requestable(request), *args, **kwargs)
                else:
                    generator = self.generator(Requestable(request), *args, **kwargs)
                res = None
                while True:
                    request_returns: RequestReturns = generator.send(res)
                    if isinstance(request_returns, RequestTransformer):
                        request_returns = (request_returns, {})
                    if isinstance(request_returns[0], RequestTransformer):
                        res = await request_returns[0].async_request(request, **request_returns[1])
                    else:
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
