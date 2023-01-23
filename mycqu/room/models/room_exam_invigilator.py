from typing import Dict, Any

from ..._lib_wrapper.dataclass import dataclass

__all__ = ['RoomExamInvigilator']


@dataclass
class RoomExamInvigilator:
    """教室考试活动监考员信息"""
    name: str
    """姓名"""
    type: str
    """监考类型，如副监考、巡考等"""
    dept_name: str
    """所在部门名称"""

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        """从反序列化的一个教室考试监考员信息 json 中生成RoomExamInvigilator对象

        :param data: 反序列化成字典的教室考试监考员信息 json
        :type data: Dict[str, Any]
        :return: 教室考试活动监考员对象
        :rtype: RoomExamInvigilator
        """
        return RoomExamInvigilator(
            name=data['name'],
            type=data['invigilatorType'],
            dept_name=data['deptName']
        )
