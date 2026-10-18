from typing import Any
from  pydantic import BaseModel, Field

class Response(BaseModel):
    """统一封装的返回格式"""
    code: int
    message: str
    data:Any = None

    @classmethod
    def success(cls, data: Any = None, message: str = "操作成功"):
        return cls(code=200, message=message, data=data)

    @classmethod
    def error(cls, code: int = 500, message: str = "请求失败"):
        return cls(code=code, message=message)


class PageResponse(BaseModel):
    items: list = Field(default_factory=list)
    total: int = 0
