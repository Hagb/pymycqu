from __future__ import annotations

from typing import Any, Dict, List

from requests import Session

from ...exception import MycquUnauthorized
from ..._lib_wrapper.dataclass import dataclass
from ...utils.request_transformer import Request, RequestTransformer

ROOM_ID_URL = "https://my.cqu.edu.cn/api/resourceapi/room/roomName-filter"

__all__ = ['Room']


@dataclass
class Room:
    """教室对象，储存了某个教室的相关信息"""
    id: int
    """教室id"""
    name: str
    """教室名称，如D1345"""
    capacity: int
    """教室容量"""
    building_name: str
    """教室所属建筑名称"""
    campus_name: str
    """教室所属校区"""
    room_type: str
    """教室类型"""

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Room:
        """从反序列化的一个教室信息 json 中生成教室对象

        :param data: 反序列化成字典的教室 json
        :type data: Dict[str, Any]
        :return: 教室对象
        :rtype: Room
        """
        return Room(
            id=int(data['id']),
            name=data['name'],
            capacity=int(data['capacity']),
            building_name=data['buildingName'],
            campus_name=data['campusName'],
            room_type=data['roomClassificationName']
        )

    @staticmethod
    @RequestTransformer.register()
    def _fetch(session: Session, name: str) -> List[Room]:
        res = yield session.get(ROOM_ID_URL, params={'roomName': name})
        if res.status_code == 401:
            raise MycquUnauthorized

        return [Room.from_dict(room) for room in res.json()]

    @staticmethod
    def fetch(session: Session, name: str) -> List[Room]:
        """
        依据教室名字查询教室（支持模糊查询）

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
        :type session: Session
        :param name: 教室名称
        :type name: str
        :return: 教室对象组成的列表
        :rtype: List[Room]
        """
        return Room._fetch.sync_request(session, name)

    @staticmethod
    async def async_fetch(session: Request, name: str) -> List[Room]:
        """
        依据教室名字查询教室（支持模糊查询）

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
        :type session: Session
        :param name: 教室名称
        :type name: str
        :return: 教室对象组成的列表
        :rtype: List[Room]
        """
        return await Room._fetch.async_request(session, name)

