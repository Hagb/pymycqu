from typing import Dict, Any, List

from ..._lib_wrapper.dataclass import dataclass
from .room_activity_info import RoomActivityInfo
from .room_exam_invigilator import RoomExamInvigilator

__all__ = ['RoomExam']


@dataclass
class RoomExam:
    """教室中考试活动相关信息"""
    activity_info: RoomActivityInfo
    """基础信息"""
    course_name: str
    """考试课程名称"""
    stu_capacity: int
    """考试学生数量"""
    time_range: str
    """持续时间"""
    invigilators: List[RoomExamInvigilator]
    """监考员信息"""

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        """从反序列化的一个教室考试信息 json 中生成RoomExam对象

        :param data: 反序列化成字典的教室考试 json
        :type data: Dict[str, Any]
        :return: 教室考试
        :rtype: RoomExam
        """
        return RoomExam(
            activity_info=RoomActivityInfo.from_dict(data),
            course_name=data['courseName'],
            stu_capacity=int(data['stuCapacity']),
            time_range=data['timeIn'],
            invigilators=[RoomExamInvigilator.from_dict(temp) for temp in data['invigilatorVOList']]
        )
