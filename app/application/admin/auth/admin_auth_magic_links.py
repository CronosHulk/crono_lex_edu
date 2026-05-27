from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

from app.acl.processor import AclProcessor
from app.application.admin.auth.errors import AdminAuthUnauthorizedError
from app.application.admin.auth.models import AdminAuthVerifyResult
from app.application.admin.auth.target_path import (
    DEFAULT_ADMIN_TARGET_PATH,
    normalize_admin_target_path,
)
from app.auth.identity import normalize_username
from app.auth.request_context import WebRequestContext
from app.auth.secrets import hash_token_for_lookup
from app.time_utils import TimeService

from .admin_auth_login_history import AdminAuthLoginHistory
from .admin_auth_messages import AdminAuthMessages
from .admin_auth_ports import AdminAuthDatabasePort


class AdminAuthMagicLinks:
    def __init__(
        self,
        db: AdminAuthDatabasePort,
        time_service: TimeService,
        acl_processor: AclProcessor,
        login_history: AdminAuthLoginHistory,
        messages: AdminAuthMessages,
        *,
        token_urlsafe: Callable[[int], str],
        create_session_token: Callable[[dict[str, Any], WebRequestContext | None, Any], str],
        require_acl_access: Callable[..., None],
        with_auth_flags: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.acl_processor = acl_processor
        self.login_history = login_history
        self.messages = messages
        self.token_urlsafe = token_urlsafe
        self.create_session_token = create_session_token
        self.require_acl_access = require_acl_access
        self.with_auth_flags = with_auth_flags

    def create_admin_magic_link_url(self, *, telegram_user_id: int, target_path: str = DEFAULT_ADMIN_TARGET_PATH) -> str:
        user = self.db.admin_users.get_by_id(telegram_user_id)
        self.require_acl_access(
            user,
            action="auth/login",
            environment="web_admin",
            detail="Admin access required",
        )
        current_time = self.time_service.now()
        token = self.token_urlsafe(48)
        normalized_target = normalize_admin_target_path(target_path)
        self.db.admin_auth.create_magic_link(
            telegram_user_id=telegram_user_id,
            token_hash=hash_token_for_lookup(token),
            target_path=normalized_target,
            expires=current_time + timedelta(minutes=self.db.settings.app_admin_magic_link_ttl_minutes),
            current_time=current_time,
        )
        query = urlencode({"token": token, "next": normalized_target})
        return f"{self.db.settings.app_web_base_url.rstrip('/')}/admin/auth/magic?{query}"

    def consume_magic_link(
        self,
        *,
        token: str,
        request_context: WebRequestContext | None = None,
    ) -> AdminAuthVerifyResult:
        current_time = self.time_service.now()
        token_value = str(token or "").strip()
        magic_link = self.db.admin_auth.get_active_magic_link_by_token_hash(
            hash_token_for_lookup(token_value),
            current_time=current_time,
        )
        if magic_link is None:
            self.login_history.log_web_login_event(
                request_context,
                telegram_user_id=None,
                username_attempted=None,
                event_type="magic_login",
                result="failure",
                current_time=current_time,
                details={"detail": "Invalid magic link"},
            )
            raise AdminAuthUnauthorizedError("Invalid magic link")
        user = self.db.admin_users.get_by_id(int(magic_link["telegram_user_id"]))
        if user is None or not self.acl_processor.can_access(user, action="auth/login", environment="web_admin").is_allowed:
            self.login_history.log_web_login_event(
                request_context,
                telegram_user_id=int(magic_link["telegram_user_id"]),
                username_attempted=None,
                event_type="magic_login",
                result="failure",
                current_time=current_time,
                details={"detail": "Invalid credentials"},
            )
            raise AdminAuthUnauthorizedError("Invalid credentials")
        session_token = self.create_session_token(user, request_context, current_time=current_time)
        self.db.admin_auth.consume_magic_link(int(magic_link["id"]), current_time=current_time)
        self.login_history.log_web_login_event(
            request_context,
            telegram_user_id=int(user["telegram_user_id"]),
            username_attempted=normalize_username(str(user.get("username") or "")) or None,
            event_type="magic_login",
            result="success",
            current_time=current_time,
            details={"target_path": magic_link["target_path"]},
        )
        self.messages.send_login_success_notice(user, current_time=current_time)
        flagged_user = self.with_auth_flags(user)
        return AdminAuthVerifyResult(
            session_token=session_token,
            requires_password_setup=bool(flagged_user["requires_password_setup"]),
            user=flagged_user,
            target_path=str(magic_link["target_path"]),
        )
