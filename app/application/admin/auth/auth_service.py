from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Any

import app.validation.request_values as request_values
from app.acl.processor import AclEnvironment, AclProcessor
from app.application.admin.auth.admin_auth_login_history import AdminAuthLoginHistory
from app.application.admin.auth.admin_auth_magic_links import AdminAuthMagicLinks
from app.application.admin.auth.admin_auth_messages import AdminAuthMessages
from app.application.admin.auth.admin_auth_passwords import AdminAuthPasswords
from app.application.admin.auth.admin_auth_ports import (
    AdminAuthBotMessageLogPort,
    AdminAuthDatabasePort,
    AdminAuthRepositoryPort,
    AdminAuthSettingsPort,
    AdminAuthUserRepositoryPort,
    AdminAuthWebLoginHistoryPort,
)
from app.application.admin.auth.admin_auth_sessions import AdminAuthSessions
from app.application.admin.auth.errors import (
    AdminAuthAccessDeniedError,
    AdminAuthError,
    AdminAuthTooManyAttemptsError,
    AdminAuthUnauthorizedError,
    AdminAuthValidationError,
)
from app.application.admin.auth.gateways import AdminAuthTelegramGateway
from app.application.admin.auth.models import AdminAuthStartResult, AdminAuthVerifyResult
from app.application.admin.auth.target_path import DEFAULT_ADMIN_TARGET_PATH
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    ensure_super_admin_actor_allowed,
    require_acl_access_allowed,
)
from app.auth.identity import normalize_username
from app.auth.otp import normalize_otp
from app.auth.request_context import WebRequestContext
from app.auth.secrets import hash_secret, verify_secret
from app.reference.admin_actions import ADMIN_DESTRUCTIVE_ACTION_KEYS
from app.time_utils import TimeService

ACTION_OTP_SCREEN_PREFIX = "admin_action_otp:"

__all__ = [
    "ACTION_OTP_SCREEN_PREFIX",
    "AdminAuthBotMessageLogPort",
    "AdminAuthDatabasePort",
    "AdminAuthRepositoryPort",
    "AdminAuthService",
    "AdminAuthSettingsPort",
    "AdminAuthUserRepositoryPort",
    "AdminAuthWebLoginHistoryPort",
]


class AdminAuthService:
    def __init__(self, db: AdminAuthDatabasePort, time_service: TimeService, telegram_gateway: AdminAuthTelegramGateway) -> None:
        self.db = db
        self.time_service = time_service
        self.telegram_gateway = telegram_gateway
        self.acl_processor = AclProcessor(db.acl_permissions)
        self.login_history = AdminAuthLoginHistory(db)
        self.messages = AdminAuthMessages(db, time_service, telegram_gateway)
        self.sessions = AdminAuthSessions(
            db,
            time_service,
            self.acl_processor,
            self.login_history,
            token_urlsafe=lambda length: secrets.token_urlsafe(length),
            with_auth_flags=self._with_auth_flags,
        )
        self.passwords = AdminAuthPasswords(
            db,
            time_service,
            is_dev_login_enabled=lambda: self.is_dev_login_enabled,
        )
        self.magic_links = AdminAuthMagicLinks(
            db,
            time_service,
            self.acl_processor,
            self.login_history,
            self.messages,
            token_urlsafe=lambda length: secrets.token_urlsafe(length),
            create_session_token=self._create_session_token,
            require_acl_access=self._require_acl_access,
            with_auth_flags=self._with_auth_flags,
        )

    @property
    def is_dev_login_enabled(self) -> bool:
        return (
            self.db.settings.app_admin_dev_login_enabled
            and self.db.settings.app_env in {"development", "dev", "local", "test"}
        )

    def start_login(
        self,
        *,
        username: str,
        password: str | None = None,
        request_context: WebRequestContext | None = None,
    ) -> AdminAuthStartResult:
        normalized_username = normalize_username(username)
        current_time = self.time_service.now()
        resolved_user: dict[str, Any] | None = None
        if self.is_dev_login_enabled and normalized_username == "admin":
            user = self.db.admin_auth.ensure_dev_admin_user(current_time=current_time)
        else:
            user = self.db.admin_users.get_login_by_username(normalized_username)
        resolved_user = user

        try:
            if not self.is_dev_login_enabled and user is not None and int(user.get("telegram_user_id") or 0) == 999_000_001:
                raise AdminAuthUnauthorizedError("Invalid credentials")
            if user is None or not self.acl_processor.can_access(user, action="auth/login", environment="web_admin").is_allowed:
                raise AdminAuthUnauthorizedError("Invalid credentials")

            is_dev_admin = self.is_dev_login_enabled and normalized_username == "admin"
            credential = self.db.admin_auth.get_credential(int(user["telegram_user_id"]))
            has_password = bool(credential and credential.get("password_hash")) or is_dev_admin
            if has_password and not password:
                self.log_web_login_event(
                    request_context,
                    telegram_user_id=int(user["telegram_user_id"]),
                    username_attempted=normalized_username,
                    event_type="login_start",
                    result="success",
                    current_time=current_time,
                    details={"requires_password": True},
                )
                return AdminAuthStartResult(
                    challenge_id=None,
                    requires_otp=False,
                    requires_password_setup=False,
                    requires_password=True,
                )
            if is_dev_admin and password and password != "admin":
                raise AdminAuthUnauthorizedError("Invalid credentials")
            if not is_dev_admin and has_password and password and not verify_secret(password, credential["password_hash"]):
                raise AdminAuthUnauthorizedError("Invalid credentials")
        except AdminAuthError as error:
            self.log_web_login_event(
                request_context,
                telegram_user_id=int(resolved_user["telegram_user_id"]) if resolved_user else None,
                username_attempted=normalized_username,
                event_type="login_start",
                result="failure",
                current_time=current_time,
                details={"detail": str(error.detail)},
            )
            raise

        otp_code = "111111" if is_dev_admin else f"{secrets.randbelow(1_000_000):06d}"
        previous_screen = self.db.bot_message_logs.get_latest_active_screen(int(user["telegram_user_id"]))
        challenge = self.db.admin_auth.create_otp_challenge(
            telegram_user_id=int(user["telegram_user_id"]),
            otp_hash=hash_secret(otp_code),
            expires=current_time + timedelta(minutes=self.db.settings.app_admin_otp_ttl_minutes),
            previous_screen_id=previous_screen.get("screen_id") if previous_screen else None,
            sent_chat_id=user.get("chat_id"),
            current_time=current_time,
        )
        if not is_dev_admin:
            message_id = self.send_otp_message(user, otp_code, current_time=current_time)
            if message_id is not None:
                self.db.admin_auth.save_otp_message_id(int(challenge["id"]), message_id, current_time=current_time)

        return AdminAuthStartResult(
            challenge_id=int(challenge["id"]),
            requires_otp=True,
            requires_password_setup=not has_password,
            requires_password=False,
            dev_otp_hint="111111" if is_dev_admin else None,
        )

    def start_action_otp(self, *, user: dict[str, Any], action_key: str) -> dict[str, Any]:
        self._require_acl_access(user, action="acl/manage", environment="web_admin")
        try:
            action_key = request_values.ensure_allowed_value(action_key, ADMIN_DESTRUCTIVE_ACTION_KEYS, "action_key")
        except ValueError as error:
            raise AdminAuthValidationError(str(error)) from error
        self._ensure_super_admin_actor(user)
        current_time = self.time_service.now()
        is_dev_admin = self.is_dev_login_enabled and normalize_username(str(user.get("username") or "")) == "admin"
        otp_code = "111111" if is_dev_admin else f"{secrets.randbelow(1_000_000):06d}"
        challenge = self.db.admin_auth.create_otp_challenge(
            telegram_user_id=int(user["telegram_user_id"]),
            otp_hash=hash_secret(otp_code),
            expires=current_time + timedelta(minutes=self.db.settings.app_admin_otp_ttl_minutes),
            previous_screen_id=f"{ACTION_OTP_SCREEN_PREFIX}{action_key}",
            sent_chat_id=user.get("chat_id"),
            current_time=current_time,
        )
        if not is_dev_admin:
            message_id = self.send_action_otp_message(user, otp_code, action_key=action_key, current_time=current_time)
            if message_id is not None:
                self.db.admin_auth.save_otp_message_id(int(challenge["id"]), message_id, current_time=current_time)
        return {
            "challenge_id": int(challenge["id"]),
            "ttl_minutes": max(int(self.db.settings.app_admin_otp_ttl_minutes), 1),
            "dev_otp_hint": "111111" if is_dev_admin else None,
        }

    def verify_action_otp(self, *, user: dict[str, Any], action_key: str, challenge_id: int, otp: str) -> None:
        self._ensure_super_admin_actor(user)
        current_time = self.time_service.now()
        challenge = self.db.admin_auth.get_otp_challenge(challenge_id)
        expected_screen_id = f"{ACTION_OTP_SCREEN_PREFIX}{action_key}"
        if (
            challenge is None
            or challenge.get("consumed") is not None
            or challenge["expires"] <= current_time
            or int(challenge["telegram_user_id"]) != int(user["telegram_user_id"])
            or challenge.get("previous_screen_id") != expected_screen_id
        ):
            raise AdminAuthUnauthorizedError("Invalid OTP")
        if int(challenge.get("attempts_count") or 0) >= 5:
            raise AdminAuthTooManyAttemptsError("Too many attempts")
        if not verify_secret(normalize_otp(otp), challenge["otp_hash"]):
            self.db.admin_auth.increment_otp_attempts(challenge_id, current_time=current_time)
            raise AdminAuthUnauthorizedError("Invalid OTP")
        self.db.admin_auth.consume_otp_challenge(challenge_id, current_time=current_time)
        self.cleanup_action_otp_message(challenge, user)

    def verify_otp(
        self,
        *,
        challenge_id: int,
        otp: str,
        request_context: WebRequestContext | None = None,
    ) -> AdminAuthVerifyResult:
        current_time = self.time_service.now()
        challenge = self.db.admin_auth.get_otp_challenge(challenge_id)
        if (
            challenge is None
            or challenge.get("consumed") is not None
            or challenge["expires"] <= current_time
            or str(challenge.get("previous_screen_id") or "").startswith(ACTION_OTP_SCREEN_PREFIX)
        ):
            self.log_web_login_event(
                request_context,
                telegram_user_id=int(challenge["telegram_user_id"]) if challenge else None,
                username_attempted=None,
                event_type="otp_verify",
                result="failure",
                current_time=current_time,
                details={"detail": "Invalid OTP"},
            )
            raise AdminAuthUnauthorizedError("Invalid OTP")
        if int(challenge.get("attempts_count") or 0) >= 5:
            self.log_web_login_event(
                request_context,
                telegram_user_id=int(challenge["telegram_user_id"]),
                username_attempted=None,
                event_type="otp_verify",
                result="failure",
                current_time=current_time,
                details={"detail": "Too many attempts"},
            )
            raise AdminAuthTooManyAttemptsError("Too many attempts")

        normalized_otp = normalize_otp(otp)
        if not verify_secret(normalized_otp, challenge["otp_hash"]):
            self.db.admin_auth.increment_otp_attempts(challenge_id, current_time=current_time)
            self.log_web_login_event(
                request_context,
                telegram_user_id=int(challenge["telegram_user_id"]),
                username_attempted=None,
                event_type="otp_verify",
                result="failure",
                current_time=current_time,
                details={"detail": "Invalid OTP"},
            )
            raise AdminAuthUnauthorizedError("Invalid OTP")

        user = self.db.admin_users.get_by_id(int(challenge["telegram_user_id"]))
        if user is None or not self.acl_processor.can_access(user, action="auth/login", environment="web_admin").is_allowed:
            self.log_web_login_event(
                request_context,
                telegram_user_id=int(challenge["telegram_user_id"]),
                username_attempted=None,
                event_type="otp_verify",
                result="failure",
                current_time=current_time,
                details={"detail": "Invalid credentials"},
            )
            raise AdminAuthUnauthorizedError("Invalid credentials")

        self.db.admin_auth.consume_otp_challenge(challenge_id, current_time=current_time)
        token = self._create_session_token(user, request_context, current_time=current_time)
        credential = self.db.admin_auth.get_credential(int(user["telegram_user_id"]))
        is_dev_admin = self.is_dev_login_enabled and normalize_username(str(user.get("username") or "")) == "admin"
        self.log_web_login_event(
            request_context,
            telegram_user_id=int(user["telegram_user_id"]),
            username_attempted=normalize_username(str(user.get("username") or "")) or None,
            event_type="login_success",
            result="success",
            current_time=current_time,
            details={"requires_password_setup": not is_dev_admin and not bool(credential and credential.get("password_hash"))},
        )
        self.cleanup_otp_message(challenge, user, current_time)

        flagged_user = self._with_auth_flags(user)
        return AdminAuthVerifyResult(
            session_token=token,
            requires_password_setup=bool(flagged_user["requires_password_setup"]),
            user=flagged_user,
        )

    def create_admin_magic_link_url(self, *, telegram_user_id: int, target_path: str = DEFAULT_ADMIN_TARGET_PATH) -> str:
        return self.magic_links.create_admin_magic_link_url(telegram_user_id=telegram_user_id, target_path=target_path)

    def consume_magic_link(
        self,
        *,
        token: str,
        request_context: WebRequestContext | None = None,
    ) -> AdminAuthVerifyResult:
        return self.magic_links.consume_magic_link(token=token, request_context=request_context)

    def get_session_user(self, token: str | None, *, request_context: WebRequestContext | None = None) -> dict[str, Any]:
        return self.sessions.get_session_user(token, request_context=request_context)

    def logout(self, token: str | None, *, request_context: WebRequestContext | None = None) -> None:
        self.sessions.logout(token, request_context=request_context)

    def set_password(self, *, user: dict[str, Any], password: str) -> None:
        self._require_acl_access(
            user,
            action="auth/set_password",
            environment="web_admin",
            detail="Access denied",
        )
        self._set_password_hash(user=user, password=password)

    def update_password(self, *, user: dict[str, Any], current_password: str | None, password: str) -> dict[str, Any]:
        self._require_acl_access(
            user,
            action="auth/set_password",
            environment="web_admin",
            detail="Access denied",
        )
        return self.passwords.update_password(user=user, current_password=current_password, password=password)

    def mark_password_prompted(self, *, user: dict[str, Any]) -> dict[str, Any]:
        return self.passwords.mark_password_prompted(user=user)

    def _set_password_hash(self, *, user: dict[str, Any], password: str) -> None:
        self.passwords.set_password_hash(user=user, password=password)

    def _require_acl_access(
        self,
        user: dict[str, Any] | None,
        *,
        action: str,
        environment: AclEnvironment,
        detail: str = "Access denied",
    ) -> None:
        try:
            require_acl_access_allowed(
                self.acl_processor,
                user,
                action=action,
                environment=environment,
                detail=detail,
            )
        except AdminPermissionDeniedError as error:
            raise AdminAuthAccessDeniedError(error.detail) from error

    def _ensure_super_admin_actor(self, user: dict[str, Any]) -> None:
        try:
            ensure_super_admin_actor_allowed(user)
        except AdminPermissionDeniedError as error:
            raise AdminAuthAccessDeniedError(error.detail) from error

    def _with_auth_flags(self, user: dict[str, Any], *, credential: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.passwords.with_auth_flags(user, credential=credential)

    def _create_session_token(
        self,
        user: dict[str, Any],
        request_context: WebRequestContext | None,
        *,
        current_time: datetime,
    ) -> str:
        return self.sessions.create_session_token(user, request_context, current_time=current_time)

    def send_otp_message(self, user: dict[str, Any], otp_code: str, *, current_time: datetime | None = None) -> int | None:
        return self.messages.send_otp_message(user, otp_code, current_time=current_time)

    def send_action_otp_message(
        self,
        user: dict[str, Any],
        otp_code: str,
        *,
        action_key: str,
        current_time: datetime | None = None,
    ) -> int | None:
        return self.messages.send_action_otp_message(
            user,
            otp_code,
            action_key=action_key,
            current_time=current_time,
        )

    def cleanup_action_otp_message(self, challenge: dict[str, Any], user: dict[str, Any]) -> None:
        self.messages.cleanup_action_otp_message(challenge, user)

    def cleanup_otp_message(self, challenge: dict[str, Any], user: dict[str, Any], current_time: datetime | None = None) -> None:
        self.messages.cleanup_otp_message(challenge, user, current_time=current_time)

    def send_login_success_notice(self, user: dict[str, Any], *, current_time: datetime) -> None:
        self.messages.send_login_success_notice(user, current_time=current_time)

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
        self.login_history.log_web_login_event(
            request_context,
            telegram_user_id=telegram_user_id,
            username_attempted=username_attempted,
            event_type=event_type,
            result=result,
            current_time=current_time,
            details=details,
        )
