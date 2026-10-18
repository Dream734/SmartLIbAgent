from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SeatArea(Base):
    """阅览区/楼层"""
    __tablename__ = "seat_areas"
    __table_args__ = {"comment": "阅览区表"}

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="区域名称")
    floor: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="楼层")
    open_time: Mapped[str] = mapped_column(String(5), nullable=False, default="08:00", comment="开放时间 HH:MM")
    close_time: Mapped[str] = mapped_column(String(5), nullable=False, default="22:00", comment="关闭时间 HH:MM")
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="状态: 1启用 0停用")


class Seat(Base):
    """座位"""
    __tablename__ = "seats"
    __table_args__ = {"comment": "座位表"}

    area_id: Mapped[int] = mapped_column(ForeignKey("seat_areas.id"), nullable=False, comment="所属阅览区id")
    seat_no: Mapped[str] = mapped_column(String(50), nullable=False, comment="座位号")
    seat_type: Mapped[str] = mapped_column(String(50), nullable=False, default="普通", comment="座位类型")
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="状态: 1启用 0停用")


class SeatReservation(Base):
    """座位预约"""
    __tablename__ = "seat_reservations"
    __table_args__ = {"comment": "座位预约表"}

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, comment="用户id")
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"), nullable=False, comment="座位id")
    date: Mapped[date] = mapped_column(Date, nullable=False, comment="预约日期")
    start_time: Mapped[str] = mapped_column(String(5), nullable=False, comment="开始时间 HH:MM")
    end_time: Mapped[str] = mapped_column(String(5), nullable=False, comment="结束时间 HH:MM")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", comment="状态: pending待审批/reserved已预约/cancelled已取消/finished已离座")
