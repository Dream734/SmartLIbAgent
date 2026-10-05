from pydantic import BaseModel, ConfigDict

class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None = None
    name: str
    role: str
    phone: str | None = None
    status: int


    model_config = ConfigDict(from_attributes=True)#对象转化JSON时，使用对象的属性值，而不是字典的键值对

    