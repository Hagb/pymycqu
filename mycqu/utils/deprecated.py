from functools import wraps
from warnings import warn

__all__ = ['deprecated']

def deprecated(reason: str):
    def wrapped_function(func):
        @wraps(func)
        def inner_function(*args, **kwargs):
            warning_info = f'函数："{func.__name__}" 已被弃用，即将在后续版本被移除，弃用信息：{reason}'
            warn(warning_info, DeprecationWarning)
            return func(*args, **kwargs)
        return inner_function
    return wrapped_function
