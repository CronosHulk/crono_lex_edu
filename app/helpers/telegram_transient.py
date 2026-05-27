from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Protocol

ADMIN_LOGIN_SUCCESS_RESTORE_SECONDS = 5
AUTH_OTP_SCREEN_ID = "auth:otp"
AUTH_SUCCESS_SCREEN_ID = "auth:login_success"
WEB_LEARNING_CLAIM_RESTORE_MINUTES = 5


class TelegramTransientMessageGateway(Protocol):
    def send_message(
        self,
        *,
        chat_id: int | str,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        disable_notification: bool = False,
        ignore_errors: bool = False,
    ) -> int | None: ...


def send_tracked_transient_message(
    *,
    db: Any,
    telegram_gateway: TelegramTransientMessageGateway,
    telegram_user_id: int,
    chat_id: int,
    text: str,
    screen_id: str,
    current_time: datetime,
    ttl_seconds: int,
    reply_markup: dict[str, Any] | None = None,
    disable_notification: bool = True,
    ignore_errors: bool = True,
) -> int | None:
    message_id = telegram_gateway.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        disable_notification=disable_notification,
        ignore_errors=ignore_errors,
    )
    if message_id is None:
        return None
    db.bot_message_logs.create(
        telegram_user_id,
        chat_id,
        message_id,
        screen_id,
        current_time + timedelta(seconds=max(ttl_seconds, 0)),
        current_time,
    )
    return message_id


def schedule_main_menu_restore(
    *,
    db: Any,
    telegram_user_id: int,
    chat_id: int,
    current_time: datetime,
    delay_seconds: int,
) -> None:
    db.admin_auth.schedule_bot_restore(
        telegram_user_id=telegram_user_id,
        chat_id=chat_id,
        previous_screen_id=None,
        scheduled_for=current_time + timedelta(seconds=max(delay_seconds, 0)),
        current_time=current_time,
    )
