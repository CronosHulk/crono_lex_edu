from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


class ClientRuntimeBotMessageService:
    def __init__(
        self,
        bot_message_service: Any,
        *,
        dispatch_lock: Callable[[str], AbstractContextManager[bool]],
    ) -> None:
        self.bot_message_service = bot_message_service
        self.dispatch_lock = dispatch_lock

    def track_bot_message(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
        screen_id: str,
        delete_after_hours: int | None = None,
    ) -> dict[str, Any]:
        return self.bot_message_service.track_bot_message(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            message_id=message_id,
            screen_id=screen_id,
            delete_after_hours=delete_after_hours,
        )

    def get_bot_message_log(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
    ) -> dict[str, Any] | None:
        return self.bot_message_service.get_bot_message_log(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            message_id=message_id,
        )

    def list_active_bot_messages(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
    ) -> list[dict[str, Any]]:
        return self.bot_message_service.list_active_bot_messages(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
        )

    def dispatch_due_bot_message_cleanup(self) -> list[dict[str, Any]]:
        with self.dispatch_lock("bot_message_cleanup") as acquired:
            if not acquired:
                return []
            return self.bot_message_service.dispatch_due_bot_message_cleanup()

    def save_bot_message_cleanup_result(
        self,
        *,
        message_log_id: int,
        is_deleted: bool,
        error_text: str | None = None,
    ) -> None:
        self.bot_message_service.save_bot_message_cleanup_result(
            message_log_id=message_log_id,
            is_deleted=is_deleted,
            error_text=error_text,
        )
