from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionActionPayload:
    session_id: int
    action_type: str
    session_word_id: int | None = None
    card_action: str | None = None
    expected_stage: str | None = None
    decision: str | None = None
    option_index: int | None = None


def parse_int_or_none(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_session_action(action: str) -> SessionActionPayload | None:
    parts = action.split(":")
    if len(parts) < 3 or parts[0] != "s":
        return None
    session_id = parse_int_or_none(parts[1])
    if session_id is None:
        return None
    action_type = parts[2]
    if action_type == "c":
        return SessionActionPayload(
            session_id=session_id,
            action_type=action_type,
            session_word_id=parse_int_or_none(parts[3]) if len(parts) >= 4 else None,
            card_action=parts[4] if len(parts) >= 5 else None,
        )
    if action_type == "ready":
        return SessionActionPayload(
            session_id=session_id,
            action_type=action_type,
            expected_stage=parts[3] if len(parts) >= 4 else None,
            decision=parts[4] if len(parts) >= 5 else None,
        )
    if action_type == "a":
        return SessionActionPayload(
            session_id=session_id,
            action_type=action_type,
            session_word_id=parse_int_or_none(parts[3]) if len(parts) >= 4 else None,
            option_index=parse_int_or_none(parts[4]) if len(parts) >= 5 else None,
        )
    return SessionActionPayload(session_id=session_id, action_type=action_type)
