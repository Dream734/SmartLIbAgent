"""供 LLM 调用的只读业务查询工具。

设计约束：
1. 每个工具自己创建 / 关闭数据库会话，不复用 FastAPI 请求的 Session；
2. “我的预约 / 我的预借”从 LangGraph 的 RunnableConfig 读取 user_id，
   工具签名里不暴露用户身份参数，避免 LLM 猜测或越权查询；
3. 只封装查询，不封装预约、取消、审批、借还等写操作；
4. 统一返回 JSON 字符串，不把 SQLAlchemy 对象直接交给 LLM。
"""

import json
import logging
import re
from contextlib import contextmanager
from datetime import date as date_cls
from datetime import datetime, time
from typing import Annotated, Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import Field
from sqlalchemy import and_, func, or_

from app.database import SessionLocal
from app.models.book import Book, BookCategory, BorrowRecord
from app.models.seat import Seat, SeatArea, SeatReservation
from app.services import kb_service

logger = logging.getLogger(__name__)

ACTIVE_SEAT_STATUSES = ("pending", "reserved")
ACTIVE_BORROW_STATUSES = ("pending", "reserved", "pickup", "borrowed")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):(00|30)$")
MAX_DURATION_MINUTES = 4 * 60
MAX_LIST_ITEMS = 50
MAX_HISTORY_ITEMS = 20

SEAT_STATUS_TEXT = {
    "pending": "待审批",
    "reserved": "已预约",
    "cancelled": "已取消",
    "finished": "已离座",
}

BORROW_STATUS_TEXT = {
    "pending": "待审批",
    "reserved": "预借中",
    "pickup": "可取书",
    "borrowed": "已借出",
    "returned": "已归还",
    "cancelled": "已取消",
}


@contextmanager
def _db_session():
    """工具专用数据库会话：用前创建，用完一定关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _error(message: str) -> str:
    return _json({"ok": False, "error": message})


def _user_id_from_config(config: RunnableConfig) -> int | None:
    """从 LangGraph 运行时配置中取当前登录用户，禁止 LLM 自己传 user_id。"""
    configurable = (config or {}).get("configurable") or {}
    user_id = configurable.get("user_id")
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return None


def _parse_day(value: str) -> date_cls:
    try:
        return date_cls.fromisoformat((value or "").strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("日期格式应为 YYYY-MM-DD，例如 2026-10-20") from exc


def _to_minutes(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def _validate_time_slot(start_time: str, end_time: str) -> None:
    if not TIME_RE.match(start_time) or not TIME_RE.match(end_time):
        raise ValueError("时间只能是整点或半点，格式 HH:MM，例如 09:00、10:30")
    if _to_minutes(start_time) >= _to_minutes(end_time):
        raise ValueError("结束时间必须晚于开始时间")
    if _to_minutes(end_time) - _to_minutes(start_time) > MAX_DURATION_MINUTES:
        raise ValueError("单次查询/预约的时段最长不超过 4 小时")


def _fmt_datetime(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%d %H:%M") if value else None


@tool
def list_areas() -> str:
    """查询所有启用的阅览区，返回区域ID、名称、楼层、开放时间和座位数。

    当用户询问“有哪些阅览区 / 在几楼 / 几点开放”，或需要 area_id 时调用。
    """
    try:
        with _db_session() as db:
            rows = (
                db.query(SeatArea, func.count(Seat.id))
                .outerjoin(Seat, and_(Seat.area_id == SeatArea.id, Seat.status == 1))
                .filter(SeatArea.status == 1)
                .group_by(SeatArea.id)
                .order_by(SeatArea.floor.asc(), SeatArea.id.asc())
                .all()
            )
            items = [
                {
                    "area_id": area.id,
                    "name": area.name,
                    "floor": area.floor,
                    "open_time": area.open_time,
                    "close_time": area.close_time,
                    "seat_count": int(seat_count or 0),
                }
                for area, seat_count in rows
            ]
            return _json({"ok": True, "total": len(items), "areas": items})
    except Exception:
        logger.exception("list_areas 查询失败")
        return _error("查询阅览区失败，请稍后重试。")


@tool
def query_available_seats(
    area_id: Annotated[int, Field(description="阅览区ID，可先调用 list_areas 查询")],
    date: Annotated[str, Field(description="预约日期，格式 YYYY-MM-DD")],
    start_time: Annotated[str, Field(description="开始时间，格式 HH:MM，必须是整点或半点")],
    end_time: Annotated[str, Field(description="结束时间，格式 HH:MM，必须是整点或半点")],
) -> str:
    """查询指定阅览区在某天某时段内仍然可预约的座位。

    用户问“明天下午 2 点到 4 点还有没有座位 / 某个区域哪些座位空着”时调用。
    返回座位ID、座位号、座位类型和所在区域。
    """
    try:
        day = _parse_day(date)
        start_time = (start_time or "").strip()
        end_time = (end_time or "").strip()
        _validate_time_slot(start_time, end_time)

        if day < date_cls.today():
            return _error("不能查询过去的日期，请确认日期是否正确。")

        with _db_session() as db:
            area = (
                db.query(SeatArea)
                .filter(SeatArea.id == area_id, SeatArea.status == 1)
                .first()
            )
            if not area:
                return _error(
                    f"阅览区 {area_id} 不存在或已停用，请先调用 list_areas 查看可用区域。"
                )

            if start_time < area.open_time or end_time > area.close_time:
                return _error(
                    f"所选时段 {start_time}-{end_time} 不在该区域开放时间 "
                    f"{area.open_time}-{area.close_time} 内。"
                )

            booked_ids = [
                row[0]
                for row in db.query(SeatReservation.seat_id)
                .filter(
                    SeatReservation.date == day,
                    SeatReservation.status.in_(ACTIVE_SEAT_STATUSES),
                    SeatReservation.start_time < end_time,
                    SeatReservation.end_time > start_time,
                )
                .all()
            ]

            query = db.query(Seat).filter(Seat.area_id == area_id, Seat.status == 1)
            if booked_ids:
                query = query.filter(Seat.id.notin_(booked_ids))

            seats = query.order_by(Seat.seat_no.asc()).all()
            available_count = len(seats)
            items = [
                {
                    "seat_id": seat.id,
                    "seat_no": seat.seat_no,
                    "seat_type": seat.seat_type,
                    "area_name": area.name,
                    "floor": area.floor,
                }
                for seat in seats[:MAX_LIST_ITEMS]
            ]

            payload = {
                "ok": True,
                "area": {"area_id": area.id, "name": area.name, "floor": area.floor},
                "date": day.isoformat(),
                "start_time": start_time,
                "end_time": end_time,
                "available_count": available_count,
                "returned": len(items),
                "seats": items,
            }
            if available_count == 0:
                payload["note"] = "该区域在所选时段没有可预约的座位。"
            elif available_count > MAX_LIST_ITEMS:
                payload["note"] = (
                    f"可用座位较多，仅返回前 {MAX_LIST_ITEMS} 个，"
                    f"共 {available_count} 个。"
                )
            return _json(payload)
    except ValueError as exc:
        return _error(str(exc))
    except Exception:
        logger.exception("query_available_seats 查询失败")
        return _error("查询可用座位失败，请稍后重试。")


@tool
def query_my_seat_reservations(config: RunnableConfig) -> str:
    """查询当前登录用户最近的座位预约记录（最多 20 条）。

    用户问“我预约了哪些座位 / 我的座位预约到几点 / 有没有待审批的预约”时调用。
    用户身份由系统注入，不要让用户提供 user_id。
    """
    user_id = _user_id_from_config(config)
    if user_id is None:
        return _error("未获取到当前登录用户，请重新登录后再试。")

    try:
        with _db_session() as db:
            rows = (
                db.query(SeatReservation, Seat.seat_no, SeatArea.name)
                .join(Seat, SeatReservation.seat_id == Seat.id)
                .join(SeatArea, Seat.area_id == SeatArea.id)
                .filter(SeatReservation.user_id == user_id)
                .order_by(
                    SeatReservation.date.desc(),
                    SeatReservation.start_time.desc(),
                )
                .limit(MAX_HISTORY_ITEMS)
                .all()
            )

            now = datetime.now()
            items = []
            for reservation, seat_no, area_name in rows:
                status_text = SEAT_STATUS_TEXT.get(
                    reservation.status, reservation.status
                )
                is_active = reservation.status in ACTIVE_SEAT_STATUSES
                if reservation.status == "pending":
                    try:
                        start_at = datetime.combine(
                            reservation.date, time.fromisoformat(reservation.start_time)
                        )
                        if start_at < now:
                            status_text = "已超时（系统将自动取消）"
                            is_active = False
                    except ValueError:
                        pass
                items.append(
                    {
                        "reservation_id": reservation.id,
                        "date": reservation.date.isoformat(),
                        "start_time": reservation.start_time,
                        "end_time": reservation.end_time,
                        "area_name": area_name,
                        "seat_no": seat_no,
                        "status": reservation.status,
                        "status_text": status_text,
                        "is_active": is_active,
                        "create_time": _fmt_datetime(reservation.create_time),
                    }
                )

            return _json(
                {
                    "ok": True,
                    "today": date_cls.today().isoformat(),
                    "total": len(items),
                    "reservations": items,
                    "note": (
                        "pending 且开始时间已过的记录会显示为“已超时”，"
                        "系统会在下次座位业务操作时自动取消。"
                    ),
                }
            )
    except Exception:
        logger.exception("query_my_seat_reservations 查询失败")
        return _error("查询我的座位预约失败，请稍后重试。")


@tool
def list_book_categories() -> str:
    """查询所有图书分类，返回分类ID和名称。

    当用户按分类找书，或需要确定 category_id 时调用。
    """
    try:
        with _db_session() as db:
            categories = db.query(BookCategory).order_by(BookCategory.id.asc()).all()
            items = [{"category_id": item.id, "name": item.name} for item in categories]
            return _json({"ok": True, "total": len(items), "categories": items})
    except Exception:
        logger.exception("list_book_categories 查询失败")
        return _error("查询图书分类失败，请稍后重试。")


@tool
def search_books(
    keywords: Annotated[
        str | None,
        Field(description="书名、作者或 ISBN 的模糊关键词；没有可传空字符串或 null"),
    ] = None,
    category_id: Annotated[
        int | None,
        Field(description="图书分类ID，可先调用 list_book_categories 查询"),
    ] = None,
) -> str:
    """按关键词和/或分类查询在架图书，返回图书ID、书名、作者、ISBN、分类和可预借库存。

    用户问“有没有某本书 / 某作者的书 / 某分类下有哪些书”时调用。
    """
    keywords = (keywords or "").strip()
    if not keywords and not category_id:
        return _error(
            "请至少提供书名/作者/ISBN 关键词或分类ID；"
            "可先调用 list_book_categories 查看分类。"
        )

    try:
        with _db_session() as db:
            query = (
                db.query(Book, BookCategory.name)
                .outerjoin(BookCategory, Book.category_id == BookCategory.id)
                .filter(Book.status == 1)
            )
            if category_id:
                query = query.filter(Book.category_id == category_id)
            if keywords:
                # 允许多个关键词用空格分隔，例如“Python 编程”也能匹配“Python编程”
                keyword_filters = []
                for token in keywords.split():
                    pattern = f"%{token}%"
                    keyword_filters.append(
                        or_(
                            Book.title.ilike(pattern),
                            Book.author.ilike(pattern),
                            Book.isbn.ilike(pattern),
                        )
                    )
                query = query.filter(and_(*keyword_filters))

            total = query.count()
            rows = query.order_by(Book.id.desc()).limit(MAX_LIST_ITEMS).all()
            items = [
                {
                    "book_id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "isbn": book.isbn,
                    "category_id": book.category_id,
                    "category_name": category_name,
                    "publisher": book.publisher,
                    "publish_year": book.publish_year,
                    "available": book.available,
                    "total": book.total,
                    "location": book.location,
                }
                for book, category_name in rows
            ]

            payload = {
                "ok": True,
                "total": total,
                "returned": len(items),
                "books": items,
            }
            if not items:
                payload["note"] = "没有找到符合条件的在架图书。"
            elif total > MAX_LIST_ITEMS:
                payload["note"] = (
                    f"结果较多，仅返回前 {MAX_LIST_ITEMS} 条，共 {total} 条。"
                )
            return _json(payload)
    except Exception:
        logger.exception("search_books 查询失败")
        return _error("查询图书失败，请稍后重试。")


@tool
def get_book_detail(
    book_id: Annotated[int, Field(description="图书ID，可从 search_books 结果中获取")],
) -> str:
    """查询指定图书的详细信息：作者、出版社、ISBN、分类、馆藏位置、总册数、可预借库存、上架状态和简介。

    用户问“这本书还有几本 / 在哪个位置 / 能不能借 / 内容简介”时调用。
    """
    try:
        with _db_session() as db:
            book = db.query(Book).filter(Book.id == book_id).first()
            if not book:
                return _error(f"图书 {book_id} 不存在，请确认 book_id 是否正确。")

            category_name = None
            if book.category_id:
                category = (
                    db.query(BookCategory)
                    .filter(BookCategory.id == book.category_id)
                    .first()
                )
                category_name = category.name if category else None

            summary = book.summary or ""
            if len(summary) > 500:
                summary = summary[:500] + "..."

            return _json(
                {
                    "ok": True,
                    "book": {
                        "book_id": book.id,
                        "title": book.title,
                        "author": book.author,
                        "isbn": book.isbn,
                        "publisher": book.publisher,
                        "publish_year": book.publish_year,
                        "category_id": book.category_id,
                        "category_name": category_name,
                        "location": book.location,
                        "total": book.total,
                        "available": book.available,
                        "status": book.status,
                        "status_text": "在架" if book.status == 1 else "已下架",
                        "summary": summary,
                        "cover": book.cover,
                    },
                    "note": (
                        "暂无可预借库存。" if book.available <= 0 else "有可预借库存。"
                    ),
                }
            )
    except Exception:
        logger.exception("get_book_detail 查询失败")
        return _error("查询图书详情失败，请稍后重试。")


@tool
def query_my_borrows(config: RunnableConfig) -> str:
    """查询当前登录用户最近的图书预借/借阅记录（最多 20 条）。

    用户问“我预借了哪些书 / 我的借阅记录 / 什么时候到期”时调用。
    用户身份由系统注入，不要让用户提供 user_id。
    """
    user_id = _user_id_from_config(config)
    if user_id is None:
        return _error("未获取到当前登录用户，请重新登录后再试。")

    try:
        with _db_session() as db:
            rows = (
                db.query(BorrowRecord, Book.title)
                .join(Book, BorrowRecord.book_id == Book.id)
                .filter(BorrowRecord.user_id == user_id)
                .order_by(BorrowRecord.create_time.desc())
                .limit(MAX_HISTORY_ITEMS)
                .all()
            )

            now = datetime.now()
            items = []
            for record, book_title in rows:
                status_text = BORROW_STATUS_TEXT.get(record.status, record.status)
                overdue = bool(
                    record.expire_time
                    and record.expire_time < now
                    and record.status in ("pending", "reserved")
                )
                if overdue:
                    status_text = "已超时（系统将自动取消）"
                items.append(
                    {
                        "borrow_id": record.id,
                        "book_id": record.book_id,
                        "book_title": book_title,
                        "status": record.status,
                        "status_text": status_text,
                        "is_active": record.status in ACTIVE_BORROW_STATUSES,
                        "create_time": _fmt_datetime(record.create_time),
                        "expire_time": _fmt_datetime(record.expire_time),
                        "borrow_time": _fmt_datetime(record.borrow_time),
                        "return_time": _fmt_datetime(record.return_time),
                    }
                )

            return _json(
                {
                    "ok": True,
                    "today": date_cls.today().isoformat(),
                    "total": len(items),
                    "borrows": items,
                    "note": "预借超过 expire_time 后，系统会在下次业务操作时自动取消并释放库存。",
                }
            )
    except Exception:
        logger.exception("query_my_borrows 查询失败")
        return _error("查询我的借阅记录失败，请稍后重试。")


@tool
def search_knowledge_base(
    question: Annotated[
        str,
        Field(description="要检索的规则问题，例如：座位预约一次可以约多久？"),
    ],
) -> str:
    """检索图书馆规则知识库（开放时间、座位预约规则、图书预借规则）。

    用户问规则、开放时间、预约限制等“制度类”问题时调用；
    涉及具体座位、图书、个人记录时请改用对应的业务查询工具。
    """
    question = (question or "").strip()
    if not question:
        return _error("检索问题不能为空。")

    try:
        content = kb_service.search(query=question)
    except Exception:
        logger.exception("知识库检索失败")
        return _error("知识库检索失败，请稍后重试。")

    if not content:
        return _json(
            {
                "ok": True,
                "found": False,
                "content": "",
                "note": "知识库中没有找到相关资料，请如实告知用户，不要编造规则。",
            }
        )
    return _json({"ok": True, "found": True, "content": content})


TOOLS = [
    list_areas,
    query_available_seats,
    query_my_seat_reservations,
    list_book_categories,
    search_books,
    get_book_detail,
    query_my_borrows,
    search_knowledge_base,
]
