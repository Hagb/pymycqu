"""从两种模块不同的模块名字中加载加密模块
"""
from typing import Callable
pad: Callable[[bytes], bytes]
aes_cbc_encryptor: Callable[[bytes, bytes], Callable[[bytes], bytes]]
aes_ecb_encryptor: Callable[[bytes], Callable[[bytes], bytes]]
try:
    from Cryptodome.Cipher import AES as AES_
    from Cryptodome.Util.Padding import pad as pad_
except (OSError, ImportError):
    try:
        from Crypto.Cipher import AES as AES__
        from Crypto.Util.Padding import pad as pad__
    except (OSError, ImportError):
        try:
            from pyaes.util import append_PKCS7_padding  # type: ignore
            from pyaes import AESModeOfOperationCBC  # type: ignore
            from pyaes import AESModeOfOperationECB

            def aes_cbc_encryptor(key, iv):
                encrypt = AESModeOfOperationCBC(key, iv).encrypt
                return lambda x: b''.join(encrypt(x[i: i+16]) for i in range(0, len(x), 16))

            def aes_ecb_encryptor(key):
                encrypt = AESModeOfOperationECB(key).encrypt
                return lambda x: b''.join(encrypt(x[i: i+16]) for i in range(0, len(x), 16))
            pad = append_PKCS7_padding
        except ImportError:
            raise ImportError(  # pylint: ignore disable=raise-missing-from
                "Please install pyryptodome, pyryptodomex or pyaes")
    else:
        def pad(x):
            return pad__(x, 16, style='pkcs7')

        def aes_cbc_encryptor(key, iv):
            return AES__.new(key=key, iv=iv, mode=AES__.MODE_CBC).encrypt

        def aes_ecb_encryptor(key):
            return AES__.new(key, AES__.MODE_ECB).encrypt
else:
    def pad(x):
        return pad_(x, 16, style='pkcs7')

    def aes_cbc_encryptor(key, iv):
        return AES_.new(key=key, iv=iv, mode=AES_.MODE_CBC).encrypt

    def aes_ecb_encryptor(key):
        return AES_.new(key, AES_.MODE_ECB).encrypt

__all__ = ("aes_cbc_encryptor", "aes_ecb_encryptor", "pad")
