from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol


class AdminAuthSettingsPort(Protocol):
    app_admin_dev_login_enabled: bool
    app_env: str
    app_admin_otp_ttl_minutes: int
    app_admin_magic_link_ttl_minutes: int
    app_admin_session_hours: int
    app_web_base_url: str


class AdminAuthRepositoryPort(Protocol):
    def ensure_dev_admin_user(self, *, current_time: datetime) -> dict[str, Any]: ...

    def get_credential(self, telegram_user_id: int) -> dict[str, Any] | None: ...

    def set_password_hash(self, telegram_user_id: int, password_hash: str, *, current_time: datetime) -> None: ...

    def create_otp_challenge(
        self,
        *,
        telegram_user_id: int,
        otp_hash: str,
        expires: datetime,
        previous_screen_id: str | None,
        sent_chat_id: int | None,
        current_time: datetime,
    ) -> dict[str, Any]: ...

    def save_otp_message_id(self, challenge_id: int, message_id: int, *, current_time: datetime) -> None: ...

    def get_otp_challenge(self, challenge_id: int) -> dict[str, Any] | None: ...

    def increment_otp_attempts(self, challenge_id: int, *, current_time: datetime) -> None: ...

    def consume_otp_challenge(self, challenge_id: int, *, current_time: datetime) -> None: ...

    def create_magic_link(
        self,
        *,
        telegram_user_id: int,
        token_hash: str,
        target_path: str,
        expires: datetime,
        current_time: datetime,
    ) -> dict[str, Any]: ...

    def get_active_magic_link_by_token_hash(self, token_hash: str, *, current_time: datetime) -> dict[str, Any] | None: ...

    def consume_magic_link(self, magic_link_id: int, *, current_time: datetime) -> None: ...

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

    def get_active_session_by_token_hash(self, *, token_hash_matcher: Any, current_time: datetime) -> dict[str, Any] | None: ...

    def touch_session(self, session_id: int, *, current_time: datetime) -> None: ...

    def revoke_session(self, session_id: int, *, current_time: datetime) -> None: ...

    def revoke_session_by_token_match(self, *, token_hash_matcher: Any, current_time: datetime) -> None: ...

    def mark_password_prompted(self, telegram_user_id: int, *, current_time: datetime) -> None: ...


class AdminAuthUserRepositoryPort(Protocol):
    def get_login_by_username(self, username: str) -> dict[str, Any] | None: ...

    def get_by_id(self, user_id: int) -> dict[str, Any] | None: ...


class AdminAuthWebLoginHistoryPort(Protocol):
    def create(self, **kwargs: Any) -> dict[str, Any]: ...


class AdminAuthBotMessageLogPort(Protocol):
    def get_latest_active_screen(self, telegram_user_id: int) -> dict[str, Any] | None: ...

    def create(
        self,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
        screen_id: str,
        delete_after: datetime,
        current_time: datetime,
    ) -> dict[str, Any]: ...


class AdminAuthDatabasePort(Protocol):
    settings: AdminAuthSettingsPort
    admin_auth: AdminAuthRepositoryPort
    admin_users: AdminAuthUserRepositoryPort
    web_login_history: AdminAuthWebLoginHistoryPort
    bot_message_logs: AdminAuthBotMessageLogPort
    acl_permissions: Any
