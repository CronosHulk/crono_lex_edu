from __future__ import annotations

from typing import Any


def with_runtime_telegram_user_id(session: dict[str, Any], telegram_user_id: int) -> dict[str, Any]:
    return {**session, "telegram_user_id": telegram_user_id}


def resolve_runtime_telegram_user_id(session: dict[str, Any], explicit_value: int | None) -> int:
    if explicit_value is not None:
        return int(explicit_value)
    value = session.get("telegram_user_id")
    if value is None:
        raise ValueError("telegram_user_id runtime context is required")
    return int(value)
