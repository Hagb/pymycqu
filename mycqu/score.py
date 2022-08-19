"""
成绩相关模块
"""
from __future__ import annotations
import json
from typing import Dict, Any, Union, Optional, List
import requests
from requests import Session
from ._lib_wrapper.dataclass import dataclass
from .course import Course, CQUSession
from .exception import CQUWebsiteError, MycquUnauthorized

__all__ = ("Score", "GpaRanking")


def get_score_raw(auth: Union[Session, str], is_minor_boo: bool):
    """
    获取学生原始成绩

    :param auth: 登陆后获取的authorization或者调用过mycqu.access_mycqu的session
    :type auth: Union[Session, str]
    :param is_minor_boo: 是否获取辅修成绩
    :type is_minor_boo: bool
    :return: 反序列化获取的score列表
    :rtype: Dict
    """
    url = 'https://my.cqu.edu.cn/api/sam/score/student/score' + ('?isMinorBoo=true' if is_minor_boo else '')
    if isinstance(auth, requests.Session):
        res = auth.get(url)
    else:
        authorization = auth
        headers = {
            'Referer': 'https://my.cqu.edu.cn/sam/home',
            'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0)',
            'Authorization': authorization
        }
        res = requests.get(
            url, headers=headers)

    content = json.loads(res.content)
    if res.status_code == 401:
        raise MycquUnauthorized()
    if content['status'] == 'error':
        raise CQUWebsiteError(content['msg'])
    return content['data']


def get_gpa_ranking_raw(auth: Union[Session, str]):
    """
    获取学生绩点排名

    :param auth: 登陆后获取的authorization或者调用过mycqu.access_mycqu的session
    :type auth: Union[Session, str]
    :return: 反序列化获取的绩点、排名
    :rtype: Dict
    """
    if isinstance(auth, requests.Session):
        res = auth.get('https://my.cqu.edu.cn/api/sam/score/student/studentGpaRanking')
    else:
        authorization = auth
        headers = {
            'Referer': 'https://my.cqu.edu.cn/sam/home',
            'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0)',
            'Authorization': authorization
        }
        res = requests.get(
            'https://my.cqu.edu.cn/api/sam/score/student/studentGpaRanking', headers=headers)

    content = json.loads(res.content)
    if res.status_code == 401:
        raise MycquUnauthorized()
    if content['status'] == 'error':
        raise CQUWebsiteError(content['msg'])
    return content['data']


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
