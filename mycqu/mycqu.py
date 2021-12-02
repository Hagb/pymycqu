"""my.cqu.edu.cn 认证相关的模块
"""
from typing import Dict
import re
from requests import Session
from .auth import access_service
__all__ = ("access_mycqu",)

MYCQU_TOKEN_INDEX_URL = "https://my.cqu.edu.cn/enroll/token-index"
MYCQU_TOKEN_URL = "https://my.cqu.edu.cn/authserver/oauth/token"
MYCQU_AUTHORIZE_URL = f"https://my.cqu.edu.cn/authserver/oauth/authorize?client_id=enroll-prod&response_type=code&scope=all&state=&redirect_uri={MYCQU_TOKEN_INDEX_URL}"
MYCQU_SERVICE_URL = "http://my.cqu.edu.cn/authserver/authentication/cas"
CODE_RE = re.compile(r"\?code=([^&]+)&")


class MycquUnauthorized(Exception):
    def __init__(self):
        super().__init__("Unanthorized in mycqu, auth.login firstly and then mycqu.access_mycqu")


def get_oauth_token(session: Session) -> str:
    # from https://github.com/CQULHW/CQUQueryGrade
    resp = session.get(MYCQU_AUTHORIZE_URL, allow_redirects=False)
    assert (match := CODE_RE.search(resp.headers['Location']))
    token_data = {
        'client_id': 'enroll-prod',
        'client_secret': 'app-a-1234',
        'code': match[1],
        'redirect_uri': MYCQU_TOKEN_INDEX_URL,
        'grant_type': 'authorization_code'
    }
    access_token = session.post(MYCQU_TOKEN_URL, data=token_data)
    return "Bearer " + access_token.json()['access_token']


def access_mycqu(session: Session, add_to_header: bool = True) -> Dict[str, str]:
    """用登陆了统一身份认证的会话在 my.cqu.edu.cn 进行认证

    :param session: 登陆了统一身份认证的会话
    :type session: Session
    :param add_to_header: 是否将 mycqu 的认证信息写入会话属性，默认为 :obj:`True`
    :type add_to_header: bool, optional
    :return: mycqu 认证信息的请求头，当 ``add_to_header`` 参数为 :obj:`True` 时无需手动使用该返回值
    :rtype: Dict[str, str]
    """
    session.get(access_service(session, MYCQU_SERVICE_URL).headers['Location'],
                allow_redirects=False)  # http 302 to https
    token = get_oauth_token(session)
    if add_to_header:
        session.headers["Authorization"] = token
    return {"Authorization": token}
