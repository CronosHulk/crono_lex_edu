from __future__ import annotations

from datetime import datetime
from typing import Any

from app.auth.request_context import WebRequestContext

from .admin_auth_ports import AdminAuthDatabasePort


class AdminAuthLoginHistory:
    def __init__(self, db: AdminAuthDatabasePort) -> None:
        self.db = db

    def log_web_login_event(
        self,
        request_context: WebRequestContext | None,
        *,
        telegram_user_id: int | None,
        username_attempted: str | None,
        event_type: str,
        result: str,
        current_time: datetime,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.db.web_login_history.create(
            telegram_user_id=telegram_user_id,
            username_attempted=username_attempted,
            interface_context="admin",
            event_type=event_type,
            result=result,
            api_origin=request_context.api_origin if request_context else None,
            api_path=request_context.api_path if request_context else None,
            client_ip=request_context.client_ip if request_context else None,
            user_agent=request_context.user_agent if request_context else None,
            device_fingerprint_hash=request_context.device_fingerprint_hash if request_context else None,
            details_json=details or {},
            current_time=current_time,
        )
