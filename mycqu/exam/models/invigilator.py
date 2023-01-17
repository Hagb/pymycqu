from __future__ import annotations

from typing import Dict, Optional

from ..._lib_wrapper.dataclass import dataclass
from ..._lib_wrapper.encrypt import pad16, aes_ecb_encryptor


__all__ = ['Invigilator']

@dataclass
class Invigilator:
    """监考员信息
    """
    name: str
    """监考员姓名"""
    dept: str
    """监考员所在学院（可能是简称，如 :obj:`"数统"`）"""

    @staticmethod
    def from_dict(data: Dict[str, Optional[str]]) -> Invigilator:
        """从反序列化后的 json 数据中一名正/副监考员的数据中生成 :class:`Invigilator` 对象。

        :param data: 反序列化后的 json 数据中的一次考试数据
        :type data: Dict[str, Optional[str]]
        :return: 对应的 :class:`Invigilator` 对象
        :rtype: Invigilator
        """
        return Invigilator(
            name=data["instructor"],  # type: ignore
            dept=data["instDeptShortName"]  # type: ignore
        )