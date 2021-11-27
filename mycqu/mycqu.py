from typing import Dict
import re
from .auth import access_service
from requests import Session
__all__ = ("access_mycqu",)

MYCQU_TOKEN_INDEX_URL = "http://my.cqu.edu.cn/enroll/token-index"
MYCQU_TOKEN_URL = "http://my.cqu.edu.cn/authserver/oauth/token"
MYCQU_AUTHORIZE_URL = f"http://my.cqu.edu.cn/authserver/oauth/authorize?client_id=enroll-prod&response_type=code&scope=all&state=&redirect_uri={MYCQU_TOKEN_INDEX_URL}"
MYCQU_SERVICE_URL = "http://my.cqu.edu.cn/authserver/authentication/cas"
CODE_RE = re.compile(r"\?code=([^&]+)&")


class MycquUnauthorized(Exception):
    def __init__(self):
        super().__init__("Unanthorized in mycqu, auth.login firstly and then mycqu.access_mycqu")

# from https://github.com/CQULHW/CQUQueryGrade
def get_oauth_token(session: Session) -> str:
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
    access_service(session, MYCQU_SERVICE_URL)
    token = get_oauth_token(session)
    if add_to_header:
        session.headers["Authorization"] = token
    return {"Authorization": token}
