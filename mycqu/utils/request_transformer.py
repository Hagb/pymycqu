from functools import wraps
from inspect import isgeneratorfunction
from typing import Callable

import requests

from ..exception import RequestTransformerException


class RequestTransformer:
    register_function = {}

    def __init__(self, name: str, generator):
        if not isgeneratorfunction(generator):
            raise RequestTransformerException('注册为Request Transformer的函数应当为生成器函数')
        if name in self.register_function.keys():
            raise RequestTransformerException('请求转换器名称重复，已存在：' +
                                              RequestTransformer.register_function[name].__name__)

        RequestTransformer.register_function[name] = self
        self.name = name
        self.generator = generator

    def __call__(self, *args, **kwargs):
        self.as_sync_request(requests)(*args, **kwargs)

    def as_sync_request(self, request_handler) -> Callable:
        @wraps(self.generator)
        def inner_function(*args, **kwargs):
            try:
                generator = self.generator(*args, **kwargs)
                res = None
                while True:
                    params = generator.send(res)
                    res = request_handler.get(**params)
            except StopIteration as e:
                print(e.value)

        return inner_function

    def as_async_request(self, request_handler) -> Callable:
        @wraps(self.generator)
        async def inner_function(*args, **kwargs):
            try:
                generator = self.generator(*args, **kwargs)
                res = None
                while True:
                    params = generator.send(res)
                    res = await request_handler.get(**params)
            except StopIteration as e:
                print(e.value)

        return inner_function


    @classmethod
    def register(cls, name: str):
        def wrapped_function(func):
            return cls(name, func)

        return wrapped_function
