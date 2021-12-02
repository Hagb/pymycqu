"""考试相关的模块
"""
from __future__ import annotations
from typing import Dict, Any, Optional, List
from datetime import date, time
import requests
from .course import Course
from .utils.datetimes import date_from_str, time_from_str
# from pydantic.dataclasses import dataclass
from ._lib_wrapper.dataclass import dataclass
from ._lib_wrapper.Crypto import pad, AES

__all__ = ("Exam",)

EXAM_AES = AES.new("cquisse123456789".encode(), AES.MODE_ECB)
EXAM_LIST_URL = "https://my.cqu.edu.cn/api/exam/examTask/get-student-exam-list-outside"


def get_exam_raw(student_id: str) -> Dict[str, Any]:
    return requests.get(EXAM_LIST_URL,
                        params={"studentId":
                                EXAM_AES.encrypt(
                                    pad(student_id.encode(), 16, style='pkcs7')).hex().upper()
                                }
                        ).json()


@dataclass
class Invigilator:
    """监考员信息
    """
    name: str
    dept: str

    @staticmethod
    def from_dict(data: Dict[str, Optional[str]]) -> Invigilator:
        return Invigilator(
            name=data["instructor"],  # type: ignore
            dept=data["instDeptShortName"]  # type: ignore
        )


@dataclass
class Exam:
    """考试信息
    """
    course: Course
    batch: str
    batch_id: int
    building: str
    floor: int
    room: str
    stu_num: int
    date: date
    start_time: time
    end_time: time
    week: int
    weekday: int
    stu_id: str
    seat_num: int
    chief_invi: List[Invigilator]
    asst_invi: List[Invigilator]

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        course = Course.from_dict(data)
        return Exam(
            course=course,
            batch=data["batchName"],
            batch_id=data["batchId"],
            building=data["buildingName"],
            room=data["roomName"],
            floor=data["floorNum"],
            date=date_from_str(data["examDate"]),
            start_time=time_from_str(data["startTime"]),
            end_time=time_from_str(data["endTime"]),
            week=data["week"],
            weekday=int(data["weekDay"]) - 1,
            stu_id=data["studentId"],
            seat_num=data["seatNum"],
            stu_num=data["examStuNum"],
            chief_invi=[Invigilator.from_dict(invi)
                        for invi in data["simpleChiefinvigilatorVOS"]],
            asst_invi=[Invigilator.from_dict(invi)
                       for invi in data["simpleAssistantInviVOS"]]
        )

    @staticmethod
    def fetch(student_id: str) -> List[Exam]:
        """从 my.cqu.edu.cn 上获取指定学生的考表

        :param student_id: 学生学号
        :type student_id: str
        :return: 本学期的考表
        :rtype: List[Exam]
        """
        return [Exam.from_dict(exam)
                for exam in get_exam_raw(student_id)["data"]["content"]]
