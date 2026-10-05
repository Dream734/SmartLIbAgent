from fastapi import APIRouter, Depends
from app.common.response import Response
from app.schemas.auth import LoginRequest, LoginResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse
from app.utils.password import verify_password
from app.utils.jwt import create_access_token
from app.common.exceptions import BusinessException


router = APIRouter(prefix="/auth", tags=["权限验证"])#生成接口文档

@router.post("/login", summary="用户登录")
def login(data: LoginRequest, db: Session = Depends(get_db)):
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
    # 返回登录成功的响应，信息
    return Response.success(
        message="登录成功",
        data=LoginResponse(token=token, user=UserResponse.model_validate(user)),
    )
