from fastapi import Depends, HTTPException,status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.jwt import decode_access_token
from app.models.user import User
from app.common.exceptions import BusinessException


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme),db: Session = Depends(get_db))-> User:

    """JWT token验证用户身份"""
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="登录失效，请重新登录")
    
#获取用户ID
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="无效的登录凭证")
#查询数据库获取用户信息
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户被禁用")
    return user



def get_current_admin(current_user:User = Depends(get_current_user))-> User:
    """判断JWT token角色是否为admin"""
    if current_user.role != "admin":
        raise BusinessException(code=403, message="无权限访问")
    return current_user
