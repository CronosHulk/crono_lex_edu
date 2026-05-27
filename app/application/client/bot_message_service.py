from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Protocol

from app.time_utils import TimeService

BOT_MESSAGE_CLEANUP_RETRY_MINUTES = 30


class BotMessageLogPort(Protocol):
    def create(
        self,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
        screen_id: str,
        delete_after: datetime,
        current_time: datetime,
    ) -> dict[str, Any]: ...

    def get_latest_for_message(
        self,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
    ) -> dict[str, Any] | None: ...

    def list_active(self, telegram_user_id: int, chat_id: int) -> list[dict[str, Any]]: ...

    def claim_due_cleanup(self, current_time: datetime, retry_before: datetime) -> list[dict[str, Any]]: ...

    def save_cleanup_result(
        self,
        message_log_id: int,
        *,
        is_deleted: bool,
        current_time: datetime,
        error_text: str | None = None,
    ) -> None: ...


class ClientBotMessageService:
    def __init__(
        self,
        bot_message_logs: BotMessageLogPort,
        time_service: TimeService,
        *,
        retention_days: int,
    ) -> None:
        self.bot_message_logs = bot_message_logs
        self.time_service = time_service
        self.retention_days = retention_days

    def track_bot_message(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
        screen_id: str,
        delete_after_hours: int | None = None,
    ) -> dict[str, Any]:
        current_time = self.time_service.now()
        retention_days = max(self.retention_days, 0)
        effective_delete_after = (
            current_time + timedelta(hours=max(delete_after_hours, 0))
            if delete_after_hours is not None
            else current_time + timedelta(days=retention_days)
        )
        return self.bot_message_logs.create(
            telegram_user_id,
            chat_id,
            message_id,
            screen_id,
            effective_delete_after,
            current_time,
        )

    def get_bot_message_log(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
    ) -> dict[str, Any] | None:
        return self.bot_message_logs.get_latest_for_message(telegram_user_id, chat_id, message_id)

    def list_active_bot_messages(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
    ) -> list[dict[str, Any]]:
        return self.bot_message_logs.list_active(telegram_user_id, chat_id)

    def dispatch_due_bot_message_cleanup(self) -> list[dict[str, Any]]:
        current_time = self.time_service.now()
        retry_before = current_time - timedelta(minutes=BOT_MESSAGE_CLEANUP_RETRY_MINUTES)
        return self.bot_message_logs.claim_due_cleanup(current_time, retry_before)

    def save_bot_message_cleanup_result(
        self,
        *,
        message_log_id: int,
        is_deleted: bool,
        error_text: str | None = None,
    ) -> None:
        self.bot_message_logs.save_cleanup_result(
            message_log_id,
            is_deleted=is_deleted,
            current_time=self.time_service.now(),
            error_text=error_text,
        )
