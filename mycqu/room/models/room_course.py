from typing import Dict, Any

from ..._lib_wrapper.dataclass import dataclass
from .room_activity_info import RoomActivityInfo


@dataclass
class RoomCourse:
    """教室课程活动"""
    activity_info: RoomActivityInfo
    """基础信息"""
    class_number: str
    """教学班号"""
    course_code: str
    """课程代码"""
    course_name: str
    """课程名称"""
    department: str
    """开课学院"""
    stu_num: int
    """选课学生数"""
    credit: float
    """课程学分"""
    instructor_name: str
    """教师姓名"""

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        """从反序列化的一个教室课程信息 json 中生成RoomCourse对象

        :param data: 反序列化成字典的教室课程 json
        :type data: Dict[str, Any]
        :return: 教室课程
        :rtype: RoomCourse
        """
        return RoomCourse(
            activity_info=RoomActivityInfo.from_dict(data),
            class_number=data['classNbr'],
            course_code=data['courseCode'],
            course_name=data['courseName'],
            department=data['courseDepartmentName'],
            stu_num=int(data['selectedStuNum']),
            credit=float(data['credit']),
            instructor_name=data['instructorName'],
        )