from __future__ import annotations

import json
from typing import List, Dict

from requests import Session

from ..utils.request_transformer import Request, RequestTransformer

ENROLLMENT_COURSE_LIST_URL = "https://my.cqu.edu.cn/api/enrollment/enrollment/course-list?selectionSource="
ENROLLMENT_COURSE_DETAIL_URL = "https://my.cqu.edu.cn/api/enrollment/enrollment/courseDetails/"


__all__ = ['get_enroll_list_raw', 'get_enroll_detail_raw',
           'async_get_enroll_list_raw', 'async_get_enroll_detail_raw']


@RequestTransformer.register()
def _get_enroll_list_raw(session: Request, is_major: bool = True) -> Dict[str: List]:
    url = ENROLLMENT_COURSE_LIST_URL + ("主修" if is_major else "辅修")
    res = yield session.get(url)
    content = json.loads(res.text)
    assert content["status"] == "success"

    result = {}
    for data in content["data"]:
        result[data["selectionArea"]] = data["courseVOList"]

    return result

def get_enroll_list_raw(session: Session, is_major: bool = True) -> Dict[str: List]:
    """

    从 my.cqu.edu.cn 上获取学生可选课程

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    :param is_major: 是否查询主修专业可选课程(为false时查询辅修专业可选课程)
    :type is_major: bool
    :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 进行认证
    :return: 反序列化获取可选课程的的json
    :rtype: Dict[str, List]
    """

    return _get_enroll_list_raw.sync_request(session, is_major)

async def async_get_enroll_list_raw(session: Request, is_major: bool = True) -> Dict[str: List]:
    """

    异步的从 my.cqu.edu.cn 上获取学生可选课程

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    :param is_major: 是否查询主修专业可选课程(为false时查询辅修专业可选课程)
    :type is_major: bool
    :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 进行认证
    :return: 反序列化获取可选课程的的json
    :rtype: Dict[str, List]
    """

    return await _get_enroll_list_raw.async_request(session, is_major)

@RequestTransformer.register()
def _get_enroll_detail_raw(session: Request, course_id: str, is_major: bool = True) -> List:
    url = ENROLLMENT_COURSE_DETAIL_URL + course_id + "?selectionSource=" + ("主修" if is_major else "辅修")
    res = yield session.get(url)
    content = json.loads(res.text)
    return content['selectCourseListVOs'][0]['selectCourseVOList'] if len(content['selectCourseListVOs']) > 0 else []

def get_enroll_detail_raw(session: Session, course_id: str, is_major: bool = True) -> List:
    """
    从 my.cqu.edu.cn 上获取某可选课程详情

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    :param course_id: 待查询课程参数
    :type course_id: str
    :param is_major: 待查询课程是否为主修课程(为false时表示查询辅修可选课程)
    :type is_major: bool
    :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 进行认证
    :return: 反序列化查询到当可选课程的的json
    :rtype: List
    """
    return _get_enroll_detail_raw.sync_request(session, course_id, is_major)

async def async_get_enroll_detail_raw(session: Request, course_id: str, is_major: bool = True) -> List:
    """
    异步的从 my.cqu.edu.cn 上获取某可选课程详情

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    :param course_id: 待查询课程参数
    :type course_id: str
    :param is_major: 待查询课程是否为主修课程(为false时表示查询辅修可选课程)
    :type is_major: bool
    :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 进行认证
    :return: 反序列化查询到当可选课程的的json
    :rtype: List
    """
    return await _get_enroll_detail_raw.async_request(session, course_id, is_major)
