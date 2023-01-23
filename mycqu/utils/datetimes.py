from typing import List, Tuple, Dict, Optional
from datetime import date, time, datetime
import pytz

TIMEZONE = datetime.now(pytz.timezone("Asia/Shanghai")).tzinfo
SHORT_WEEKDAY: Dict[str, int] = {
    "一": 0,
    "二": 1,
    "三": 2,
    "四": 3,
    "五": 4,
    "六": 5,
    "日": 6
}
LONG_WEEKDAY: Dict[str, int] = {
    "星期一": 0,
    "星期二": 1,
    "星期三": 2,
    "星期四": 3,
    "星期五": 4,
    "星期六": 5,
    "星期日": 6
}


def time_from_str(string: str) -> time:
    hour, minute = map(int, string.split(":"))
    return time(hour, minute, tzinfo=TIMEZONE)


def parse_period_str(string: str) -> Tuple[int, int]:
    period = tuple(map(int, string.split("-")))
    assert len(period) == 1 or len(period) == 2
    return period[0], (period[1] if len(period) == 2 else period[0])


def parse_weeks_str(string: str) -> List[Tuple[int, int]]:
    return [parse_period_str(unit) for unit in string.split(',')]


def parse_weekday_str(string: str) -> Optional[int]:
    return SHORT_WEEKDAY.get(string) if SHORT_WEEKDAY.get(string) is not None else LONG_WEEKDAY.get(string)


def date_from_str(string: str) -> Optional[date]:
    return date.fromisoformat(string) if string is not None else None


def datetime_from_str(string: str) -> datetime:
    return datetime.strptime(string, '%Y-%m-%d %H:%M:%S').replace(tzinfo=TIMEZONE)
