from __future__ import annotations

import hmac
import secrets
from datetime import datetime, timedelta
from typing import Any, Protocol

from app.application.client_web.auth_errors import ClientWebAuthUnauthorizedError
from app.auth.request_context import WebRequestContext
from app.auth.secrets import hash_secret, verify_secret
from app.reference.teacher_referrals import build_teacher_referral_url
from app.time_utils import TimeService


class ClientWebAuthSessionSettingsPort(Protocol):
    app_admin_session_hours: int
    app_bot_username: str


class ClientWebAuthSessionRepositoryPort(Protocol):
    def get_active_session_by_token_hash(self, *, token_hash_matcher: Any, current_time: datetime) -> dict[str, Any] | None: ...

    def revoke_session(self, session_id: int, *, current_time: datetime) -> None: ...

    def touch_session(self, session_id: int, *, current_time: datetime) -> None: ...

    def revoke_session_by_token_match(self, *, token_hash_matcher: Any, current_time: datetime) -> None: ...

    def create_session(
        self,
        *,
        telegram_user_id: int,
        session_token_hash: str,
        expires: datetime,
        api_origin: str | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
        device_fingerprint_hash: str | None = None,
        current_time: datetime,
    ) -> dict[str, Any]: ...

    def get_user_by_id(self, telegram_user_id: int) -> dict[str, Any] | None: ...

    def get_credential(self, telegram_user_id: int) -> dict[str, Any] | None: ...


class ClientWebAuthSessionWebLoginHistoryPort(Protocol):
    def create(self, **kwargs: Any) -> dict[str, Any]: ...


class ClientWebAuthSessionDatabasePort(Protocol):
    settings: ClientWebAuthSessionSettingsPort
    client_web_auth: ClientWebAuthSessionRepositoryPort
    web_login_history: ClientWebAuthSessionWebLoginHistoryPort


class ClientWebAuthSessionService:
    def __init__(self, db: ClientWebAuthSessionDatabasePort, time_service: TimeService) -> None:
        self.db = db
        self.time_service = time_service

    def get_session_user(self, token: str | None, *, request_context: WebRequestContext | None) -> dict[str, Any]:
        if not token:
            raise ClientWebAuthUnauthorizedError("Not authenticated")
        current_time = self.time_service.now()
        session = self.db.client_web_auth.get_active_session_by_token_hash(
            token_hash_matcher=lambda stored_hash: verify_secret(token, stored_hash),
            current_time=current_time,
        )
        if session is None:
            raise ClientWebAuthUnauthorizedError("Not authenticated")
        if request_context is not None and session.get("device_fingerprint_hash"):
            if not hmac.compare_digest(str(session["device_fingerprint_hash"]), request_context.device_fingerprint_hash):
                self.db.client_web_auth.revoke_session(int(session["id"]), current_time=current_time)
                raise ClientWebAuthUnauthorizedError("Device or network changed. Please log in again.")
        user = self.db.client_web_auth.get_user_by_id(int(session["telegram_user_id"]))
        if user is None:
            raise ClientWebAuthUnauthorizedError("Not authenticated")
        self.db.client_web_auth.touch_session(int(session["id"]), current_time=current_time)
        return self.with_auth_flags(user)

    def logout(self, token: str | None) -> None:
        if not token:
            return
        self.db.client_web_auth.revoke_session_by_token_match(
            token_hash_matcher=lambda stored_hash: verify_secret(token, stored_hash),
            current_time=self.time_service.now(),
        )

    def create_session_token(
        self,
        user: dict[str, Any],
        request_context: WebRequestContext | None,
        *,
        current_time: datetime,
    ) -> str:
        token = secrets.token_urlsafe(48)
        self.db.client_web_auth.create_session(
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

    def log_login_event(
        self,
        request_context: WebRequestContext | None,
        *,
        telegram_user_id: int,
        username_attempted: str | None,
        event_type: str,
        current_time: datetime,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.db.web_login_history.create(
            telegram_user_id=telegram_user_id,
            username_attempted=username_attempted,
            interface_context="client_web",
            event_type=event_type,
            result="success",
            api_origin=request_context.api_origin if request_context else None,
            api_path=request_context.api_path if request_context else None,
            client_ip=request_context.client_ip if request_context else None,
            user_agent=request_context.user_agent if request_context else None,
            device_fingerprint_hash=request_context.device_fingerprint_hash if request_context else None,
            details_json=details or {},
            current_time=current_time,
        )

    def with_auth_flags(self, user: dict[str, Any]) -> dict[str, Any]:
        credential = self.db.client_web_auth.get_credential(int(user["telegram_user_id"]))
        has_password = bool(credential and credential.get("password_hash"))
        return {
            **user,
            "has_password": has_password,
            "requires_password_setup": not has_password and not bool(user.get("client_web_password_prompted")),
            "teacher_referral_url": self._build_teacher_referral_url(user),
        }

    def _build_teacher_referral_url(self, user: dict[str, Any]) -> str | None:
        if user.get("learning_role") != "teacher":
            return None
        return build_teacher_referral_url(
            getattr(self.db.settings, "app_bot_username", ""),
            user.get("user_id") or user.get("user_uuid"),
        )
