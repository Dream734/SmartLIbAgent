from fastapi import APIRouter, Depends
from app.common.response import Response
from app.schemas.auth import LoginRequest,RegisterRequest
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import auth_service
from app.utils.password import verify_password
from app.utils.jwt import create_access_token


router = APIRouter(prefix="/auth", tags=["权限验证"])#生成接口文档

@router.post("/login", summary="用户登录")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """登录"""
    result =  auth_service.login(db,data)
    # 返回登录成功的响应，信息
    return Response.success(
        message="登录成功",
        data=result,
    )


@router.post("/register", summary="用户注册")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """注册"""
    auth_service.register(db,data)
    # 返回登录成功的响应，信息
    return Response.success(message="注册成功")
