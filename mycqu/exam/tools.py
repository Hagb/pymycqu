"""考试相关的模块
"""
from __future__ import annotations

from typing import Dict, Any, Optional

import requests

from .._lib_wrapper.encrypt import pad16, aes_ecb_encryptor

from ..utils.request_transformer import Request, RequestTransformer

__all__ = ['get_exam_raw', 'async_get_exam_raw']

__exam_encryptor = aes_ecb_encryptor("cquisse123456789".encode())
EXAM_LIST_URL = "https://my.cqu.edu.cn/api/exam/examTask/get-student-exam-list-outside"


@RequestTransformer.register()
def _get_exam_raw(session: Request, student_id: str) -> Dict[str, Any]:
    return (yield session.get(EXAM_LIST_URL,
                              params={"studentId": __exam_encryptor(pad16(student_id.encode())).hex().upper()}
                              )).json()

def get_exam_raw(student_id: str, session: Optional[requests.Session] = None) -> Dict[str, Any]:
    """获取考表的原始 json 数据（被反序列化为 python 字典对象）

    :param student_id: 学号
    :type student_id: str
    :param session: 用于请求的 requests session
    :type session: requests.Session, optional
    :return: 反序列化后的课表 json 数据
    :rtype: Dict[str, Any]
    """
    return _get_exam_raw.sync_request((session or requests), student_id)

async def async_get_exam_raw(session: Request, student_id: str) -> Dict[str, Any]:
    """获取考表的原始 json 数据（被反序列化为 python 字典对象）

    :param session: 用于请求的 requests session
    :type session: requests.Session
    :param student_id: 学号
    :type student_id: str
    :return: 反序列化后的课表 json 数据
    :rtype: Dict[str, Any]
    """
    return await _get_exam_raw.async_request((session or requests), student_id)
