from __future__ import annotations

from typing import Dict, Any, Union, Optional, List
from requests import Session

from ..tools import get_score_raw, async_get_score_raw
from ..._lib_wrapper.dataclass import dataclass
from ...course import Course, CQUSession

__all__ = ['Score']


@dataclass
class Score:
    """
    成绩对象
    """
    session: CQUSession
    """学期"""
    course: Course
    """课程"""
    score: Optional[str]
    """成绩，可能为数字，也可能为字符（优、良等）"""
    study_nature: str
    """初修/重修"""
    course_nature: str
    """必修/选修"""

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Score:
        """
        从反序列化的字典生成Score对象

        @param: data
        @type: dict
        @return: 返回成绩对象
        @rtype: Score
        """
        return Score(
            session=CQUSession.from_str(data["sessionName"]),
            course=Course.from_dict(data),
            score=data['effectiveScoreShow'],
            study_nature=data['studyNature'],
            course_nature=data['courseNature']
        )

    @staticmethod
    def fetch(auth: Union[str, Session], is_minor_boo: bool = False) -> List[Score]:
        """
        从网站获取成绩信息

        :param auth: 登陆后获取的 authorization 或者调用过 :func:`.mycqu.access_mycqu` 的 Session
        :type auth: Union[Session, str]
        :param is_minor_boo: 是否获取辅修成绩
        :type is_minor_boo: bool
        :return: 返回成绩对象
        :rtype: List[Score]
        :raises CQUWebsiteError: 查询时教务网报错
        """
        temp = get_score_raw(auth, is_minor_boo)
        score = []
        for courses in temp.values():
            for course in courses['stuScoreHomePgVoS']:
                score.append(Score.from_dict(course))
        return score

    @staticmethod
    async def async_fetch(auth: Union[str, Session], is_minor_boo: bool = False) -> List[Score]:
        """
        异步的从网站获取成绩信息

        :param auth: 登陆后获取的 authorization 或者调用过 :func:`.mycqu.access_mycqu` 的 Session
        :type auth: Union[Session, str]
        :param is_minor_boo: 是否获取辅修成绩
        :type is_minor_boo: bool
        :return: 返回成绩对象
        :rtype: List[Score]
        :raises CQUWebsiteError: 查询时教务网报错
        """
        temp = await async_get_score_raw(auth, is_minor_boo)
        score = []
        for courses in temp.values():
            for course in courses['stuScoreHomePgVoS']:
                score.append(Score.from_dict(course))
        return score