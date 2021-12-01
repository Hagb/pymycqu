"""从两种模块不同的模块名字中加载加密模块
"""
try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad as pad
except ImportError:
    from Crypto.Cipher import AES  # type: ignore
    from Crypto.Util.Padding import pad


__all__ = ("AES", "pad")
