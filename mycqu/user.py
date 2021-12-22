from __future__ import annotations
from ._lib_wrapper.dataclass import dataclass
from .mycqu import MycquUnauthorized
from requests import Session
__all__ = ("User",)


@dataclass
class User:
    """用户信息"""

    name: str
    """姓名"""
    uniform_id: str
    """统一身份认证号"""
    code: str
    """学工号"""
    role: str
    """身份，已知取值有学生 :obj:`"student"`、教师 :obj:`"instructor`"`"""
    email: str
    "电子邮箱"
    phone_number: str
    "电话号码"

    @staticmethod
    def fetch_self(session: Session) -> User:
        resp = session.get("https://my.cqu.edu.cn/authserver/simple-user")
        if resp.status_code == 401:
            raise MycquUnauthorized()
        data = resp.json()
        return User(
            name=data["name"],
            code=data["code"],
            uniform_id=data["username"],
            role=data["type"],
            email=data["email"],
            phone_number=data["phoneNumber"]
        )
