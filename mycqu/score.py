import requests
import json
from typing import Dict, Any, Union, Optional, List
from ._lib_wrapper.dataclass import dataclass
from .course import Course, CQUSession


def get_score_raw(authorization: str):
    """
    获取学生原始成绩
    :param authorization: 登陆后获取的authorization
    :type authorization: str
    :return: 反序列化获取的score列表
    :rtype: Dict
    """
    headers = {
        'Referer': 'https://my.cqu.edu.cn/sam/home',
        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0)',
        'Authorization': authorization
    }
    res = requests.get('http://my.cqu.edu.cn/api/sam/score/student/score', headers=headers)
    return json.loads(res.content)['data']


@dataclass(order=True)
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
    def from_dict(data: Dict[str, Any],
                  session: Optional[Union[str, CQUSession]] = None):
        """
        从反序列化的字典生成Score对象

        @param: data
        @type: dict
        @return: 返回成绩对象
        @rtype: Score
        """
        if session is None and not data.get("session") is None:
            session = CQUSession.from_str(data["session"])
        if isinstance(session, str):
            session = CQUSession.from_str(session)
        course = Course.from_dict(data)
        return Score(
            session=session,
            course=course,
            score=data['effectiveScoreShow'],
            study_nature=data['studyNature'],
            course_nature=data['courseNature']
        )

    @staticmethod
    def fetch(authorization: str) -> List:
        """
        从网站获取成绩信息

        @param: authorization 登陆后获取的authorization
        @type: str
        @return: 返回成绩对象
        @rtype: List
        """
        temp = get_score_raw(authorization)
        score = []
        for term, courses in temp.items():
            for course in courses:
                score.append(Score.from_dict(course, term))
        return score
