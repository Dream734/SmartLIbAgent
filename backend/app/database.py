from sqlalchemy.orm import sessionmaker,DeclarativeBase,Mapped,mapped_column
from sqlalchemy import create_engine,DateTime,func
from app.config import settings
from datetime import datetime

"""engine 是「数据库引擎」，相当于到 MySQL 的一条连接通道"""
engine = create_engine(settings.DATABASE_URL)

# 数据库session会话的连接工厂
SessionLocal = sessionmaker(bind=engine, autocommit=False,)

def get_db():
    db = SessionLocal()
    print("===== 会话已打开 =====")
    try:
        yield db
    finally:
        db.close()
        print("===== 会话已关闭 =====")
class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True,comment="主键id")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
