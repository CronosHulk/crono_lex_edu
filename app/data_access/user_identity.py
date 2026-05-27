from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session

from app.models import User


def get_user_by_telegram_id(session: Any, telegram_user_id: int) -> User | None:
    try:
        user = session.get(User, telegram_user_id)
    except (AttributeError, StatementError, TypeError, ValueError):
        user = None
    if user is not None and getattr(user, "telegram_user_id", None) == telegram_user_id:
        return user
    if not isinstance(session, Session):
        return None
    return session.scalar(select(User).where(User.telegram_user_id == telegram_user_id).limit(1))


def get_user_uuid_by_telegram_id(session: Any, telegram_user_id: int) -> UUID | None:
    user = get_user_by_telegram_id(session, telegram_user_id)
    return getattr(user, "uuid", None) if user is not None else None


def get_user_by_uuid(session: Any, user_uuid: str | UUID) -> User | None:
    try:
        resolved_uuid = user_uuid if isinstance(user_uuid, UUID) else UUID(str(user_uuid))
    except (TypeError, ValueError):
        return None
    return session.scalar(select(User).where(User.uuid == resolved_uuid).limit(1))
