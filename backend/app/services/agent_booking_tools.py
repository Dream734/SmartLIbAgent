"""AI 可写的预约工具：座位预约、图书预借。

安全设计：
1. 一律两阶段：prepare_* 只创建 agent_actions 待确认动作，不写业务表；
   confirm_* 才调用现有 service 真正写 seat_reservations / borrow_records。
2. user_id 只从 RunnableConfig 读取，工具签名不暴露用户身份。
3. confirm_* 会检查最近一轮对话：必须先是助手给出预约摘要，再由用户明确回复
   确认词，避免模型在用户没确认时直接写库。
4. 只开放“提交预约/预借”和“取消待确认动作”，不开放审批、取消已提交记录。
"""

import json
import logging
from contextlib import contextmanager
from datetime import date as date_cls
from datetime import datetime
from typing import Annotated, Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from pydantic import Field
from sqlalchemy import and_, or_

from app.common.exceptions import BusinessException
from app.database import SessionLocal
from app.models.book import Book, BorrowRecord
from app.models.seat import Seat, SeatArea, SeatReservation
from app.models.user import User
from app.schemas.book import BorrowCreateRequest
from app.schemas.seat import SeatReservationCreateRequest
from app.services import agent_action_service, book_service, seat_service

logger = logging.getLogger(__name__)

BORROW_STATUS_TEXT = {
    "pending": "待审批",
    "reserved": "预借中",
    "pickup": "可取书",
    "borrowed": "已借出",
    "returned": "已归还",
    "cancelled": "已取消",
}

SEAT_STATUS_TEXT = {
    "pending": "待审批",
    "reserved": "已预约",
    "cancelled": "已取消",
    "finished": "已离座",
}

CONFIRM_KEYWORDS = (
    "确认",
    "确定",
    "提交",
    "可以",
    "是的",
    "好的",
    "行",
    "约吧",
    "预约吧",
    "ok",
    "yes",
    "嗯",
)
NEGATIVE_KEYWORDS = ("不", "别", "取消", "算了", "不要", "不用")
ASSISTANT_CONFIRM_HINTS = ("确认", "提交", "预约", "预借")
CANCEL_KEYWORDS = (
    "取消",
    "算了",
    "不约",
    "不借",
    "不预约",
    "不要",
    "不用",
    "换一个",
    "改约",
    "换座位",
    "换书",
    "换",
)


@contextmanager
def _db_session():
    """写工具专用数据库会话：异常回滚，结束一定关闭。"""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _error(message: str) -> str:
    return _json({"ok": False, "error": message})


def _user_id_from_config(config: RunnableConfig | None) -> int | None:
    configurable = (config or {}).get("configurable") or {}
    user_id = configurable.get("user_id")
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return None


def _get_user(db, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text") or block.get("content")
                if text:
                    parts.append(str(text))
        return "\n".join(parts).strip()
    return str(content).strip() if content is not None else ""


def _last_human_message(runtime: ToolRuntime) -> tuple[int, HumanMessage] | None:
    messages = (runtime.state or {}).get("messages") or []
    for index in range(len(messages) - 1, -1, -1):
        if isinstance(messages[index], HumanMessage):
            return index, messages[index]
    return None


def _is_user_confirmation(runtime: ToolRuntime, action_type: str) -> bool:
    """确认必须发生在“助手展示摘要”之后，而不是同一轮里模型自作主张。"""
    found = _last_human_message(runtime)
    if not found:
        return False

    human_index, human_message = found
    if human_index == 0:
        return False

    messages = (runtime.state or {}).get("messages") or []
    previous = messages[human_index - 1]
    if not isinstance(previous, AIMessage):
        return False

    previous_text = _content_to_text(previous.content)
    if not any(word in previous_text for word in ASSISTANT_CONFIRM_HINTS):
        return False

    if action_type == "seat_reservation" and not any(
        word in previous_text for word in ("座位", "阅览区")
    ):
        return False
    if action_type == "book_borrow" and not any(
        word in previous_text for word in ("图书", "预借", "《", "书")
    ):
        return False

    user_text = _content_to_text(human_message.content).lower()
    if any(word in user_text for word in NEGATIVE_KEYWORDS):
        return False
    return any(word in user_text for word in CONFIRM_KEYWORDS)


def _is_user_cancellation(runtime: ToolRuntime) -> bool:
    found = _last_human_message(runtime)
    if not found:
        return False
    _, human_message = found
    text = _content_to_text(human_message.content).lower()
    return any(word in text for word in CANCEL_KEYWORDS)


def _fmt_datetime(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%d %H:%M") if value else None


def _book_keyword_filter(keyword: str):
    """把“Python 编程”拆成多个关键词做 AND，避免空格导致匹配不到。"""
    filters = []
    for token in (keyword or "").split():
        pattern = f"%{token}%"
        filters.append(
            or_(
                Book.title.ilike(pattern),
                Book.author.ilike(pattern),
                Book.isbn.ilike(pattern),
            )
        )
    return and_(*filters) if filters else None


@tool
def prepare_seat_reservation(
    date: Annotated[str, Field(description="预约日期，格式 YYYY-MM-DD")],
    start_time: Annotated[str, Field(description="开始时间 HH:MM，整点或半点")],
    end_time: Annotated[str, Field(description="结束时间 HH:MM，整点或半点")],
    config: RunnableConfig,
    seat_id: Annotated[
        int | None,
        Field(description="座位ID；不传则根据 area_id 自动选择一个可用座位"),
    ] = None,
    area_id: Annotated[
        int | None,
        Field(description="阅览区ID；不传 seat_id 时必须提供，可先调用 list_areas"),
    ] = None,
) -> str:
    """校验座位预约并创建待确认动作，不写预约表。

    可以只传 area_id + 日期/时间，工具会自动选择一个可用座位；也可以传具体 seat_id。
    只做预校验并返回预约摘要。必须把摘要展示给用户，等用户明确确认后
    再调用 confirm_seat_reservation，不能直接说预约成功。
    """
    user_id = _user_id_from_config(config)
    if user_id is None:
        return _error("未获取到当前登录用户，请重新登录后再试。")

    if seat_id is None and area_id is None:
        return _error("请提供 seat_id 或 area_id；不知道 area_id 时先调用 list_areas。")

    try:
        reservation_date = date_cls.fromisoformat((date or "").strip())
    except ValueError:
        return _error("日期格式应为 YYYY-MM-DD，例如 2026-10-19")

    try:
        with _db_session() as db:
            user = _get_user(db, user_id)
            if not user:
                return _error("当前用户不存在，请重新登录后再试。")

            # 系统惰性过期清理，不会创建新的预约
            seat_service._expire_overdue_reservations(db)

            auto_selected = False
            if seat_id is None:
                available_seats = seat_service.get_seat_list(
                    db,
                    area_id=area_id,
                    date=reservation_date,
                    start_time=start_time,
                    end_time=end_time,
                )
                if not available_seats:
                    return _error(
                        "该区域在所选时段没有可用座位，请换一个时段或区域。"
                    )
                seat_id = available_seats[0].id
                auto_selected = True

            data = SeatReservationCreateRequest(
                seat_id=seat_id,
                date=date,
                start_time=start_time,
                end_time=end_time,
            )
            seat, area = seat_service.check_reservation(db, user, data)

            prefix = "已为你自动选择 " if auto_selected else ""
            summary = (
                f"{prefix}{area.name}（{area.floor}楼）{seat.seat_no}号座位，"
                f"{data.date.isoformat()} {data.start_time}-{data.end_time}"
            )
            action = agent_action_service.create_pending_action(
                db,
                user_id=user_id,
                action_type="seat_reservation",
                payload={
                    "seat_id": data.seat_id,
                    "date": data.date.isoformat(),
                    "start_time": data.start_time,
                    "end_time": data.end_time,
                },
                summary=summary,
            )
            return _json(
                {
                    "ok": True,
                    "action_type": "seat_reservation",
                    "action_id": action.id,
                    "summary": summary,
                    "auto_selected": auto_selected,
                    "requires_confirmation": True,
                    "expire_minutes": agent_action_service.ACTION_TTL_MINUTES,
                    "message": (
                        "请把 summary 展示给用户，并询问是否确认提交；"
                        "用户明确确认后再调用 confirm_seat_reservation。"
                    ),
                }
            )
    except BusinessException as exc:
        return _error(exc.message)
    except ValueError as exc:
        return _error(f"预约参数不正确：{exc}")
    except Exception:
        logger.exception("prepare_seat_reservation 失败")
        return _error("座位预约预校验失败，请稍后重试。")


@tool
def confirm_seat_reservation(runtime: ToolRuntime) -> str:
    """用户明确确认后，真正提交座位预约申请。

    会再次校验座位/时段/冲突，校验通过后写入 seat_reservations。
    没有待确认动作、用户未确认或校验失败时返回错误，不会写库。
    """
    if not _is_user_confirmation(runtime, "seat_reservation"):
        return _error(
            "还没有收到用户明确确认。请先把预约摘要展示给用户，"
            "等用户回复“确认/提交/可以”后再调用本工具。"
        )

    user_id = _user_id_from_config(runtime.config)
    if user_id is None:
        return _error("未获取到当前登录用户，请重新登录后再试。")

    try:
        with _db_session() as db:
            user = _get_user(db, user_id)
            if not user:
                return _error("当前用户不存在，请重新登录后再试。")

            action = agent_action_service.get_pending_action(
                db, user_id, "seat_reservation"
            )
            if not action:
                return _error("没有待确认的座位预约，请先调用 prepare_seat_reservation。")

            action_id = action.id
            try:
                payload = json.loads(action.payload)
            except (TypeError, ValueError):
                agent_action_service.mark_failed(db, action_id, "待确认动作数据损坏")
                return _error("待确认的预约数据异常，请重新选择座位。")

            if not agent_action_service.claim_action(db, action_id):
                return _error("该预约正在处理或已提交，请勿重复确认。")

            try:
                data = SeatReservationCreateRequest(**payload)
                reservation = seat_service.create_reservation(db, user, data)
            except BusinessException as exc:
                db.rollback()
                agent_action_service.mark_failed(db, action_id, exc.message)
                return _error(exc.message)
            except Exception:
                logger.exception("confirm_seat_reservation 写库失败")
                db.rollback()
                agent_action_service.mark_failed(db, action_id, "座位预约提交失败")
                return _error("座位预约提交失败，请稍后重试。")

            result = {
                "reservation_id": reservation.id,
                "status": reservation.status,
                "date": reservation.date.isoformat(),
                "start_time": reservation.start_time,
                "end_time": reservation.end_time,
            }
            try:
                agent_action_service.mark_confirmed(db, action_id, result)
            except Exception:
                # 业务记录已经写入，这里只记录日志，仍然按成功返回
                logger.exception("标记座位预约动作成功失败: action_id=%s", action_id)

            return _json(
                {
                    "ok": True,
                    **result,
                    "message": "座位预约申请已提交，等待管理员审批。",
                }
            )
    except Exception:
        logger.exception("confirm_seat_reservation 失败")
        return _error("座位预约提交失败，请稍后重试。")


@tool
def prepare_book_borrow(
    config: RunnableConfig,
    book_id: Annotated[
        int | None, Field(description="图书ID；已知图书ID时可直接传")
    ] = None,
    title: Annotated[
        str | None,
        Field(description="书名/作者/ISBN 关键词；用户只说了书名时直接传这个，工具会自动查找"),
    ] = None,
) -> str:
    """校验图书预借并创建待确认动作，不扣库存、不写借阅表。

    图书预借没有日期/时段参数。用户说书名时直接传 title，不要先问日期，
    也不要只调用 search_books 后停下；工具会自动查找并选择一本可预借图书。
    只做预校验并返回摘要。必须把摘要展示给用户，等用户明确确认后
    再调用 confirm_book_borrow，不能直接说预借成功。
    """
    user_id = _user_id_from_config(config)
    if user_id is None:
        return _error("未获取到当前登录用户，请重新登录后再试。")

    if book_id is None and not (title or "").strip():
        return _error("请提供 book_id 或书名 title。")

    try:
        with _db_session() as db:
            user = _get_user(db, user_id)
            if not user:
                return _error("当前用户不存在，请重新登录后再试。")

            # 系统惰性过期清理，不会创建新的借阅记录
            book_service._expire_overdue_borrows(db)

            book = None
            if book_id is not None:
                data = BorrowCreateRequest(book_id=book_id)
                book = book_service.check_borrow(db, user, data)
            else:
                keyword = title.strip()
                candidates_query = db.query(Book).filter(Book.status == 1)
                keyword_filter = _book_keyword_filter(keyword)
                if keyword_filter is not None:
                    candidates_query = candidates_query.filter(keyword_filter)
                candidates = (
                    candidates_query.order_by(Book.id.asc()).limit(10).all()
                )
                if not candidates:
                    return _error(f"没有找到与“{keyword}”匹配的在架图书。")

                last_error = None
                for candidate in candidates:
                    try:
                        book = book_service.check_borrow(
                            db, user, BorrowCreateRequest(book_id=candidate.id)
                        )
                        break
                    except BusinessException as exc:
                        last_error = exc.message
                if not book:
                    return _error(
                        last_error or "找到图书，但暂时没有可预借库存。"
                    )

            summary = (
                f"《{book.title}》（{book.author}），"
                f"当前可预借库存 {book.available} 本，预借有效期 2 天"
            )
            action = agent_action_service.create_pending_action(
                db,
                user_id=user_id,
                action_type="book_borrow",
                payload={"book_id": book.id},
                summary=summary,
            )
            return _json(
                {
                    "ok": True,
                    "action_type": "book_borrow",
                    "action_id": action.id,
                    "summary": summary,
                    "requires_confirmation": True,
                    "expire_minutes": agent_action_service.ACTION_TTL_MINUTES,
                    "message": (
                        "请把 summary 展示给用户，并询问是否确认提交；"
                        "用户明确确认后再调用 confirm_book_borrow。"
                    ),
                }
            )
    except BusinessException as exc:
        return _error(exc.message)
    except Exception:
        logger.exception("prepare_book_borrow 失败")
        return _error("图书预借预校验失败，请稍后重试。")


@tool
def confirm_book_borrow(runtime: ToolRuntime) -> str:
    """用户明确确认后，真正提交图书预借申请。

    会再次校验图书状态/库存/是否已预借，校验通过后写入 borrow_records
    并扣减可预借库存。没有待确认动作、用户未确认或校验失败时返回错误。
    """
    if not _is_user_confirmation(runtime, "book_borrow"):
        return _error(
            "还没有收到用户明确确认。请先把预借摘要展示给用户，"
            "等用户回复“确认/提交/可以”后再调用本工具。"
        )

    user_id = _user_id_from_config(runtime.config)
    if user_id is None:
        return _error("未获取到当前登录用户，请重新登录后再试。")

    try:
        with _db_session() as db:
            user = _get_user(db, user_id)
            if not user:
                return _error("当前用户不存在，请重新登录后再试。")

            action = agent_action_service.get_pending_action(
                db, user_id, "book_borrow"
            )
            if not action:
                return _error("没有待确认的图书预借，请先调用 prepare_book_borrow。")

            action_id = action.id
            try:
                payload = json.loads(action.payload)
            except (TypeError, ValueError):
                agent_action_service.mark_failed(db, action_id, "待确认动作数据损坏")
                return _error("待确认的预借数据异常，请重新选择图书。")

            if not agent_action_service.claim_action(db, action_id):
                return _error("该预借正在处理或已提交，请勿重复确认。")

            try:
                data = BorrowCreateRequest(**payload)
                record = book_service.create_borrow(db, user, data)
            except BusinessException as exc:
                db.rollback()
                agent_action_service.mark_failed(db, action_id, exc.message)
                return _error(exc.message)
            except Exception:
                logger.exception("confirm_book_borrow 写库失败")
                db.rollback()
                agent_action_service.mark_failed(db, action_id, "图书预借提交失败")
                return _error("图书预借提交失败，请稍后重试。")

            result = {
                "borrow_id": record.id,
                "status": record.status,
                "expire_time": _fmt_datetime(record.expire_time),
            }
            try:
                agent_action_service.mark_confirmed(db, action_id, result)
            except Exception:
                logger.exception("标记图书预借动作成功失败: action_id=%s", action_id)

            return _json(
                {
                    "ok": True,
                    **result,
                    "message": "图书预借申请已提交，库存已为你保留，等待管理员审批。",
                }
            )
    except Exception:
        logger.exception("confirm_book_borrow 失败")
        return _error("图书预借提交失败，请稍后重试。")


@tool
def cancel_pending_action(
    action_type: Annotated[
        str,
        Field(description="要取消的动作类型：seat_reservation 或 book_borrow"),
    ],
    runtime: ToolRuntime,
) -> str:
    """取消尚未确认的预约/预借动作。

    用户反悔、改约、换座位/换书时调用。只影响 agent_actions 中的待确认动作，
    不会取消已经提交的预约或借阅记录。
    """
    if action_type not in ("seat_reservation", "book_borrow"):
        return _error("action_type 只能是 seat_reservation 或 book_borrow。")
    if not _is_user_cancellation(runtime):
        return _error("还没有收到用户取消或改约的明确意思。")

    user_id = _user_id_from_config(runtime.config)
    if user_id is None:
        return _error("未获取到当前登录用户，请重新登录后再试。")

    try:
        with _db_session() as db:
            action = agent_action_service.cancel_pending_action(
                db, user_id, action_type
            )
            if not action:
                return _error("没有待确认的动作可以取消。")
            return _json(
                {
                    "ok": True,
                    "action_type": action_type,
                    "message": "已取消待确认的动作，没有影响任何已提交的预约。",
                }
            )
    except Exception:
        logger.exception("cancel_pending_action 失败")
        return _error("取消待确认动作失败，请稍后重试。")


@tool
def cancel_my_book_borrow(
    runtime: ToolRuntime,
    borrow_id: Annotated[
        int | None, Field(description="借阅记录ID；已知记录ID时可直接传")
    ] = None,
    title: Annotated[
        str | None,
        Field(description="书名/作者/ISBN 关键词；用户只说了书名时传这个"),
    ] = None,
) -> str:
    """取消当前用户已经提交的图书预借（pending / reserved），并释放库存。

    只能取消自己的记录。用户说“取消《某本书》的预借”时，直接传 title，
    不要先 search_books。已经取消的记录会返回“已取消”，不会重复释放库存。
    如果要取消的是还没确认的 prepare 动作，请改用 cancel_pending_action。
    """
    if not _is_user_cancellation(runtime):
        return _error("还没有收到用户取消的明确意思。")

    user_id = _user_id_from_config(runtime.config)
    if user_id is None:
        return _error("未获取到当前登录用户，请重新登录后再试。")

    try:
        with _db_session() as db:
            user = _get_user(db, user_id)
            if not user:
                return _error("当前用户不存在，请重新登录后再试。")

            if borrow_id is not None:
                record = (
                    db.query(BorrowRecord)
                    .filter(
                        BorrowRecord.id == borrow_id,
                        BorrowRecord.user_id == user_id,
                    )
                    .first()
                )
                if not record:
                    return _error(
                        "没有找到这条预借记录，请刷新“我的图书预借”后再试。"
                    )
                book = db.query(Book).filter(Book.id == record.book_id).first()
                book_title = book.title if book else "该图书"
                if record.status == "cancelled":
                    return _json(
                        {
                            "ok": True,
                            "borrow_id": record.id,
                            "book_title": book_title,
                            "status": "cancelled",
                            "message": f"《{book_title}》的预借已经取消，无需重复操作。",
                        }
                    )
                if record.status not in ("pending", "reserved", "pickup"):
                    status_text = BORROW_STATUS_TEXT.get(record.status, record.status)
                    return _error(
                        f"《{book_title}》当前状态为“{status_text}”，不能取消。"
                    )
                target_id = record.id
            else:
                query = (
                    db.query(BorrowRecord, Book.title)
                    .join(Book, BorrowRecord.book_id == Book.id)
                    .filter(
                        BorrowRecord.user_id == user_id,
                        BorrowRecord.status.in_(("pending", "reserved", "pickup")),
                    )
                )
                keyword = (title or "").strip()
                if keyword:
                    keyword_filter = _book_keyword_filter(keyword)
                    if keyword_filter is not None:
                        query = query.filter(keyword_filter)
                rows = query.order_by(BorrowRecord.id.desc()).limit(5).all()
                if not rows:
                    return _error(
                        "没有找到你当前可以取消的图书预借。"
                        "可能已经取消、已过期，或已进入借阅阶段。"
                    )
                if len(rows) > 1:
                    return _json(
                        {
                            "ok": False,
                            "error": "找到多条可取消的预借，请指定要取消的书名。",
                            "candidates": [
                                {
                                    "borrow_id": record.id,
                                    "book_title": book_title,
                                    "status": record.status,
                                    "status_text": BORROW_STATUS_TEXT.get(
                                        record.status, record.status
                                    ),
                                }
                                for record, book_title in rows
                            ],
                        }
                    )
                record, book_title = rows[0]
                target_id = record.id

            try:
                result = book_service.cancel_borrow(db, user, target_id)
            except BusinessException as exc:
                return _error(exc.message)

            return _json(
                {
                    "ok": True,
                    "borrow_id": result.id,
                    "book_title": book_title,
                    "status": result.status,
                    "message": f"已取消《{book_title}》的预借，库存已释放。",
                }
            )
    except Exception:
        logger.exception("cancel_my_book_borrow 失败")
        return _error("取消图书预借失败，请稍后重试。")


@tool
def cancel_my_seat_reservation(
    runtime: ToolRuntime,
    reservation_id: Annotated[
        int | None, Field(description="座位预约记录ID；已知时可直接传")
    ] = None,
    date: Annotated[
        str | None, Field(description="预约日期 YYYY-MM-DD；用于区分多条记录")
    ] = None,
    start_time: Annotated[
        str | None, Field(description="开始时间 HH:MM；用于区分多条记录")
    ] = None,
    seat_no: Annotated[
        str | None, Field(description="座位号；用于区分多条记录")
    ] = None,
) -> str:
    """取消当前用户已经提交的座位预约（pending / reserved），释放该时段座位。

    只能取消自己的记录。用户说“取消我的座位预约”时，不传 reservation_id
    会取消唯一一条可取消记录；有多条时可按 date/start_time/seat_no 过滤，
    仍有多条则返回候选让用户选择。
    已经取消的记录会返回“已取消”，不会重复操作。
    如果要取消的是还没确认的 prepare 动作，请改用 cancel_pending_action。
    """
    if not _is_user_cancellation(runtime):
        return _error("还没有收到用户取消的明确意思。")

    user_id = _user_id_from_config(runtime.config)
    if user_id is None:
        return _error("未获取到当前登录用户，请重新登录后再试。")

    date_value = None
    if date:
        try:
            date_value = date_cls.fromisoformat(date.strip())
        except ValueError:
            return _error("日期格式应为 YYYY-MM-DD，例如 2026-10-19。")
    start_time_value = (start_time or "").strip() or None
    seat_no_value = (seat_no or "").strip() or None

    try:
        with _db_session() as db:
            user = _get_user(db, user_id)
            if not user:
                return _error("当前用户不存在，请重新登录后再试。")

            query = (
                db.query(SeatReservation, Seat.seat_no, SeatArea.name)
                .join(Seat, SeatReservation.seat_id == Seat.id)
                .join(SeatArea, Seat.area_id == SeatArea.id)
                .filter(SeatReservation.user_id == user_id)
            )

            if reservation_id is not None:
                rows = (
                    query.filter(SeatReservation.id == reservation_id)
                    .limit(1)
                    .all()
                )
                if not rows:
                    return _error(
                        "没有找到这条座位预约记录，请刷新“我的预约”后再试。"
                    )
                reservation, seat_no, area_name = rows[0]
                if reservation.status == "cancelled":
                    return _json(
                        {
                            "ok": True,
                            "reservation_id": reservation.id,
                            "status": "cancelled",
                            "message": "该座位预约已经取消，无需重复操作。",
                        }
                    )
                if reservation.status not in ("pending", "reserved"):
                    status_text = SEAT_STATUS_TEXT.get(
                        reservation.status, reservation.status
                    )
                    return _error(
                        f"该座位预约当前状态为“{status_text}”，不能取消。"
                    )
                target = rows[0]
            else:
                if date_value is not None:
                    query = query.filter(SeatReservation.date == date_value)
                if start_time_value:
                    query = query.filter(
                        SeatReservation.start_time == start_time_value
                    )
                if seat_no_value:
                    query = query.filter(
                        Seat.seat_no.ilike(f"%{seat_no_value}%")
                    )

                rows = (
                    query.filter(
                        SeatReservation.status.in_(("pending", "reserved"))
                    )
                    .order_by(
                        SeatReservation.date.desc(),
                        SeatReservation.start_time.desc(),
                    )
                    .limit(5)
                    .all()
                )
                if not rows:
                    return _error(
                        "没有找到符合条件、且当前可以取消的座位预约。"
                        "可能已经取消、已过期，或已经离座。"
                    )
                if len(rows) > 1:
                    return _json(
                        {
                            "ok": False,
                            "error": (
                                "找到多条可取消的座位预约，请回复"
                                "“取消记录 编号”，或指定日期+开始时间。"
                            ),
                            "candidates": [
                                {
                                    "reservation_id": reservation.id,
                                    "date": reservation.date.isoformat(),
                                    "start_time": reservation.start_time,
                                    "end_time": reservation.end_time,
                                    "seat_no": seat_no,
                                    "area_name": area_name,
                                    "status": reservation.status,
                                    "status_text": SEAT_STATUS_TEXT.get(
                                        reservation.status, reservation.status
                                    ),
                                }
                                for reservation, seat_no, area_name in rows
                            ],
                        }
                    )
                target = rows[0]

            reservation, seat_no, area_name = target
            try:
                result = seat_service.cancel_reservation(
                    db, user, reservation.id
                )
            except BusinessException as exc:
                return _error(exc.message)

            return _json(
                {
                    "ok": True,
                    "reservation_id": result.id,
                    "date": result.date.isoformat(),
                    "start_time": result.start_time,
                    "end_time": result.end_time,
                    "seat_no": seat_no,
                    "area_name": area_name,
                    "status": result.status,
                    "message": (
                        f"已取消 {result.date.isoformat()} "
                        f"{result.start_time}-{result.end_time} 的座位预约"
                        f"（{area_name} {seat_no}号）。"
                    ),
                }
            )
    except Exception:
        logger.exception("cancel_my_seat_reservation 失败")
        return _error("取消座位预约失败，请稍后重试。")


BOOKING_TOOLS = [
    prepare_seat_reservation,
    confirm_seat_reservation,
    prepare_book_borrow,
    confirm_book_borrow,
    cancel_pending_action,
    cancel_my_book_borrow,
    cancel_my_seat_reservation,
]
