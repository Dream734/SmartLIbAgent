from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentAction(Base):
    """AI 待确认动作。

    prepare 阶段只写这张表，不写真正的预约/借阅表；
    confirm 阶段才由工具调用业务 service 写业务表。
    """

    __tablename__ = "agent_actions"
    __table_args__ = {"comment": "AI待确认操作表"}

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True, comment="用户id"
    )
    action_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="动作类型: seat_reservation/book_borrow",
    )
    payload: Mapped[str] = mapped_column(Text, nullable=False, comment="动作参数JSON")
    summary: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="展示给用户的预约摘要"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="pending/processing/confirmed/failed/expired/cancelled",
    )
    expire_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="确认过期时间"
    )
    result: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="成功后的结果JSON"
    )
