from __future__ import annotations
from typing import Dict, Any, Optional, List, Tuple, List
import requests
from .course import Course
from .utils.datetimes import date_from_str, time_from_str
# from pydantic.dataclasses import dataclass
from .dataclass import dataclass
from datetime import date, time

try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad
except ModuleNotFoundError:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    from Crypto import version_info
    if version_info[0] == 2:
        # pylint: ignore disable=raise-missing-from
        raise ModuleNotFoundError(
            'Need either `pycryptodome` or `pycryptodomex`!')

__all__ = ("Exam",)

EXAM_AES = AES.new("cquisse123456789".encode(), AES.MODE_ECB)
EXAM_LIST_URL = "http://my.cqu.edu.cn/api/exam/examTask/get-student-exam-list-outside"


def get_exam_raw(student_id: str) -> Dict[str, Any]:
    return requests.get(EXAM_LIST_URL,
                        params={"studentId":
                                EXAM_AES.encrypt(
                                    pad(student_id.encode(), 16, style='pkcs7')).hex().upper()
                                }
                        ).json()


@dataclass
class Invigilator:
    name: str
    dept: str

    @staticmethod
    def from_dict(data: Dict[str, Optional[str]]) -> Invigilator:
        return Invigilator(
            name=data["instructor"],
            dept=data["instDeptShortName"]
        )


@dataclass
class Exam:
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
        return [Exam.from_dict(exam)
                for exam in get_exam_raw(student_id)["data"]["content"]]
