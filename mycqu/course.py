from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, List, Union, ClassVar
#from pydantic.dataclasses import dataclass
from .dataclass import dataclass
from .utils.datetimes import parse_period_str, parse_weeks_str, parse_weekday_str, date_from_str
from .mycqu import MycquUnauthorized
from requests import Session, get
from datetime import date
import re
__all__ = ("CQUSession", "CQUSessionInfo", "CourseTimetable")


CQUSESSIONS_URL = "http://my.cqu.edu.cn/api/timetable/optionFinder/session?blankOption=false"
CUR_SESSION_URL = "http://my.cqu.edu.cn/api/resourceapi/session/cur-active-session"
TIMETABLE_URL = "http://my.cqu.edu.cn/api/timetable/class/timetable/student/table-detail"


@dataclass(order=True)
class CQUSession:
    year: int
    is_autumn: bool
    SESSION_RE: ClassVar = re.compile("^([0-9]{4})年?(春|秋)$")
    CQUSESSION_MIN: ClassVar[CQUSession]

    def __post_init_post_parse__(self):
        if hasattr(CQUSession, "CQUSESSION_MIN"):
            if self < CQUSession.CQUSESSION_MIN:
                raise ValueError(
                    f"session should not be earlier than {CQUSession.CQUSESSION_MIN}")

    def get_id(self) -> int:
        return (self.year-1503)*2 + int(self.is_autumn) + 1

    @staticmethod
    def from_str(string: str) -> CQUSession:
        match = CQUSession.SESSION_RE.match(string)
        if match:
            return CQUSession(
                year=match[1],
                is_autumn=match[2] == "秋"
            )
        else:
            raise ValueError(f"string {string} is not a session")

    @staticmethod
    def fetch() -> List[CQUSession]:
        session_list = []
        for session in get(CQUSESSIONS_URL).json():
            try:
                session_list.append(CQUSession.from_str(session["name"]))
            except ValueError:
                pass
        return session_list


CQUSession.CQUSESSION_MIN = CQUSession(2020, True)


@dataclass
class CQUSessionInfo:
    session: CQUSession
    begin_date: date
    end_date: date

    @staticmethod
    def fetch(session: Session) -> CQUSessionInfo:
        resp = session.get(CUR_SESSION_URL)
        if resp.status_code == 401:
            raise MycquUnauthorized()
        data = resp.json()["data"]
        return CQUSessionInfo(
            session=CQUSession(year=data["year"],
                               is_autumn=data["term"] == "秋"),
            begin_date=date_from_str(data["beginDate"]),
            end_date=date_from_str(data["endDate"])
        )


@dataclass
class CourseDayTime:
    weekday: int
    period: Tuple[int, int]

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Optional[CourseDayTime]:
        if "periodFormat" in data and "weekDayFormat" in data:
            return CourseDayTime(
                weekday=parse_weekday_str(data["weekDayFormat"]),
                period=parse_period_str(data["periodFormat"])
            )
        return None


@ dataclass
class Course:
    name: str
    code: str
    course_num: Optional[str]
    dept: str
    credit: Optional[float]
    instructor: Optional[str]
    session: Optional[CQUSession]

    @ staticmethod
    def from_dict(data: Dict[str, Any],
                  session: Optional[Union[str, CQUSession]] = None) -> Course:
        if session is None and not (data.get("session") is None):
            session = CQUSession.from_str(data["session"])
        if isinstance(session, str):
            session = CQUSession.from_str(session)
        return Course(
            name=data["courseName"],
            code=data["courseCode"],
            course_num=data.get("classNbr"),
            dept=data.get(
                "courseDepartmentName") or data["courseDeptShortName"],
            credit=data.get("credit"),
            instructor=data.get("instructorName"),
            session=session,
        )


@ dataclass
class CourseTimetable:
    course: Course
    stu_num: int
    classroom: Optional[str]
    weeks: List[Tuple[int, int]]
    day_time: Optional[CourseDayTime]
    whole_week: bool

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> CourseTimetable:
        return CourseTimetable(
            course=Course.from_dict(data),
            stu_num=data["selectedStuNum"],
            classroom=data["roomName"],
            weeks=parse_weeks_str(data.get("weeks")
                                  or data.get("teachingWeekFormat")),
            day_time=CourseDayTime.from_dict(data),
            whole_week=bool(data["wholeWeekOccupy"])
        )

    @staticmethod
    def fetch(session: Session, stu_id: str, cqu_session: Optional[Union[CQUSession, str]] = None) -> List[CourseTimetable]:
        if cqu_session is None:
            cqu_session = CQUSessionInfo.fetch(session).session
        elif isinstance(cqu_session, str):
            cqu_session = CQUSession.from_str(cqu_session)
        resp = session.post(TIMETABLE_URL,
                            params={"sessionId": cqu_session.get_id()},
                            json=[stu_id],
                            )
        if resp.status_code == 401:
            raise MycquUnauthorized()
        return [CourseTimetable.from_dict(timetable) for timetable in resp.json()["classTimetableVOList"]
                if timetable["teachingWeekFormat"]
                ]
