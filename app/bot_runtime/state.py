from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ActiveScreenMessage:
    message_id: int
    message_log_id: int | None = None
    has_audio: bool = False
    screen_id: str | None = None


def read_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def build_message_log_refs(messages: list[ActiveScreenMessage]) -> list[dict[str, int]]:
    refs: list[dict[str, int]] = []
    for message in messages:
        if message.message_log_id is None:
            continue
        refs.append({"message_id": message.message_id, "message_log_id": message.message_log_id})
    return refs


def get_active_screen_message(user_data: dict | None) -> ActiveScreenMessage | None:
    if user_data is None:
        return None

    active_message_id = user_data.get("active_screen_message_id")
    if isinstance(active_message_id, int):
        return ActiveScreenMessage(
            message_id=active_message_id,
            message_log_id=read_int(user_data.get("active_screen_message_log_id")),
            has_audio=bool(user_data.get("active_screen_has_audio", False)),
            screen_id=user_data.get("active_screen_screen_id")
            if isinstance(user_data.get("active_screen_screen_id"), str)
            else None,
        )

    message_ids = list(user_data.get("bot_message_ids", []))
    if not message_ids:
        return None
    refs_by_message_id = {
        item["message_id"]: item["message_log_id"]
        for item in user_data.get("bot_message_log_refs", [])
        if "message_id" in item and "message_log_id" in item
    }
    message_id = message_ids[-1]
    return ActiveScreenMessage(
        message_id=message_id,
        message_log_id=refs_by_message_id.get(message_id),
        has_audio=bool(user_data.get("active_screen_has_audio", False)),
        screen_id=user_data.get("active_screen_screen_id")
        if isinstance(user_data.get("active_screen_screen_id"), str)
        else None,
    )


def save_active_screen_message(user_data: dict, active_message: ActiveScreenMessage) -> None:
    previous_message_ids = [
        message_id
        for message_id in user_data.get("bot_message_ids", [])
        if isinstance(message_id, int) and message_id != active_message.message_id
    ]
    previous_refs = [
        item
        for item in user_data.get("bot_message_log_refs", [])
        if item.get("message_id") != active_message.message_id
    ]
    user_data["active_screen_message_id"] = active_message.message_id
    user_data["active_screen_message_log_id"] = active_message.message_log_id
    user_data["active_screen_has_audio"] = active_message.has_audio
    user_data["active_screen_screen_id"] = active_message.screen_id
    user_data["bot_message_ids"] = [*previous_message_ids, active_message.message_id]
    user_data["bot_message_log_refs"] = [*previous_refs, *build_message_log_refs([active_message])]


def get_auxiliary_screen_message(user_data: dict | None) -> ActiveScreenMessage | None:
    if user_data is None:
        return None
    message_id = read_int(user_data.get("auxiliary_screen_message_id"))
    if message_id is None:
        return None
    return ActiveScreenMessage(
        message_id=message_id,
        message_log_id=read_int(user_data.get("auxiliary_screen_message_log_id")),
        has_audio=False,
    )


def save_auxiliary_screen_message(user_data: dict, message: ActiveScreenMessage) -> None:
    user_data["auxiliary_screen_message_id"] = message.message_id
    user_data["auxiliary_screen_message_log_id"] = message.message_log_id


def clear_auxiliary_screen_message_state(user_data: dict | None) -> None:
    if user_data is None:
        return
    user_data["auxiliary_screen_message_id"] = None
    user_data["auxiliary_screen_message_log_id"] = None
