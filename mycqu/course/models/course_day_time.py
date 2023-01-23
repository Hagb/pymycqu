from __future__ import annotations
from typing import Any, Dict, Optional, Tuple

from ..._lib_wrapper.dataclass import dataclass
from ...utils.datetimes import parse_period_str, parse_weekday_str


__all__ = ['CourseDayTime']

@dataclass
class CourseDayTime:
    """课程一次的星期和节次
    """
    weekday: int
    """星期，0 为周一，6 为周日，此与 :attr:`datetime.date.day` 一致"""
    period: Tuple[int, int]
    """节次，第一个元素为开始节次，第二个元素为结束节次（该节次也包括在范围内）。
    只有一节课时，两个元素相同。
    """

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Optional[CourseDayTime]:
        """从反序列化的（一个）课表 json 中获取课程的星期和节次

        :param data: 反序列化成字典的课表 json
        :type data: Dict[str, Any]
        :return: 若其中有课程的星期和节次则返回相应对象，否则返回 :obj:`None`
        :rtype: Optional[CourseDayTime]
        """
        if data.get("periodFormat") and data.get("weekDayFormat"):
            return CourseDayTime(
                weekday=parse_weekday_str(data["weekDayFormat"]),
                period=parse_period_str(data["periodFormat"])
            )
        return None
