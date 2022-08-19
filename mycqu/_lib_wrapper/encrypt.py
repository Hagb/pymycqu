"""从两种模块不同的模块名字中加载加密模块
"""
from typing import Callable
try:
    from Cryptodome.Cipher import AES as _AES
    from Cryptodome.Cipher import DES as _DES
    from Cryptodome.Util.Padding import pad as _pad
except ImportError:
    try:
        from Crypto.Cipher import AES as _AES  # type: ignore
        from Crypto.Cipher import DES as _DES  # type: ignore
        from Crypto.Util.Padding import pad as _pad  # type: ignore
    except ImportError:
        raise ImportError(  # pylint: ignore disable=raise-missing-from
            "Please install pyryptodome, pyryptodomex")


def pad16(x: bytes) -> bytes:
    return _pad(x, 16, style='pkcs7')


def pad8(x: bytes) -> bytes:
    return _pad(x, 8, style='pkcs7')


def aes_cbc_encryptor(key: bytes, iv: bytes) -> Callable[[bytes], bytes]:
    return _AES.new(key=key, iv=iv, mode=_AES.MODE_CBC).encrypt


def aes_ecb_encryptor(key: bytes) -> Callable[[bytes], bytes]:
    return _AES.new(key, _AES.MODE_ECB).encrypt


def des_ecb_encryptor(key: bytes) -> Callable[[bytes], bytes]:
    return _DES.new(key, _DES.MODE_ECB).encrypt


__all__ = ("aes_cbc_encryptor", "aes_ecb_encryptor",
           "des_ecb_encryptor", "pad16", "pad8")
