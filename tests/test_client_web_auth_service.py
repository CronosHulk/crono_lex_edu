from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.application.client_web.auth_errors import (
    ClientWebAuthNotFoundError,
    ClientWebAuthUnauthorizedError,
    ClientWebAuthValidationError,
)
from app.application.client_web.auth_service import ClientWebAuthService
from app.auth.secrets import hash_token_for_lookup
from app.reference.teacher_referrals import encode_teacher_referral_payload


class FixedTimeService:
    def __init__(self, current_time: datetime) -> None:
        self.current_time = current_time

    def now(self) -> datetime:
        return self.current_time


class FakeClientWebAuthRepository:
    def __init__(self, current_time: datetime) -> None:
        self.user = {
            "telegram_user_id": 1,
            "user_id": "11111111-1111-4111-8111-111111111111",
            "username": "cronos",
            "chat_id": 55,
            "interface_locale": "uk",
            "language_code": "uk",
            "learning_role": "student",
        }
        self.magic_links = [
            {
                "id": 7,
                "telegram_user_id": 1,
                "token_hash": hash_token_for_lookup("old-token"),
                "target_path": "/settings",
                "expires": current_time - timedelta(minutes=1),
                "created": current_time - timedelta(minutes=20),
                "updated": current_time - timedelta(minutes=20),
                "consumed": None,
            }
        ]
        self.sessions: list[dict[str, object]] = []
        self.credentials: dict[int, dict[str, object]] = {}
        self.otp_challenges: list[dict[str, object]] = []

    def get_active_magic_link_by_token_hash(self, token_hash: str, *, current_time: datetime) -> dict | None:
        for row in self.magic_links:
            if row["token_hash"] == token_hash and row["expires"] > current_time and row.get("consumed") is None:
                return dict(row)
        return None

    def get_magic_link_by_token_hash(self, token_hash: str) -> dict | None:
        for row in self.magic_links:
            if row["token_hash"] == token_hash:
                return dict(row)
        return None

    def get_user_by_id(self, telegram_user_id: int) -> dict | None:
        return dict(self.user) if telegram_user_id == self.user["telegram_user_id"] else None

    def get_user_by_username(self, username: str) -> dict | None:
        return dict(self.user) if username == self.user["username"] else None

    def create_magic_link(self, **kwargs) -> dict:
        row = {"id": len(self.magic_links) + 1, "consumed": None, **kwargs}
        self.magic_links.append(row)
        return dict(row)

    def create_session(self, **kwargs) -> dict:
        row = {"id": len(self.sessions) + 1, **kwargs}
        self.sessions.append(row)
        return dict(row)

    def create_otp_challenge(self, **kwargs) -> dict:
        row = {"id": len(self.otp_challenges) + 1, "attempts_count": 0, "consumed": None, "sent_message_id": None, **kwargs}
        self.otp_challenges.append(row)
        return dict(row)

    def save_otp_message_id(self, challenge_id: int, message_id: int, *, current_time: datetime) -> None:
        self.otp_challenges[challenge_id - 1]["sent_message_id"] = message_id

    def get_otp_challenge(self, challenge_id: int) -> dict | None:
        if not 0 < challenge_id <= len(self.otp_challenges):
            return None
        return dict(self.otp_challenges[challenge_id - 1])

    def consume_otp_challenge(self, challenge_id: int, *, current_time: datetime) -> None:
        self.otp_challenges[challenge_id - 1]["consumed"] = current_time

    def increment_otp_attempts(self, challenge_id: int, *, current_time: datetime) -> None:
        self.otp_challenges[challenge_id - 1]["attempts_count"] += 1

    def consume_magic_link(self, magic_link_id: int, *, current_time: datetime) -> None:
        for row in self.magic_links:
            if row["id"] == magic_link_id:
                row["consumed"] = current_time

    def get_credential(self, telegram_user_id: int) -> dict | None:
        return self.credentials.get(telegram_user_id)

    def set_password_hash(self, telegram_user_id: int, password_hash: str, *, current_time: datetime) -> None:
        self.credentials[telegram_user_id] = {"password_hash": password_hash}

    def mark_password_prompted(self, telegram_user_id: int, *, current_time: datetime) -> None:
        self.user["client_web_password_prompted"] = True


class FakeTelegramGateway:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []
        self.deleted_messages: list[dict[str, object]] = []

    def send_message(self, **kwargs) -> int:
        self.messages.append(kwargs)
        return len(self.messages)

    def delete_message(self, **kwargs) -> bool:
        self.deleted_messages.append(kwargs)
        return True


class FakeWebLoginHistoryRepository:
    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []

    def create(self, **kwargs) -> dict[str, object]:
        row = {"id": len(self.rows) + 1, **kwargs}
        self.rows.append(row)
        return dict(row)

    def __eq__(self, other: object) -> bool:
        return self.rows == other


class FakeBotMessageLogRepository:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def create(self, telegram_user_id, chat_id, message_id, screen_id, delete_after, current_time) -> dict[str, object]:
        row = {
            "telegram_user_id": telegram_user_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "screen_id": screen_id,
            "delete_after": delete_after,
            "current_time": current_time,
        }
        self.rows.append(row)
        return {"id": len(self.rows), **row}


class FakeAdminAuthRepository:
    def __init__(self, restores: list[dict[str, object]]) -> None:
        self.restores = restores

    def schedule_bot_restore(self, **kwargs) -> dict[str, object]:
        self.restores.append(kwargs)
        return {"id": len(self.restores), **kwargs}


class FakeClientWebDb:
    def __init__(self, repository: FakeClientWebAuthRepository) -> None:
        self.client_web_auth = repository
        self.settings = SimpleNamespace(
            app_web_base_url="https://cronolex.local",
            app_admin_magic_link_ttl_minutes=5,
            app_admin_otp_ttl_minutes=5,
            app_admin_session_hours=12,
            app_bot_username="",
        )
        self.created_bot_messages: list[dict[str, object]] = []
        self.restores: list[dict[str, object]] = []
        self.web_login_history = FakeWebLoginHistoryRepository()
        self.bot_message_logs = FakeBotMessageLogRepository(self.created_bot_messages)
        self.admin_auth = FakeAdminAuthRepository(self.restores)


def make_service(current_time: datetime) -> tuple[ClientWebAuthService, FakeClientWebAuthRepository, FakeTelegramGateway]:
    repository = FakeClientWebAuthRepository(current_time)
    db = FakeClientWebDb(repository)
    gateway = FakeTelegramGateway()
    service = ClientWebAuthService(db, FixedTimeService(current_time), gateway)
    return service, repository, gateway


def make_request_context() -> SimpleNamespace:
    return SimpleNamespace(
        api_origin="https://app.cronolex.local",
        api_path="/api/v1/client-web/auth/verify-otp",
        client_ip="203.0.113.10",
        user_agent="pytest-browser",
        device_fingerprint_hash="device-hash",
    )


def test_expired_client_web_magic_link_sends_renewed_link_to_telegram(monkeypatch) -> None:
    current_time = datetime(2026, 4, 28, 13, 0, 0)
    service, repository, gateway = make_service(current_time)
    monkeypatch.setattr("app.application.client_web.auth_service.secrets.token_urlsafe", lambda size: "new-token")

    with pytest.raises(ClientWebAuthUnauthorizedError) as error:
        service.consume_magic_link(token="old-token", request_context=None)

    assert "нове посилання" in error.value.detail
    assert repository.magic_links[-1]["token_hash"] == hash_token_for_lookup("new-token")
    assert gateway.messages[0]["chat_id"] == 55
    assert "5 хв" in gateway.messages[0]["text"]
    assert gateway.messages[0]["reply_markup"]["inline_keyboard"][0][0]["url"].endswith(
        "/auth/magic?token=new-token&next=%2Fsettings"
    )
    assert gateway.messages[0]["reply_markup"]["inline_keyboard"][1][0]["callback_data"] == "m:menu"


def test_client_web_magic_link_keeps_requested_allowed_target(monkeypatch) -> None:
    current_time = datetime(2026, 4, 28, 13, 0, 0)
    service, repository, _ = make_service(current_time)
    monkeypatch.setattr("app.application.client_web.auth_service.secrets.token_urlsafe", lambda size: "settings-token")

    url = service.create_magic_link_url(telegram_user_id=1, target_path="/settings")

    assert url.endswith("/auth/magic?token=settings-token&next=%2Fsettings")
    assert repository.magic_links[-1]["target_path"] == "/settings"


def test_client_web_magic_link_rejects_unknown_target_path(monkeypatch) -> None:
    current_time = datetime(2026, 4, 28, 13, 0, 0)
    service, repository, _ = make_service(current_time)
    monkeypatch.setattr("app.application.client_web.auth_service.secrets.token_urlsafe", lambda size: "safe-token")

    url = service.create_magic_link_url(telegram_user_id=1, target_path="https://evil.test")

    assert url.endswith("/auth/magic?token=safe-token&next=%2Fsettings")
    assert repository.magic_links[-1]["target_path"] == "/settings"


def test_client_web_magic_link_rejects_retired_homework_target(monkeypatch) -> None:
    current_time = datetime(2026, 4, 28, 13, 0, 0)
    service, repository, _ = make_service(current_time)
    monkeypatch.setattr("app.application.client_web.auth_service.secrets.token_urlsafe", lambda size: "safe-token")

    url = service.create_magic_link_url(telegram_user_id=1, target_path="/homework")

    assert url.endswith("/auth/magic?token=safe-token&next=%2Fsettings")
    assert repository.magic_links[-1]["target_path"] == "/settings"


def test_login_menu_message_uses_menu_markup_without_extra_success_text() -> None:
    current_time = datetime(2026, 4, 28, 13, 0, 0)
    service, _, gateway = make_service(current_time)

    service.send_login_menu(
        {
            "telegram_user_id": 1,
            "chat_id": 55,
            "interface_locale": "uk",
        },
        "Головне меню",
        {"inline_keyboard": [[{"text": "Почати", "callback_data": "m:s"}]]},
    )

    assert gateway.messages[0]["text"] == "Головне меню"
    assert gateway.messages[0]["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == "m:s"
    assert gateway.messages[0]["disable_notification"] is True


def test_start_login_without_password_sends_otp_without_requiring_password_setup(monkeypatch) -> None:
    current_time = datetime(2026, 4, 28, 13, 0, 0)
    service, repository, gateway = make_service(current_time)
    monkeypatch.setattr("app.application.client_web.auth_service.secrets.randbelow", lambda limit: 123456)

    result = service.start_login(username="cronos")

    assert result.challenge_id == 1
    assert result.requires_otp is True
    assert result.requires_password is False
    assert result.requires_password_setup is False
    assert repository.otp_challenges[0]["telegram_user_id"] == 1
    assert gateway.messages[0]["text"] == "OTP код для входа в CronoLex: 123 456"
    assert gateway.messages[0].get("disable_notification", False) is False
    assert service.db.created_bot_messages == [
        {
            "telegram_user_id": 1,
            "chat_id": 55,
            "message_id": 1,
            "screen_id": "auth:otp",
            "delete_after": current_time + timedelta(minutes=5),
            "current_time": current_time,
        }
    ]


def test_verify_otp_deletes_otp_message_and_sends_transient_success_without_menu_restore(monkeypatch) -> None:
    current_time = datetime(2026, 4, 28, 13, 0, 0)
    service, repository, gateway = make_service(current_time)
    monkeypatch.setattr("app.application.client_web.auth_service.secrets.randbelow", lambda limit: 123456)

    service.start_login(username="cronos")
    request_context = make_request_context()
    result = service.verify_otp(challenge_id=1, otp="123456", request_context=request_context)

    assert result.user["telegram_user_id"] == 1
    assert repository.otp_challenges[0]["consumed"] == current_time
    assert service.db.web_login_history == [
        {
            "id": 1,
            "telegram_user_id": 1,
            "username_attempted": "cronos",
            "interface_context": "client_web",
            "event_type": "otp_login",
            "result": "success",
            "api_origin": "https://app.cronolex.local",
            "api_path": "/api/v1/client-web/auth/verify-otp",
            "client_ip": "203.0.113.10",
            "user_agent": "pytest-browser",
            "device_fingerprint_hash": "device-hash",
            "details_json": {},
            "current_time": current_time,
        }
    ]
    assert gateway.deleted_messages == [{"chat_id": 55, "message_id": 1, "ignore_errors": True}]
    assert [message["text"] for message in gateway.messages] == [
        "OTP код для входа в CronoLex: 123 456",
        "Вхід виконано успішно",
    ]
    assert gateway.messages[-1]["disable_notification"] is False
    assert service.db.created_bot_messages[-1] == {
        "telegram_user_id": 1,
        "chat_id": 55,
        "message_id": 2,
        "screen_id": "auth:login_success",
        "delete_after": current_time + timedelta(seconds=5),
        "current_time": current_time,
    }
    assert service.db.restores == []


def test_consume_magic_link_writes_client_web_login_history(monkeypatch) -> None:
    current_time = datetime(2026, 4, 28, 13, 0, 0)
    service, repository, _ = make_service(current_time)
    repository.magic_links.append(
        {
            "id": 8,
            "telegram_user_id": 1,
            "token_hash": hash_token_for_lookup("active-token"),
            "target_path": "/settings",
            "expires": current_time + timedelta(minutes=5),
            "created": current_time,
            "updated": current_time,
            "consumed": None,
        }
    )
    monkeypatch.setattr("app.application.client_web.auth_service.secrets.token_urlsafe", lambda size: "session-token")

    request_context = make_request_context()
    request_context.api_path = "/api/v1/client-web/auth/magic"
    result = service.consume_magic_link(token="active-token", request_context=request_context)

    assert result.session_token == "session-token"
    assert result.target_path == "/settings"
    assert repository.magic_links[-1]["consumed"] == current_time
    assert service.db.web_login_history == [
        {
            "id": 1,
            "telegram_user_id": 1,
            "username_attempted": "cronos",
            "interface_context": "client_web",
            "event_type": "magic_login",
            "result": "success",
            "api_origin": "https://app.cronolex.local",
            "api_path": "/api/v1/client-web/auth/magic",
            "client_ip": "203.0.113.10",
            "user_agent": "pytest-browser",
            "device_fingerprint_hash": "device-hash",
            "details_json": {"target_path": "/settings"},
            "current_time": current_time,
        }
    ]


def test_password_prompt_flag_is_cleared_after_first_authenticated_prompt() -> None:
    current_time = datetime(2026, 4, 28, 13, 0, 0)
    service, repository, _ = make_service(current_time)

    first_user_payload = service.session_service.with_auth_flags(repository.user)
    marked_user_payload = service.mark_password_prompted(user=first_user_payload)

    assert first_user_payload["requires_password_setup"] is True
    assert marked_user_payload["requires_password_setup"] is False
    assert repository.user["client_web_password_prompted"] is True


def test_teacher_session_user_contains_referral_url() -> None:
    current_time = datetime(2026, 4, 28, 13, 0, 0)
    service, repository, _ = make_service(current_time)
    service.db.settings.app_bot_username = "CronoLexBot"
    repository.user = {
        **repository.user,
        "learning_role": "teacher",
    }

    payload = service.session_service.with_auth_flags(repository.user)

    assert payload["teacher_referral_url"] == (
        "https://t.me/CronoLexBot?start="
        f"{encode_teacher_referral_payload('11111111-1111-4111-8111-111111111111')}"
    )


def test_password_update_requires_current_password_when_password_exists() -> None:
    current_time = datetime(2026, 4, 28, 13, 0, 0)
    service, repository, _ = make_service(current_time)
    service.update_password(user=repository.user, current_password=None, password="Pass1234")

    with pytest.raises(ClientWebAuthUnauthorizedError) as error:
        service.update_password(user=repository.user, current_password="bad", password="Next1234")

    assert error.value.detail == "Invalid current password"


def test_password_update_raises_validation_error_for_weak_password() -> None:
    current_time = datetime(2026, 4, 28, 13, 0, 0)
    service, repository, _ = make_service(current_time)

    with pytest.raises(ClientWebAuthValidationError) as error:
        service.update_password(user=repository.user, current_password=None, password="short")

    assert "at least" in error.value.detail


def test_create_magic_link_raises_not_found_error_for_missing_user() -> None:
    current_time = datetime(2026, 4, 28, 13, 0, 0)
    service, _, _ = make_service(current_time)

    with pytest.raises(ClientWebAuthNotFoundError) as error:
        service.create_magic_link_url(telegram_user_id=999)

    assert error.value.detail == "User not found"
