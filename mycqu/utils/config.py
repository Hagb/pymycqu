from typing import Dict

from .request_transformer.params_mapper import RequestsParamsMapper, HttpxParamsMapper

__all__ = ['ConfigManager']


PYMYCQU_CONFIG = {
    'request': {
        'sync_request_params_mapper': RequestsParamsMapper,
        'async_request_params_mapper': HttpxParamsMapper
    }
}


def singleton(cls):
    _instance = {}

    def inner() -> 'ConfigManager':
        if cls not in _instance:
            _instance[cls] = cls()
        return _instance[cls]
    return inner

@singleton
class ConfigManager:
    def __init__(self):
        self._config = PYMYCQU_CONFIG

    @property
    def config(self) -> Dict:
        return self._config

    @config.setter
    def config(self, value):
        self._config = value

