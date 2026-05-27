from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol
from urllib.parse import urlencode

from app.application.client_web.auth_errors import (
    ClientWebAuthNotFoundError,
    ClientWebAuthRateLimitError,
    ClientWebAuthUnauthorizedError,
    ClientWebAuthValidationError,
)
from app.application.client_web.auth_gateways import ClientWebAuthTelegramGateway
from app.application.client_web.auth_session_service import ClientWebAuthSessionService
from app.auth.identity import normalize_username
from app.auth.otp import format_otp, normalize_otp
from app.auth.password import validate_password_complexity
from app.auth.request_context import WebRequestContext
from app.auth.secrets import hash_secret, hash_token_for_lookup, verify_secret
from app.helpers.locale import resolve_user_locale
from app.helpers.telegram_transient import (
    ADMIN_LOGIN_SUCCESS_RESTORE_SECONDS,
    AUTH_OTP_SCREEN_ID,
    AUTH_SUCCESS_SCREEN_ID,
    send_tracked_transient_message,
)
from app.i18n import translate
from app.time_utils import TimeService

CLIENT_WEB_MAGIC_TARGET_PATHS = {"/", "/import-words", "/settings"}


@dataclass(frozen=True)
class ClientWebAuthStartResult:
    challenge_id: int | None
    requires_otp: bool
    requires_password_setup: bool
    requires_password: bool = False


@dataclass(frozen=True)
class ClientWebAuthResult:
    session_token: str
    user: dict[str, Any]
    target_path: str | None = None


class ClientWebAuthSettingsPort(Protocol):
    app_admin_otp_ttl_minutes: int
    app_admin_magic_link_ttl_minutes: int
    app_admin_session_hours: int
    app_web_base_url: str
    app_bot_username: str


class ClientWebAuthRepositoryPort(Protocol):
    def get_user_by_username(self, username: str) -> dict[str, Any] | None: ...

    def get_credential(self, telegram_user_id: int) -> dict[str, Any] | None: ...

    def create_otp_challenge(
        self,
        *,
        telegram_user_id: int,
        otp_hash: str,
        expires: datetime,
        sent_chat_id: int | None,
        current_time: datetime,
    ) -> dict[str, Any]: ...

    def save_otp_message_id(self, challenge_id: int, message_id: int, *, current_time: datetime) -> None: ...

    def get_otp_challenge(self, challenge_id: int) -> dict[str, Any] | None: ...

    def increment_otp_attempts(self, challenge_id: int, *, current_time: datetime) -> None: ...

    def get_user_by_id(self, telegram_user_id: int) -> dict[str, Any] | None: ...

    def consume_otp_challenge(self, challenge_id: int, *, current_time: datetime) -> None: ...

    def set_password_hash(self, telegram_user_id: int, password_hash: str, *, current_time: datetime) -> None: ...

    def mark_password_prompted(self, telegram_user_id: int, *, current_time: datetime) -> None: ...

    def get_active_magic_link_by_token_hash(self, token_hash: str, *, current_time: datetime) -> dict[str, Any] | None: ...

    def get_magic_link_by_token_hash(self, token_hash: str) -> dict[str, Any] | None: ...

    def consume_magic_link(self, magic_link_id: int, *, current_time: datetime) -> None: ...

    def create_magic_link(
        self,
        *,
        telegram_user_id: int,
        token_hash: str,
        target_path: str,
        expires: datetime,
        current_time: datetime,
    ) -> dict[str, Any]: ...

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


class ClientWebAuthWebLoginHistoryPort(Protocol):
    def create(self, **kwargs: Any) -> dict[str, Any]: ...


class ClientWebAuthBotMessageLogPort(Protocol):
    def create(
        self,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
        screen_id: str,
        delete_after: datetime,
        current_time: datetime,
    ) -> dict[str, Any]: ...


class ClientWebAuthDatabasePort(Protocol):
    settings: ClientWebAuthSettingsPort
    client_web_auth: ClientWebAuthRepositoryPort
    web_login_history: ClientWebAuthWebLoginHistoryPort
    bot_message_logs: ClientWebAuthBotMessageLogPort


class ClientWebAuthService:
    def __init__(self, db: ClientWebAuthDatabasePort, time_service: TimeService, telegram_gateway: ClientWebAuthTelegramGateway) -> None:
        self.db = db
        self.time_service = time_service
        self.telegram_gateway = telegram_gateway
        self.session_service = ClientWebAuthSessionService(db, time_service)

    def start_login(self, *, username: str) -> ClientWebAuthStartResult:
        normalized_username = normalize_username(username)
        user = self.db.client_web_auth.get_user_by_username(normalized_username)
        if user is None:
            raise ClientWebAuthUnauthorizedError("User is not registered in Telegram bot")
        credential = self.db.client_web_auth.get_credential(int(user["telegram_user_id"]))
        if credential and credential.get("password_hash"):
            return ClientWebAuthStartResult(
                challenge_id=None,
                requires_otp=False,
                requires_password_setup=False,
                requires_password=True,
            )

        challenge = self._create_and_send_otp_challenge(user)
        return ClientWebAuthStartResult(
            challenge_id=int(challenge["id"]),
            requires_otp=True,
            requires_password_setup=False,
            requires_password=False,
        )

    def _create_and_send_otp_challenge(self, user: dict[str, Any]) -> dict[str, Any]:
        current_time = self.time_service.now()
        otp_code = f"{secrets.randbelow(1_000_000):06d}"
        challenge = self.db.client_web_auth.create_otp_challenge(
            telegram_user_id=int(user["telegram_user_id"]),
            otp_hash=hash_secret(otp_code),
            expires=current_time + timedelta(minutes=self.db.settings.app_admin_otp_ttl_minutes),
            sent_chat_id=user.get("chat_id"),
            current_time=current_time,
        )
        message_id = self._send_otp_message(user, otp_code, current_time=current_time)
        if message_id is not None:
            self.db.client_web_auth.save_otp_message_id(int(challenge["id"]), message_id, current_time=current_time)
        return challenge

    def verify_password(
        self,
        *,
        username: str,
        password: str,
    ) -> ClientWebAuthStartResult:
        user = self.db.client_web_auth.get_user_by_username(normalize_username(username))
        credential = self.db.client_web_auth.get_credential(int(user["telegram_user_id"])) if user is not None else None
        if user is None or not credential or not verify_secret(password, credential.get("password_hash")):
            raise ClientWebAuthUnauthorizedError("Invalid credentials")
        challenge = self._create_and_send_otp_challenge(user)
        return ClientWebAuthStartResult(
            challenge_id=int(challenge["id"]),
            requires_otp=True,
            requires_password_setup=False,
            requires_password=False,
        )

    def verify_otp(
        self,
        *,
        challenge_id: int,
        otp: str,
        request_context: WebRequestContext | None,
    ) -> ClientWebAuthResult:
        current_time = self.time_service.now()
        challenge = self.db.client_web_auth.get_otp_challenge(challenge_id)
        if challenge is None or challenge.get("consumed") is not None or challenge["expires"] <= current_time:
            raise ClientWebAuthUnauthorizedError("Invalid OTP")
        if int(challenge.get("attempts_count") or 0) >= 5:
            raise ClientWebAuthRateLimitError("Too many attempts")
        if not verify_secret(normalize_otp(otp), challenge["otp_hash"]):
            self.db.client_web_auth.increment_otp_attempts(challenge_id, current_time=current_time)
            raise ClientWebAuthUnauthorizedError("Invalid OTP")

        user = self.db.client_web_auth.get_user_by_id(int(challenge["telegram_user_id"]))
        if user is None:
            raise ClientWebAuthUnauthorizedError("Invalid credentials")
        self.db.client_web_auth.consume_otp_challenge(challenge_id, current_time=current_time)
        token = self.session_service.create_session_token(user, request_context, current_time=current_time)
        self.session_service.log_login_event(
            request_context,
            telegram_user_id=int(user["telegram_user_id"]),
            username_attempted=user.get("username"),
            event_type="otp_login",
            current_time=current_time,
        )
        self._cleanup_otp_message(challenge, user, current_time=current_time)
        return ClientWebAuthResult(session_token=token, user=self.session_service.with_auth_flags(user))

    def update_password(
        self,
        *,
        user: dict[str, Any],
        current_password: str | None,
        password: str,
    ) -> dict[str, Any]:
        current_time = self.time_service.now()
        credential = self.db.client_web_auth.get_credential(int(user["telegram_user_id"]))
        if credential and credential.get("password_hash"):
            if not current_password or not verify_secret(current_password, credential["password_hash"]):
                raise ClientWebAuthUnauthorizedError("Invalid current password")
        try:
            validate_password_complexity(password)
        except ValueError as error:
            raise ClientWebAuthValidationError(str(error)) from error

        self.db.client_web_auth.set_password_hash(int(user["telegram_user_id"]), hash_secret(password), current_time=current_time)
        fresh_user = self.db.client_web_auth.get_user_by_id(int(user["telegram_user_id"])) or user
        return self.session_service.with_auth_flags(fresh_user)

    def mark_password_prompted(self, *, user: dict[str, Any]) -> dict[str, Any]:
        self.db.client_web_auth.mark_password_prompted(
            int(user["telegram_user_id"]),
            current_time=self.time_service.now(),
        )
        fresh_user = self.db.client_web_auth.get_user_by_id(int(user["telegram_user_id"])) or {
            **user,
            "client_web_password_prompted": True,
        }
        return self.session_service.with_auth_flags(fresh_user)

    def consume_magic_link(self, *, token: str, request_context: WebRequestContext | None) -> ClientWebAuthResult:
        current_time = self.time_service.now()
        hash_token = hash_token_for_lookup(str(token or "").strip())
        magic_link = self.db.client_web_auth.get_active_magic_link_by_token_hash(
            hash_token,
            current_time=current_time,
        )
        if magic_link is None:
            renewed = self._renew_inactive_magic_link(token_hash=hash_token)
            if renewed:
                raise ClientWebAuthUnauthorizedError("Посилання вже недійсне. Я надіслав нове посилання в Telegram.")
            raise ClientWebAuthUnauthorizedError("Invalid magic link")
        user = self.db.client_web_auth.get_user_by_id(int(magic_link["telegram_user_id"]))
        if user is None:
            raise ClientWebAuthUnauthorizedError("Invalid credentials")
        session_token = self.session_service.create_session_token(user, request_context, current_time=current_time)
        self.db.client_web_auth.consume_magic_link(int(magic_link["id"]), current_time=current_time)
        self.session_service.log_login_event(
            request_context,
            telegram_user_id=int(user["telegram_user_id"]),
            username_attempted=user.get("username"),
            event_type="magic_login",
            current_time=current_time,
            details={"target_path": str(magic_link["target_path"])},
        )
        self._send_success_notice(user, current_time=current_time)
        return ClientWebAuthResult(
            session_token=session_token,
            user=self.session_service.with_auth_flags(user),
            target_path=str(magic_link["target_path"]),
        )

    def create_magic_link_url(self, *, telegram_user_id: int, target_path: str = "/settings") -> str:
        user = self.db.client_web_auth.get_user_by_id(telegram_user_id)
        if user is None:
            raise ClientWebAuthNotFoundError("User not found")
        current_time = self.time_service.now()
        token = secrets.token_urlsafe(48)
        normalized_target = self._normalize_magic_target_path(target_path)
        self.db.client_web_auth.create_magic_link(
            telegram_user_id=telegram_user_id,
            token_hash=hash_token_for_lookup(token),
            target_path=normalized_target,
            expires=current_time + timedelta(minutes=self.db.settings.app_admin_magic_link_ttl_minutes),
            current_time=current_time,
        )
        query = urlencode({"token": token, "next": normalized_target})
        return f"{self.db.settings.app_web_base_url.rstrip('/')}/auth/magic?{query}"

    def _normalize_magic_target_path(self, target_path: str) -> str:
        return target_path if target_path in CLIENT_WEB_MAGIC_TARGET_PATHS else "/settings"

    def _renew_inactive_magic_link(self, *, token_hash: str) -> bool:
        lookup = getattr(self.db.client_web_auth, "get_magic_link_by_token_hash", None)
        if lookup is None:
            return False
        inactive_link = lookup(token_hash)
        if inactive_link is None:
            return False
        user = self.db.client_web_auth.get_user_by_id(int(inactive_link["telegram_user_id"]))
        if user is None:
            return False
        renewed_url = self.create_magic_link_url(
            telegram_user_id=int(inactive_link["telegram_user_id"]),
            target_path=str(inactive_link["target_path"]),
        )
        self._send_magic_link_message(
            user,
            renewed_url,
            text_key="settings_web_link_renewed_text",
        )
        return True

    def get_session_user(self, token: str | None, *, request_context: WebRequestContext | None) -> dict[str, Any]:
        return self.session_service.get_session_user(token, request_context=request_context)

    def logout(self, token: str | None) -> None:
        self.session_service.logout(token)

    def _send_otp_message(self, user: dict[str, Any], otp_code: str, *, current_time: datetime | None = None) -> int | None:
        chat_id = user.get("chat_id")
        if not chat_id:
            return None
        current_time = current_time or self.time_service.now()
        return send_tracked_transient_message(
            db=self.db,
            telegram_gateway=self.telegram_gateway,
            telegram_user_id=int(user["telegram_user_id"]),
            chat_id=int(chat_id),
            text=f"OTP код для входа в CronoLex: {format_otp(otp_code)}",
            screen_id=AUTH_OTP_SCREEN_ID,
            current_time=current_time,
            ttl_seconds=max(int(self.db.settings.app_admin_otp_ttl_minutes), 1) * 60,
            disable_notification=False,
            ignore_errors=False,
        )

    def _cleanup_otp_message(self, challenge: dict[str, Any], user: dict[str, Any], *, current_time: datetime | None = None) -> None:
        chat_id = challenge.get("sent_chat_id") or user.get("chat_id")
        message_id = challenge.get("sent_message_id")
        if chat_id and message_id:
            self.telegram_gateway.delete_message(chat_id=chat_id, message_id=message_id, ignore_errors=True)
        self._send_success_notice(user, current_time=current_time or self.time_service.now())

    def _send_success_notice(self, user: dict[str, Any], *, current_time: datetime) -> None:
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

    def send_login_menu(self, user: dict[str, Any], menu_text: str, reply_markup: dict[str, Any] | None) -> None:
        chat_id = user.get("chat_id")
        if not chat_id:
            return
        self.telegram_gateway.send_message(
            chat_id=int(chat_id),
            text=menu_text,
            reply_markup=reply_markup,
            disable_notification=True,
            ignore_errors=True,
        )

    def _send_magic_link_message(
        self,
        user: dict[str, Any],
        url: str,
        *,
        text_key: str,
    ) -> None:
        chat_id = user.get("chat_id")
        if not chat_id:
            return
        locale = resolve_user_locale(user)
        self.telegram_gateway.send_message(
            chat_id=int(chat_id),
            text=translate(
                locale,
                text_key,
                ttl_minutes=self.db.settings.app_admin_magic_link_ttl_minutes,
            ),
            reply_markup={
                "inline_keyboard": [
                    [{"text": translate(locale, "settings_web_link_button"), "url": url}],
                    [{"text": translate(locale, "menu_back_to_menu"), "callback_data": "m:menu"}],
                ]
            },
            ignore_errors=True,
        )
