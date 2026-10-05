from fastapi import APIRouter, Depends
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.schemas.user import UserResponse 

router  = APIRouter(prefix="/user", tags=["用户信息接口"])#生成接口文档

@router.get("/info", summary="获取当前登录用户信息  ")
def get_current_user_info(current_user: User = Depends(get_current_user)):# 依赖注入，校验Token，获取当前登录用户信息
    """获取当前登录用户信息"""
    return {
        "code": 200,
        "message": "获取用户信息成功",
        "data": UserResponse.model_validate(current_user)
    }