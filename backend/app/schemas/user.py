from pydantic import BaseModel, ConfigDict

"""让这个类变成一个 Pydantic 模型，拥有「数据校验」和「序列化」两大能力"""
class UserResponse(BaseModel):
    """用户个人信息的请求参数"""
    id: int
    username: str
    name: str
    role: str
    status: int
    phone: str | None = None
    email: str | None = None
    avatar: str | None = None

    model_config = ConfigDict(from_attributes=True)#对象转化JSON时，使用对象的属性值，而不是字典的键值对
                                                   # 让 Pydantic 能从 ORM 对象（User 实例）直接读属性。



class UserCreateRequest(BaseModel):
    username: str
    password: str = "123"
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None
    role: str = "student"
    status: int = 1

class UserUpdateRequest(BaseModel):
    """更新用户个人信息的请求参数"""
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None
    role: str | None = None
    status: int | None = None


class PassWordUpdateRequest(BaseModel):
    """修改密码的请求参数"""
    old_password: str
    new_password: str
