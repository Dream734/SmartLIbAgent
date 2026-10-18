"""AI 待确认动作的持久化与状态流转。

动作生命周期：
pending -> processing -> confirmed / failed
pending -> cancelled（用户反悔）
pending -> expired（超过确认时限）
"""

import json
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.agent_action import AgentAction

logger = logging.getLogger(__name__)

ACTION_TTL_MINUTES = 5
PROCESSING_TIMEOUT_MINUTES = 2
VALID_ACTION_TYPES = ("seat_reservation", "book_borrow")


def _now() -> datetime:
    return datetime.now()


def expire_stale_actions(db: Session) -> None:
    """惰性清理：过期的 pending 置为 expired，卡死的 processing 置为 failed。"""
    now = _now()

    expired = (
        db.query(AgentAction)
        .filter(
            AgentAction.status == "pending",
            AgentAction.expire_time < now,
        )
        .update(
            {"status": "expired", "update_time": now},
            synchronize_session=False,
        )
    )

    failed = (
        db.query(AgentAction)
        .filter(
            AgentAction.status == "processing",
            AgentAction.update_time < now - timedelta(minutes=PROCESSING_TIMEOUT_MINUTES),
        )
        .update(
            {"status": "failed", "update_time": now},
            synchronize_session=False,
        )
    )

    if expired or failed:
        db.commit()


def create_pending_action(
    db: Session,
    user_id: int,
    action_type: str,
    payload: dict,
    summary: str,
    ttl_minutes: int = ACTION_TTL_MINUTES,
) -> AgentAction:
    """创建待确认动作，并作废同一用户、同一类型的旧 pending 动作。"""
    if action_type not in VALID_ACTION_TYPES:
        raise ValueError(f"不支持的动作类型: {action_type}")

    expire_stale_actions(db)
    now = _now()

    db.query(AgentAction).filter(
        AgentAction.user_id == user_id,
        AgentAction.action_type == action_type,
        AgentAction.status == "pending",
    ).update(
        {"status": "cancelled", "update_time": now},
        synchronize_session=False,
    )

    action = AgentAction(
        user_id=user_id,
        action_type=action_type,
        payload=json.dumps(payload, ensure_ascii=False),
        summary=summary,
        status="pending",
        expire_time=now + timedelta(minutes=ttl_minutes),
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def get_pending_action(
    db: Session, user_id: int, action_type: str
) -> AgentAction | None:
    """取当前用户、当前类型最新的一条待确认动作。"""
    expire_stale_actions(db)
    return (
        db.query(AgentAction)
        .filter(
            AgentAction.user_id == user_id,
            AgentAction.action_type == action_type,
            AgentAction.status == "pending",
        )
        .order_by(AgentAction.id.desc())
        .first()
    )


def claim_action(db: Session, action_id: int) -> bool:
    """原子抢占动作，避免双击/重试导致重复写业务表。"""
    updated = (
        db.query(AgentAction)
        .filter(
            AgentAction.id == action_id,
            AgentAction.status == "pending",
        )
        .update(
            {"status": "processing", "update_time": _now()},
            synchronize_session=False,
        )
    )
    db.commit()
    return bool(updated)


def mark_confirmed(db: Session, action_id: int, result: dict) -> None:
    db.query(AgentAction).filter(AgentAction.id == action_id).update(
        {
            "status": "confirmed",
            "result": json.dumps(result, ensure_ascii=False),
            "update_time": _now(),
        },
        synchronize_session=False,
    )
    db.commit()


def mark_failed(db: Session, action_id: int, reason: str) -> None:
    db.query(AgentAction).filter(AgentAction.id == action_id).update(
        {
            "status": "failed",
            "result": json.dumps({"error": reason}, ensure_ascii=False),
            "update_time": _now(),
        },
        synchronize_session=False,
    )
    db.commit()


def cancel_pending_action(
    db: Session, user_id: int, action_type: str
) -> AgentAction | None:
    """取消尚未确认的动作；不会影响已经提交的预约/借阅。"""
    expire_stale_actions(db)
    action = (
        db.query(AgentAction)
        .filter(
            AgentAction.user_id == user_id,
            AgentAction.action_type == action_type,
            AgentAction.status == "pending",
        )
        .order_by(AgentAction.id.desc())
        .first()
    )
    if not action:
        return None

    action.status = "cancelled"
    db.commit()
    db.refresh(action)
    return action
