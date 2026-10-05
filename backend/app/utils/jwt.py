from app.config import settings
import jwt
from datetime import datetime, timedelta

def create_access_token(user_id: int) -> str:
    """创建JWT访问令牌"""
    expire = datetime.now() + timedelta(hours=settings.JWT_EXPIRE_HOURS)  # 设置过期时间为当前时间加上过期小时数

    payload ={"user_id": user_id,  "exp": expire}

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """解码JWT访问令牌"""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])