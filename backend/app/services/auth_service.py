from cmath import phase
from os import name
from sys import stdout
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import LoginRequest, RegisterRequest
from app.models.user import User
from app.schemas.user import UserResponse
from app.schemas.auth import LoginResponse
from app.utils import password
from app.utils.password import hash_password, verify_password
from app.utils.jwt import create_access_token
from app.common.exceptions import BusinessException


def login(db: Session, data :LoginRequest   ):
    # 验证用户名和密码是否正确
    user = db.query(User).filter(User.username == data.username).first()

    # 判断账号密码是否正确
    if not user or not verify_password(data.password, user.password):
        raise BusinessException(code=400, message="用户名或密码错误")
    # 判断账号的状态
    if user.status == 0:
        raise BusinessException(code=400, message="账号已被禁用")
    # 创建token
    token = create_access_token(user.id)
    return LoginResponse(token=token, user=UserResponse.model_validate(user))


def register(db: Session, data: RegisterRequest):
    # 验证用户名和密码是否正确
    user = db.query(User).filter(User.username == data.username).first()
    if user:
        raise BusinessException(message="账号已存在")
    user_model = User(
        username=data.username,
        password=hash_password(data.password),
        name=data.name or data.username,
        role="student",
        phone="",
        status=1,
    )

    db.add(user_model)
    db.commit()
    db.flush
