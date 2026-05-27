from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.application.client.bootstrap_service import ClientBootstrapService
from app.contracts import ScreenModel, TelegramUserContext
from app.reference.teacher_referrals import encode_teacher_referral_payload


class FakeBootstrapDb:
    def __init__(self) -> None:
        self.upserted_users: list[dict[str, Any]] = []
        self.user_events: list[dict[str, Any]] = []
        self.error_logs: list[dict[str, Any]] = []
        self.profiles_by_uuid: dict[str, dict[str, Any]] = {}
        self.teacher_student_links: list[dict[str, Any]] = []
        self.default_user_uuid = "22222222-2222-4222-8222-222222222222"
        self.now = datetime(2026, 5, 3, 12, 0, tzinfo=UTC)

    def upsert_user(self, payload: dict[str, Any]) -> None:
        payload = {
            "user_id": self.default_user_uuid,
            "user_uuid": self.default_user_uuid,
            "learning_role": "student",
            **payload,
        }
        self.upserted_users.append(payload)
        self.profiles_by_uuid[payload["user_id"]] = {
            "telegram_user_id": payload["telegram_user_id"],
            "interface_locale": "uk",
            **payload,
        }

    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        for user in reversed(self.upserted_users):
            if user["telegram_user_id"] == telegram_user_id:
                return {"telegram_user_id": telegram_user_id, "interface_locale": "uk", **user}
        return None

    def get_profile_by_user_uuid(self, user_uuid: str) -> dict[str, Any] | None:
        return self.profiles_by_uuid.get(user_uuid)

    def save_user_event(
        self,
        *,
        telegram_user_id: int,
        event_type: str,
        raw_update_json: dict[str, Any],
        message_text: str | None,
    ) -> None:
        self.user_events.append(
            {
                "telegram_user_id": telegram_user_id,
                "event_type": event_type,
                "raw_update_json": raw_update_json,
                "message_text": message_text,
            }
        )

    def log_error(self, level: str, text_parts: list[str]) -> None:
        self.error_logs.append({"level": level, "text_parts": text_parts})

    def create(
        self,
        level: str,
        text: str | list[str],
        *,
        context_json: dict[str, Any] | None = None,
    ) -> None:
        if level.lower() not in {"warn", "debug", "fatal"}:
            raise ValueError(f"Unsupported error level: {level}")
        self.error_logs.append({"level": level, "text_parts": text, "context_json": context_json})

    def assign_student_to_teacher(
        self,
        *,
        teacher_user_id: str,
        student_user_id: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        payload = {
            "teacher_user_id": teacher_user_id,
            "student_user_id": student_user_id,
            "current_time": current_time,
        }
        self.teacher_student_links.append(payload)
        return payload

def build_user(language_code: str | None = "uk") -> TelegramUserContext:
    return TelegramUserContext(
        telegram_user_id=42,
        first_name="Олена",
        username="olena",
        language_code=language_code,
        raw_telegram_json='{"id":42}',
    )


def build_service(db: FakeBootstrapDb | None = None) -> tuple[ClientBootstrapService, FakeBootstrapDb]:
    db = db or FakeBootstrapDb()
    service = ClientBootstrapService(
        db,
        db,
        build_start_screen=lambda telegram_user_id, locale: ScreenModel(
            screen_id="start",
            text=f"{telegram_user_id}:{locale}",
        ),
        teacher_student_links=db,
        current_time=lambda: db.now,
    )
    return service, db


def test_bootstrap_upserts_user_saves_command_event_and_returns_start_screen() -> None:
    service, db = build_service()

    screen = service.bootstrap(build_user(language_code="en-US"), "/start")

    assert screen.text == "42:uk"
    assert db.upserted_users[0]["telegram_user_id"] == 42
    assert db.upserted_users[0]["acl_group_id"] is None
    assert db.user_events == [
        {
            "telegram_user_id": 42,
            "event_type": "command_start",
            "raw_update_json": build_user(language_code="en-US").model_dump(mode="json"),
            "message_text": "/start",
        }
    ]


def test_bootstrap_saves_user_and_prompts_when_telegram_username_is_missing() -> None:
    service, db = build_service()
    user = build_user()
    user = user.model_copy(update={"username": None})

    screen = service.bootstrap(user, "/start")

    assert screen.screen_id == "start:missing_username"
    assert "Telegram username" in screen.text
    assert "/start" in screen.text
    assert db.upserted_users[0]["telegram_user_id"] == 42
    assert db.upserted_users[0]["username"] is None
    assert db.user_events[0]["event_type"] == "command_start"
    assert db.error_logs == [
        {
            "level": "warn",
            "text_parts": "Telegram /start received from user without username.",
            "context_json": {
                "route": "bootstrap",
                "screen_id": "start:missing_username",
                "telegram_user_id": 42,
                "chat_id": None,
                "first_name": "Олена",
                "last_name": None,
                "language_code": "uk",
            },
        }
    ]


def test_build_unexpected_error_screen_uses_detected_locale() -> None:
    service, _ = build_service()

    screen = service.build_unexpected_error_screen(build_user(language_code="uk"))

    assert screen.screen_id == "transient:error"
    assert "Перепрошуємо, сталася непередбачена ситуація." in screen.text
    assert screen.metadata["next_action"] == "m:menu"


def test_log_unexpected_error_writes_fatal_context() -> None:
    service, db = build_service()

    service.log_unexpected_error(
        route="action:m:test",
        user=build_user(),
        error=RuntimeError("boom"),
        details="traceback details",
    )

    assert db.error_logs == [
        {
            "level": "fatal",
            "text_parts": [
                "route=action:m:test",
                "telegram_user_id=42",
                "error_type=RuntimeError",
                "error_text=boom",
                "traceback details",
            ],
            "context_json": None,
        }
    ]


def test_build_user_payload_preserves_user_fields_and_adds_acl_group() -> None:
    service, _ = build_service()

    payload = service.build_user_payload(build_user(language_code=None))

    assert payload["telegram_user_id"] == 42
    assert payload["acl_group_id"] is None


def test_bootstrap_assigns_student_to_teacher_from_strict_referral_payload() -> None:
    db = FakeBootstrapDb()
    teacher_uuid = "11111111-1111-4111-8111-111111111111"
    db.profiles_by_uuid[teacher_uuid] = {
        "user_id": teacher_uuid,
        "learning_role": "teacher",
        "interface_locale": "uk",
    }
    service, db = build_service(db)

    service.bootstrap(build_user(), f"/start {encode_teacher_referral_payload(teacher_uuid)}")

    assert db.teacher_student_links == [
        {
            "teacher_user_id": teacher_uuid,
            "student_user_id": db.default_user_uuid,
            "current_time": db.now,
        }
    ]
    assert db.upserted_users[0]["user_id"] == db.default_user_uuid


def test_bootstrap_ignores_unknown_start_payload_format() -> None:
    db = FakeBootstrapDb()
    teacher_uuid = "11111111-1111-4111-8111-111111111111"
    db.profiles_by_uuid[teacher_uuid] = {
        "user_id": teacher_uuid,
        "learning_role": "teacher",
        "interface_locale": "uk",
    }
    service, db = build_service(db)

    service.bootstrap(build_user(), f"/start teacher={teacher_uuid}")

    assert db.teacher_student_links == []
