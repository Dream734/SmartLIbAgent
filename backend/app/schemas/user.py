from pydantic import BaseModel, ConfigDict

"""让这个类变成一个 Pydantic 模型，拥有「数据校验」和「序列化」两大能力"""
class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None = None
    name: str
    role: str
    phone: str | None = None
    status: int

    model_config = ConfigDict(from_attributes=True)#对象转化JSON时，使用对象的属性值，而不是字典的键值对
# 让 Pydantic 能从 ORM 对象（User 实例）直接读属性。
