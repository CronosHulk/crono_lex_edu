from __future__ import annotations

import hmac
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from app.acl.processor import AclProcessor
from app.application.admin.auth.errors import AdminAuthUnauthorizedError
from app.auth.request_context import WebRequestContext
from app.auth.secrets import hash_secret, verify_secret
from app.time_utils import TimeService

from .admin_auth_login_history import AdminAuthLoginHistory
from .admin_auth_ports import AdminAuthDatabasePort


class AdminAuthSessions:
    def __init__(
        self,
        db: AdminAuthDatabasePort,
        time_service: TimeService,
        acl_processor: AclProcessor,
        login_history: AdminAuthLoginHistory,
        *,
        token_urlsafe: Callable[[int], str],
        with_auth_flags: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.acl_processor = acl_processor
        self.login_history = login_history
        self.token_urlsafe = token_urlsafe
        self.with_auth_flags = with_auth_flags

    def create_session_token(
        self,
        user: dict[str, Any],
        request_context: WebRequestContext | None,
        *,
        current_time: datetime,
    ) -> str:
        token = self.token_urlsafe(48)
        self.db.admin_auth.create_session(
            telegram_user_id=int(user["telegram_user_id"]),
            session_token_hash=hash_secret(token),
            expires=current_time + timedelta(hours=self.db.settings.app_admin_session_hours),
            api_origin=request_context.api_origin if request_context else None,
            client_ip=request_context.client_ip if request_context else None,
            user_agent=request_context.user_agent if request_context else None,
            device_fingerprint_hash=request_context.device_fingerprint_hash if request_context else None,
            current_time=current_time,
        )
        return token

    def get_session_user(self, token: str | None, *, request_context: WebRequestContext | None = None) -> dict[str, Any]:
        if not token:
            raise AdminAuthUnauthorizedError("Not authenticated")
        current_time = self.time_service.now()
        session = self.db.admin_auth.get_active_session_by_token_hash(
            token_hash_matcher=lambda stored_hash: verify_secret(token, stored_hash),
            current_time=current_time,
        )
        if session is None:
            raise AdminAuthUnauthorizedError("Not authenticated")
        if request_context is not None and session.get("device_fingerprint_hash"):
            if not hmac.compare_digest(str(session["device_fingerprint_hash"]), request_context.device_fingerprint_hash):
                self.db.admin_auth.revoke_session(int(session["id"]), current_time=current_time)
                self.login_history.log_web_login_event(
                    request_context,
                    telegram_user_id=int(session["telegram_user_id"]),
                    username_attempted=None,
                    event_type="session_invalidated",
                    result="failure",
                    current_time=current_time,
                    details={
                        "reason": "device_or_network_changed",
                        "previous_api_origin": session.get("api_origin"),
                        "previous_client_ip": session.get("client_ip"),
                    },
                )
                raise AdminAuthUnauthorizedError("Device or network changed. Please log in again.")
        user = self.db.admin_users.get_by_id(int(session["telegram_user_id"]))
        if user is None or not self.acl_processor.can_access(user, action="auth/use_session", environment="web_admin").is_allowed:
            raise AdminAuthUnauthorizedError("Not authenticated")
        self.db.admin_auth.touch_session(int(session["id"]), current_time=current_time)
        credential = self.db.admin_auth.get_credential(int(user["telegram_user_id"]))
        return self.with_auth_flags(user, credential=credential)

    def logout(self, token: str | None, *, request_context: WebRequestContext | None = None) -> None:
        if not token:
            return
        current_time = self.time_service.now()
        session = self.db.admin_auth.get_active_session_by_token_hash(
            token_hash_matcher=lambda stored_hash: verify_secret(token, stored_hash),
            current_time=current_time,
        )
        if session is not None:
            self.login_history.log_web_login_event(
                request_context,
                telegram_user_id=int(session["telegram_user_id"]),
                username_attempted=None,
                event_type="logout",
                result="success",
                current_time=current_time,
            )
        self.db.admin_auth.revoke_session_by_token_match(
            token_hash_matcher=lambda stored_hash: verify_secret(token, stored_hash),
            current_time=current_time,
        )
