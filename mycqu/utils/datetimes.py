from typing import List, Tuple, Dict
from datetime import date, time
import pytz
TIMEZONE = pytz.timezone("Asia/Shanghai")
WEEKDAY: Dict[str, int] = {
    "一": 0,
    "二": 1,
    "三": 2,
    "四": 3,
    "五": 4,
    "六": 5,
    "日": 6
}


def time_from_str(string: str) -> time:
    hour, minute = map(int, string.split(":"))
    return time(hour, minute, second=0, tzinfo=TIMEZONE)


def parse_period_str(string: str) -> Tuple[int, int]:
    period = tuple(map(int, string.split("-")))
    assert len(period) == 1 or len(period) == 2
    return period[0], (period[1] if len(period) == 2 else period[0])


def parse_weeks_str(string: str) -> List[Tuple[int, int]]:
    return [parse_period_str(unit) for unit in string.split(',')]


def parse_weekday_str(string: str) -> int:
    return WEEKDAY[string]


def date_from_str(string: str) -> date:
    return date.fromisoformat(string)
