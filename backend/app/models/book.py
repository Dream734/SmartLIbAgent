from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BookCategory(Base):
    """图书分类"""
    __tablename__ = "book_categories"
    __table_args__ = {"comment": "图书分类表"}

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, comment="分类名称")


class Book(Base):
    """图书"""
    __tablename__ = "books"
    __table_args__ = {"comment": "图书表"}

    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="书名")
    author: Mapped[str] = mapped_column(String(100), nullable=False, comment="作者")
    isbn: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="ISBN")
    publisher: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="出版社")
    publish_year: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="出版年份")
    category_id: Mapped[int | None] = mapped_column(ForeignKey("book_categories.id"), nullable=True, comment="分类id")
    cover: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="封面")
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="总册数")
    available: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="可预借/可借册数")
    location: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="索书号/馆藏位置")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="简介")
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="状态: 1上架 0下架")


class BorrowRecord(Base):
    """图书预借/借阅记录（create_time 即预借时间）"""
    __tablename__ = "borrow_records"
    __table_args__ = {"comment": "图书预借/借阅表"}

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, comment="用户id")
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False, comment="图书id")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", comment="状态: pending待审批/reserved预借中/pickup可取/borrowed已借/returned已还/cancelled已取消")
    expire_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="预借过期时间")
    borrow_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="借出时间")
    return_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="归还时间")
