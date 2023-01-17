from typing import List, Dict, Any

from datetime import date

from ..._lib_wrapper.dataclass import dataclass
from .room_activity_info import RoomActivityInfo
from ...utils.datetimes import date_from_str

__all__ = ['RoomTempActivity']


@dataclass
class RoomTempActivity:
    """教室临时活动"""
    activity_info: RoomActivityInfo
    """基础信息"""
    content: str
    """临时活动名称"""
    department: str
    """申请学院"""
    type: str
    """临时活动类型，如上课、开会等"""
    time_range: str
    """活动持续时间"""
    date: List[date]
    """活动举办日期"""

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        """从反序列化的一个教室临时活动信息 json 中生成RoomTempActivity对象

        :param data: 反序列化成字典的教室临时活动 json
        :type data: Dict[str, Any]
        :return: 教室临时活动
        :rtype: RoomTempActivity
        """
        return RoomTempActivity(
            activity_info=RoomActivityInfo.from_dict(data),
            content=data['actContent'],
            department=data['actDepartment'],
            type=data['tempActType'],
            time_range=data['timeIn'],
            date=[date_from_str(date) for date in data['dateStr'].split(',')]
        )
