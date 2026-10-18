"""基于 LangGraph ReAct Agent 的智能助手。

和原来的 ai_service.chat 相比：
- 仍然是“大模型 + RAG”，但 RAG 变成了一个工具；
- 额外挂载了座位、图书、个人预约/借阅等只读查询工具；
- 由模型自己决定要不要查知识库、查哪个业务工具。

用户身份不通过提示词让模型“记住”，而是放进 RunnableConfig，
由对应工具从 config 中读取，避免模型猜测 user_id。
"""

import json
import logging
import re
from datetime import datetime

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolRuntime, create_react_agent

from app.common.exceptions import BusinessException
from app.config import settings
from app.database import SessionLocal
from app.models.user import User
from app.schemas.ai import ChatMessage, ChatRequest
from app.services import agent_action_service, agent_booking_tools, agent_tools

logger = logging.getLogger(__name__)

TOOLS = [*agent_tools.TOOLS, *agent_booking_tools.BOOKING_TOOLS]
MAX_HISTORY_MESSAGES = 20
MAX_AGENT_STEPS = 16

SYSTEM_PROMPT_TEMPLATE = """你是「图书馆选座借阅系统」的智能助手，可以调用工具查询真实的阅览区、座位、图书和个人预约/借阅数据。

工作规则：
1. 用户询问具体业务数据时，必须先调用相应工具查询，严禁编造区域、座位、库存、日期和个人记录。
2. 工具参数必须来自用户明确提供的信息。日期统一用 YYYY-MM-DD，时间用 HH:MM（整点或半点）。缺少必要信息时先简短追问，不要猜测。图书预借不需要日期/时段，不要问日期；座位预约才需要日期和时间。
3. 用户只是查询余量、库存、开放时间（例如“还有座位吗 / 有没有空位 / 库存多少”）时，只调用查询工具并回答结果，不要调用 prepare_*，也不要问“确认提交吗”；只有用户明确表达“预约/预借/提交”意图时才 prepare。
4. 用户明确要预约且没有指定具体座位号时，直接调用 prepare_seat_reservation 并传 area_id，工具会自动选择一个可用座位；不要只列出座位后问“确认提交吗”。
5. 用户预借图书时，直接调用 prepare_book_borrow 并传 title=书名/作者/ISBN；不要追问日期，也不要只调用 search_books 后停下。
6. 涉及“我的预约 / 我的预借”时直接调用工具，用户身份已由系统注入，不要向用户索要 user_id。
7. 你可以代用户提交座位预约和图书预借申请，也可以取消自己已提交的座位预约和图书预借；不能审批，也不能操作别人的记录。
8. 制度类问题（开放时间、预约时长、预借规则）优先调用 search_knowledge_base；查不到就如实说明，不要编造。
9. 与图书馆系统无关的问题，礼貌拒绝。
10. 回答使用简洁中文，可以用 Markdown 列表。

写操作规则（预约/预借）：
1. 必须先调用 prepare_*，把返回的 summary 展示给用户，并问“确认提交吗？”。此时只能说“找到……，确认提交吗？”，绝对不能说“申请已提交/预约成功”。
2. 只有用户明确回复“确认/可以/提交/是的/好的”后，才能调用 confirm_*；用户说确认时，必须调用 confirm_*，不能只回复文字。
3. 只有 confirm 返回 ok=true 且 status=pending 时，才能说“申请已提交，等待管理员审批”；如果失败，重新查询并让用户改选。
4. 用户反悔或改约、但还没有确认提交时，先调用 cancel_pending_action，再重新 prepare。
5. 用户要取消已经提交的图书预借时，调用 cancel_my_book_borrow；用户说书名就传 title，不要先 search_books。
6. 用户要取消已经提交的座位预约时，调用 cancel_my_seat_reservation；用户指定记录编号时传 reservation_id，指定日期/开始时间/座位号时传 date/start_time/seat_no；仍有多条再让用户选择。
7. 不要用 cancel_pending_action 取消已经提交的记录，它只取消还没确认的 prepare 动作。
8. 同一时间只处理一个待确认动作；新的 prepare 会作废同类型的旧动作。

当前待确认动作：
{pending_actions}

如果用户本轮明确确认，调用对应的 confirm_*；如果用户改约/反悔，先调用 cancel_pending_action 再重新 prepare。没有待确认动作时，不要调用 confirm_*。

今天是 {today}（星期{weekday}）。当前用户：{name}（{role_name}）。
"""

WEEKDAY_TEXT = "一二三四五六日"
ROLE_TEXT = {"admin": "管理员", "student": "学生"}


def _pending_actions_text(user_id: int) -> str:
    """把服务端待确认动作注入提示词，弥补前端历史里没有工具消息的问题。"""
    db = SessionLocal()
    try:
        lines = []
        seat_action = agent_action_service.get_pending_action(
            db, user_id, "seat_reservation"
        )
        book_action = agent_action_service.get_pending_action(
            db, user_id, "book_borrow"
        )
        if seat_action:
            lines.append(f"- 座位预约：{seat_action.summary}")
        if book_action:
            lines.append(f"- 图书预借：{book_action.summary}")
        return "\n".join(lines) if lines else "- 当前没有待确认动作。"
    except Exception:
        logger.exception("查询待确认动作失败")
        return "- 当前没有待确认动作。"
    finally:
        db.close()


def _build_system_prompt(user: User) -> str:
    now = datetime.now()
    return SYSTEM_PROMPT_TEMPLATE.format(
        today=now.strftime("%Y-%m-%d"),
        weekday=WEEKDAY_TEXT[now.weekday()],
        name=user.name or user.username,
        role_name=ROLE_TEXT.get(user.role, user.role),
        pending_actions=_pending_actions_text(user.id),
    )


def _build_llm() -> ChatOpenAI:
    if not settings.LLM_API_KEY:
        raise BusinessException(message="未获取到大模型的 API_KEY")

    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=0,
        timeout=120,
        max_retries=1,
    )


def _build_agent(user: User):
    return create_react_agent(
        model=_build_llm(),
        tools=TOOLS,
        prompt=_build_system_prompt(user),
        name="library_agent",
    )


def _to_lc_messages(data: ChatRequest) -> list[BaseMessage]:
    """只接受 user/assistant，忽略前端可能塞进来的 system 消息。"""
    history: list[BaseMessage] = []
    for message in data.messages:
        if message.role not in ("user", "assistant"):
            continue
        content = (message.content or "").strip()
        if not content:
            continue
        if message.role == "user":
            history.append(HumanMessage(content=content))
        else:
            history.append(AIMessage(content=content))

    history = history[-MAX_HISTORY_MESSAGES:]
    while history and isinstance(history[0], AIMessage):
        history.pop(0)

    if not history or not isinstance(history[-1], HumanMessage):
        raise BusinessException(message="请输入您要对话的内容")
    return history


def _content_to_text(content) -> str:
    """兼容部分 OpenAI 兼容服务返回的 content block 列表。"""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text") or block.get("content")
                if text:
                    parts.append(str(text))
        return "\n".join(parts).strip()
    return str(content).strip() if content is not None else ""


def _looks_like_tool_output(text: str) -> bool:
    """识别被模型/Agent 当作回答返回的原始工具结果。"""
    if not text:
        return False
    if "<tool_call>" in text or "</tool_call>" in text:
        return True

    stripped = text.lstrip()
    if stripped.startswith("{") and '"ok"' in stripped:
        return True
    if '"ok"' in text and any(
        marker in text
        for marker in (
            '"books":',
            '"seats":',
            '"areas":',
            '"reservations":',
            '"borrows":',
            '"action_type":',
        )
    ):
        return True
    return False


def _extract_reply(messages: list[BaseMessage]) -> str:
    """只从最后一条 AIMessage 取回答。

    不能把最后一条 ToolMessage 的 content 当回答，否则会把 search_books 等
    工具的原始 JSON 直接暴露到前端。
    """
    if not messages:
        return ""

    final_message = messages[-1]
    if isinstance(final_message, AIMessage):
        return _content_to_text(final_message.content)
    return ""


def _log_tool_calls(messages: list[BaseMessage]) -> None:
    tool_names: list[str] = []
    for message in messages:
        if isinstance(message, AIMessage):
            for call in message.tool_calls or []:
                name = call.get("name")
                if name:
                    tool_names.append(name)
    if tool_names:
        logger.info("Agent 工具调用顺序: %s", " -> ".join(tool_names))


def _friendly_error(exc: Exception) -> str:
    """把底层异常翻译成用户能看懂的提示，避免把密钥/堆栈暴露给前端。"""
    text = str(exc).lower()
    if "does not support tools" in text or (
        "tool" in text and "support" in text
    ):
        return (
            f"当前模型 {settings.LLM_MODEL} 不支持工具调用（Function Calling）。"
            "请把 backend/.env 中的 LLM_MODEL 换成 qwen2.5:7b 等支持工具调用的模型后重试。"
        )
    if "connection" in text or "connect" in text or "refused" in text:
        return "无法连接到大模型服务，请确认 Ollama 或 LLM 服务已经启动。"
    return "AI 助手暂时不可用，请稍后重试。"


CONFIRM_WORDS = (
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
NEGATIVE_WORDS = ("不", "别", "取消", "算了", "不要", "不用")
CANCEL_WORDS = (
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
SEAT_HINTS = ("座位", "阅览区")
BOOK_HINTS = ("图书", "预借", "《", "书")
ASSISTANT_CONFIRM_HINTS = ("确认", "提交", "预约", "预借")


def _pending_action_flags(user_id: int) -> tuple[bool, bool]:
    db = SessionLocal()
    try:
        seat = agent_action_service.get_pending_action(
            db, user_id, "seat_reservation"
        )
        book = agent_action_service.get_pending_action(db, user_id, "book_borrow")
        return bool(seat), bool(book)
    except Exception:
        logger.exception("查询待确认动作失败")
        return False, False
    finally:
        db.close()


def _pick_action_type(
    previous_text: str, pending_seat: bool, pending_book: bool
) -> str | None:
    seat_hint = any(word in previous_text for word in SEAT_HINTS)
    book_hint = any(word in previous_text for word in BOOK_HINTS)

    if pending_seat and not pending_book:
        if book_hint and not seat_hint:
            return None
        return "seat_reservation"
    if pending_book and not pending_seat:
        if seat_hint and not book_hint:
            return None
        return "book_borrow"
    if pending_seat and seat_hint and not book_hint:
        return "seat_reservation"
    if pending_book and book_hint and not seat_hint:
        return "book_borrow"
    if pending_seat and seat_hint:
        return "seat_reservation"
    if pending_book and book_hint:
        return "book_borrow"
    return None


def _run_booking_tool(
    tool, history: list[BaseMessage], user: User, **kwargs
) -> dict:
    runtime = ToolRuntime(
        state={"messages": history},
        context={},
        config={"configurable": {"user_id": user.id}},
        stream_writer=lambda _: None,
        tool_call_id=None,
        store=None,
    )
    raw = tool.func(runtime=runtime, **kwargs)
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {"ok": False, "error": str(raw)}


CONFIRM_QUESTION_MARKERS = (
    "确认提交吗？",
    "确认提交吗",
    "确认预约吗？",
    "确认预约吗",
    "确认是否提交？",
    "确认是否提交",
    "要帮你提交吗？",
    "要帮你提交吗",
    "需要我帮你提交吗？",
    "需要我帮你提交吗",
)


def _remove_unbacked_confirmation(reply: str) -> str:
    """没有待确认动作时，去掉模型凭空追加的“确认提交吗？”。"""
    for marker in CONFIRM_QUESTION_MARKERS:
        reply = reply.replace(marker, "")
    reply = reply.strip()
    if not reply:
        return "查询已完成。如需预约，请告诉我具体的区域、日期和时间。"
    return reply


def _extract_book_title(text: str) -> str | None:
    match = re.search(r"《([^》]+)》", text or "")
    return match.group(1) if match else None


def _extract_record_id(text: str) -> int | None:
    match = re.search(r"(?:记录|编号)\s*#?\s*(\d+)", text or "")
    return int(match.group(1)) if match else None


def _extract_date(text: str) -> str | None:
    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text or "")
    return match.group(1) if match else None


def _extract_start_time(text: str) -> str | None:
    match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", text or "")
    if not match:
        return None
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def _extract_seat_no(text: str) -> str | None:
    match = re.search(r"(\d{1,3})\s*号", text or "")
    return match.group(1) if match else None


def _try_direct_booking(
    user: User, history: list[BaseMessage]
) -> ChatMessage | None:
    """确认/取消走确定性处理，不再依赖模型是否记得调用 confirm_*。

    prepare 阶段仍由 Agent 理解用户意图；到了“确认/取消”这一步，
    只要前端历史里上一轮助手展示过摘要、本轮用户明确确认，就直接执行工具。
    """
    if not history or not isinstance(history[-1], HumanMessage):
        return None

    user_text = _content_to_text(history[-1].content)
    previous_text = ""
    if len(history) >= 2 and isinstance(history[-2], AIMessage):
        previous_text = _content_to_text(history[-2].content)
    pending_seat, pending_book = _pending_action_flags(user.id)

    user_seat_hint = any(word in user_text for word in SEAT_HINTS)
    user_book_hint = any(word in user_text for word in BOOK_HINTS)
    # 用户只说“取消预约”时，从上一条助手回复推断是座位还是图书
    seat_context = any(word in previous_text for word in SEAT_HINTS)
    book_context = any(word in previous_text for word in BOOK_HINTS)
    inferred_seat = user_seat_hint or (not user_book_hint and seat_context)
    inferred_book = user_book_hint or (not user_seat_hint and book_context)

    # 已提交的图书预借取消：不依赖模型是否调用 cancel_my_book_borrow
    if (
        not pending_book
        and inferred_book
        and not inferred_seat
        and any(word in user_text for word in CANCEL_WORDS)
    ):
        title = _extract_book_title(user_text)
        result = _run_booking_tool(
            agent_booking_tools.cancel_my_book_borrow,
            history,
            user,
            borrow_id=_extract_record_id(user_text),
            title=title,
        )
        logger.info(
            "AI 取消已提交图书预借走确定性处理: user_id=%s ok=%s",
            user.id,
            result.get("ok"),
        )
        if result.get("ok"):
            return ChatMessage(
                role="assistant",
                content=result.get("message") or "已取消图书预借。",
            )

        candidates = result.get("candidates") or []
        if candidates:
            lines = [
                "找到多条可取消的预借，请回复“取消记录 编号”或指定书名："
            ]
            for candidate in candidates:
                status_text = candidate.get("status_text") or candidate.get("status")
                lines.append(
                    f"- 《{candidate.get('book_title')}》"
                    f"（记录 {candidate.get('borrow_id')}，{status_text}）"
                )
            return ChatMessage(role="assistant", content="\n".join(lines))

        return ChatMessage(
            role="assistant",
            content=result.get("error") or "没有找到可取消的图书预借。",
        )

    # 已提交的座位预约取消：不依赖模型是否调用 cancel_my_seat_reservation
    if (
        not pending_seat
        and inferred_seat
        and not inferred_book
        and any(word in user_text for word in CANCEL_WORDS)
    ):
        result = _run_booking_tool(
            agent_booking_tools.cancel_my_seat_reservation,
            history,
            user,
            reservation_id=_extract_record_id(user_text),
            date=_extract_date(user_text),
            start_time=_extract_start_time(user_text),
            seat_no=_extract_seat_no(user_text),
        )
        logger.info(
            "AI 取消已提交座位预约走确定性处理: user_id=%s ok=%s",
            user.id,
            result.get("ok"),
        )
        if result.get("ok"):
            return ChatMessage(
                role="assistant",
                content=result.get("message") or "已取消座位预约。",
            )

        candidates = result.get("candidates") or []
        if candidates:
            lines = [
                "找到多条可取消的座位预约，请回复“取消记录 编号”，"
                "或指定日期+开始时间："
            ]
            for candidate in candidates:
                status_text = candidate.get("status_text") or candidate.get("status")
                lines.append(
                    f"- {candidate.get('date')} "
                    f"{candidate.get('start_time')}-{candidate.get('end_time')} "
                    f"{candidate.get('area_name')} {candidate.get('seat_no')}号"
                    f"（记录 {candidate.get('reservation_id')}，{status_text}）"
                )
            return ChatMessage(role="assistant", content="\n".join(lines))

        return ChatMessage(
            role="assistant",
            content=result.get("error") or "没有找到可取消的座位预约。",
        )

    if not (pending_seat or pending_book):
        wants_action = any(
            word in user_text
            for word in (
                "确认",
                "确定",
                "提交",
                "取消",
                "算了",
                "不约",
                "不借",
                "不预约",
                "预约吧",
                "约吧",
            )
        )
        if wants_action and previous_text and any(
            word in previous_text for word in ("确认提交", "待确认", "确认预约")
        ):
            return ChatMessage(
                role="assistant",
                content="当前没有待确认的预约或预借，可能已经提交或已过期，请重新选择。",
            )
        return None

    if user_seat_hint and not user_book_hint and not pending_seat:
        return None
    if user_book_hint and not user_seat_hint and not pending_book:
        return None

    action_type = _pick_action_type(previous_text, pending_seat, pending_book)

    if any(word in user_text for word in CANCEL_WORDS):
        if action_type is None:
            return None
        result = _run_booking_tool(
            agent_booking_tools.cancel_pending_action,
            history,
            user,
            action_type=action_type,
        )
        logger.info(
            "AI 取消待确认动作走确定性处理: user_id=%s type=%s ok=%s",
            user.id,
            action_type,
            result.get("ok"),
        )
        message = result.get("message") if result.get("ok") else result.get("error")
        return ChatMessage(
            role="assistant",
            content=message or "取消待确认动作失败，请稍后重试。",
        )

    if any(word in user_text for word in NEGATIVE_WORDS):
        return None
    if not any(word in user_text.lower() for word in CONFIRM_WORDS):
        return None
    if not any(word in previous_text for word in ASSISTANT_CONFIRM_HINTS):
        return None
    if action_type is None:
        return None

    confirm_tool = (
        agent_booking_tools.confirm_seat_reservation
        if action_type == "seat_reservation"
        else agent_booking_tools.confirm_book_borrow
    )
    result = _run_booking_tool(confirm_tool, history, user)
    logger.info(
        "AI 预约确认走确定性处理: user_id=%s type=%s ok=%s",
        user.id,
        action_type,
        result.get("ok"),
    )
    message = result.get("message") if result.get("ok") else result.get("error")
    return ChatMessage(
        role="assistant",
        content=message or "预约提交失败，请稍后重试。",
    )


def chat(user: User, data: ChatRequest) -> ChatMessage:
    """执行一轮 Agent 对话，返回给前端的 assistant 消息。"""
    history = _to_lc_messages(data)

    direct_reply = _try_direct_booking(user, history)
    if direct_reply is not None:
        return direct_reply

    agent = _build_agent(user)
    config = {
        "configurable": {"user_id": user.id},
        "recursion_limit": MAX_AGENT_STEPS,
    }

    try:
        result = agent.invoke({"messages": history}, config=config)
    except Exception as exc:
        logger.exception("Agent 执行失败: %s", exc)
        raise BusinessException(message=_friendly_error(exc)) from exc

    messages = result.get("messages") or []
    _log_tool_calls(messages)

    reply = _extract_reply(messages)
    if not reply:
        raise BusinessException(message="助手没有返回内容，请换个问法再试。")

    if _looks_like_tool_output(reply):
        logger.warning(
            "检测到工具结果被直接返回，已拦截: user_id=%s", user.id
        )
        reply = "抱歉，刚才的查询结果格式异常，请再问一次。"

    pending_seat, pending_book = _pending_action_flags(user.id)
    if not (pending_seat or pending_book):
        reply = _remove_unbacked_confirmation(reply)

    return ChatMessage(role="assistant", content=reply)
