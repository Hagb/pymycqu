from __future__ import annotations

from typing import Dict, Any, Union, Optional
from requests import Session

from ..tools import get_gpa_ranking_raw, async_get_gpa_ranking_raw
from ..._lib_wrapper.dataclass import dataclass

__all__ = ['GpaRanking']


@dataclass
class GpaRanking:
    """
    绩点对象
    """
    gpa: float
    """学生总绩点"""
    majorRanking: Optional[int]
    """专业排名"""
    gradeRanking: Optional[int]
    """年级排名"""
    classRanking: Optional[int]
    """班级排名"""
    weightedAvg: float
    """加权平均分"""
    minorWeightedAvg: Optional[float]
    """辅修加权平均分"""
    minorGpa: Optional[float]
    """辅修绩点"""

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> GpaRanking:
        """
        从反序列化的字典生成GpaRanking对象

        @param: data
        @type: dict
        @return: 返回绩点排名对象
        @rtype: GpaRanking
        """
        return GpaRanking(
            gpa=float(data['gpa']),
            majorRanking=data['majorRanking'] and int(data['majorRanking']),
            gradeRanking=data['gradeRanking'] and int(data['gradeRanking']),
            classRanking=data['classRanking'] and int(data['classRanking']),
            weightedAvg=float(data['weightedAvg']),
            minorWeightedAvg=data['minorWeightedAvg'] and float(data['minorWeightedAvg']),
            minorGpa=data['minorGpa'] and float(data['minorGpa']),
        )

    @staticmethod
    def fetch(auth: Union[str, Session]) -> GpaRanking:
        """
        从网站获取绩点排名信息

        :param auth: 登陆后获取的 authorization 或者调用过 :func:`.mycqu.access_mycqu` 的 Session
        :type auth: Union[Session, str]
        :return: 返回绩点排名对象
        :rtype: GpaRanking
        :raises CQUWebsiteError: 查询时教务网报错
        """
        return GpaRanking.from_dict(get_gpa_ranking_raw(auth))

    @staticmethod
    async def async_fetch(auth: Union[str, Session]) -> GpaRanking:
        """
        异步的从网站获取绩点排名信息

        :param auth: 登陆后获取的 authorization 或者调用过 :func:`.mycqu.access_mycqu` 的 Session
        :type auth: Union[Session, str]
        :return: 返回绩点排名对象
        :rtype: GpaRanking
        :raises CQUWebsiteError: 查询时教务网报错
        """
        return GpaRanking.from_dict(await async_get_gpa_ranking_raw(auth))
