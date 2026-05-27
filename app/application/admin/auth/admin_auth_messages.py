from __future__ import annotations

from datetime import datetime
from typing import Any

from app.application.admin.auth.gateways import AdminAuthTelegramGateway
from app.auth.otp import format_otp
from app.helpers.telegram_transient import (
    ADMIN_LOGIN_SUCCESS_RESTORE_SECONDS,
    AUTH_OTP_SCREEN_ID,
    AUTH_SUCCESS_SCREEN_ID,
    send_tracked_transient_message,
)
from app.time_utils import TimeService

from .admin_auth_ports import AdminAuthDatabasePort


class AdminAuthMessages:
    def __init__(self, db: AdminAuthDatabasePort, time_service: TimeService, telegram_gateway: AdminAuthTelegramGateway) -> None:
        self.db = db
        self.time_service = time_service
        self.telegram_gateway = telegram_gateway

    def send_otp_message(self, user: dict[str, Any], otp_code: str, *, current_time: datetime | None = None) -> int | None:
        chat_id = user.get("chat_id")
        if not chat_id:
            return None
        text = f"Код входу CronoLex Admin: {format_otp(otp_code)}"
        current_time = current_time or self.time_service.now()
        return send_tracked_transient_message(
            db=self.db,
            telegram_gateway=self.telegram_gateway,
            telegram_user_id=int(user["telegram_user_id"]),
            chat_id=int(chat_id),
            text=text,
            screen_id=AUTH_OTP_SCREEN_ID,
            current_time=current_time,
            ttl_seconds=max(int(self.db.settings.app_admin_otp_ttl_minutes), 1) * 60,
            disable_notification=False,
            ignore_errors=False,
        )

    def send_action_otp_message(
        self,
        user: dict[str, Any],
        otp_code: str,
        *,
        action_key: str,
        current_time: datetime | None = None,
    ) -> int | None:
        chat_id = user.get("chat_id")
        if not chat_id:
            return None
        text = f"CronoLex OTP ({action_key}): {format_otp(otp_code)}"
        current_time = current_time or self.time_service.now()
        return send_tracked_transient_message(
            db=self.db,
            telegram_gateway=self.telegram_gateway,
            telegram_user_id=int(user["telegram_user_id"]),
            chat_id=int(chat_id),
            text=text,
            screen_id=AUTH_OTP_SCREEN_ID,
            current_time=current_time,
            ttl_seconds=max(int(self.db.settings.app_admin_otp_ttl_minutes), 1) * 60,
            disable_notification=False,
            ignore_errors=False,
        )

    def cleanup_action_otp_message(self, challenge: dict[str, Any], user: dict[str, Any]) -> None:
        chat_id = challenge.get("sent_chat_id") or user.get("chat_id")
        message_id = challenge.get("sent_message_id")
        if chat_id and message_id:
            self.telegram_gateway.delete_message(chat_id=chat_id, message_id=message_id, ignore_errors=True)

    def cleanup_otp_message(self, challenge: dict[str, Any], user: dict[str, Any], current_time: datetime | None = None) -> None:
        chat_id = challenge.get("sent_chat_id") or user.get("chat_id")
        message_id = challenge.get("sent_message_id")
        current_time = current_time or self.time_service.now()
        if chat_id and message_id:
            self.telegram_gateway.delete_message(chat_id=chat_id, message_id=message_id, ignore_errors=True)
        if chat_id:
            self.send_login_success_notice({**user, "chat_id": chat_id}, current_time=current_time)

    def send_login_success_notice(self, user: dict[str, Any], *, current_time: datetime) -> None:
        chat_id = user.get("chat_id")
        if not chat_id:
            return
        send_tracked_transient_message(
            db=self.db,
            telegram_gateway=self.telegram_gateway,
            telegram_user_id=int(user["telegram_user_id"]),
            chat_id=int(chat_id),
            text="Вхід виконано успішно",
            screen_id=AUTH_SUCCESS_SCREEN_ID,
            current_time=current_time,
            ttl_seconds=ADMIN_LOGIN_SUCCESS_RESTORE_SECONDS,
            disable_notification=False,
            ignore_errors=True,
        )
