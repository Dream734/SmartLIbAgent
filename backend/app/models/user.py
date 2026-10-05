from app.database import Base
from sqlalchemy .orm import Mapped,mapped_column
from sqlalchemy import String

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"comment": "用户表"}

    username: Mapped[str] = mapped_column(String(100), nullable=False, comment="账号")
    password: Mapped[str] = mapped_column(String(100), nullable=False, comment="密码")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="名称")
    role: Mapped[str] = mapped_column(String(100), nullable=False, comment="角色: admin:管理员, student:学生")
    email: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="邮箱")
    phone: Mapped[str] = mapped_column(String(100), nullable=False, comment="电话")
    avatar: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="头像")
    status: Mapped[int] = mapped_column(default=1, comment="状态: 1:启用, 0:禁用")