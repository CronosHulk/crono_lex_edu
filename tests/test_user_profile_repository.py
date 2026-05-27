from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from uuid import uuid4

import pytest

from app.data_access.user_profiles import UserProfileRepository, user_profile_to_dict
from app.models import (
    LanguageLevel,
    User,
    UserEvent,
    UserLearningSettings,
    UserReminderSchedule,
    UserSubscription,
)


class FakeResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)

    def first(self):
        return self.rows[0] if self.rows else None


class FakeSession:
    def __init__(self, *, row_by_id=None, execute_rows=None, scalar_values=None, scalars_rows=None) -> None:
        self.row_by_id = row_by_id or {}
        self.execute_rows = list(execute_rows or [])
        self.scalar_values = list(scalar_values or [])
        self.scalars_rows = list(scalars_rows or [])
        self.added = []

    def get(self, model, primary_key):
        return self.row_by_id.get(primary_key)

    def execute(self, statement):
        return FakeResult(self.execute_rows.pop(0) if self.execute_rows else [])

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def scalars(self, statement):
        if self.scalars_rows and isinstance(self.scalars_rows[0], list):
            return FakeResult(self.scalars_rows.pop(0))
        return FakeResult(self.scalars_rows)

    def add(self, row) -> None:
        self.added.append(row)


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def make_user(**overrides) -> User:
    now = datetime(2026, 4, 6, 10, 0, 0)
    values = {
        "telegram_user_id": 42,
        "uuid": uuid4(),
        "first_name": "Ada",
        "last_name": "Lovelace",
        "username": "ada",
        "language_code": "uk",
        "interface_locale": "uk",
        "is_premium": True,
        "status": "active",
        "chat_id": 1001,
        "chat_type": "private",
        "created": now,
        "updated": now,
    }
    values.update(overrides)
    return User(**values)


def make_level(**overrides) -> LanguageLevel:
    values = {"id": 2, "title": "A2", "description": "basic"}
    values.update(overrides)
    return LanguageLevel(**values)


def make_settings(**overrides) -> UserLearningSettings:
    values = {
        "user_uuid": uuid4(),
        "words_per_session": 15,
        "daily_reminder_hour": 20,
        "preferred_gender": "feminine",
        "import_google_doc_id": "doc",
        "is_import_google_doc_auto_sync_enabled": True,
        "import_google_doc_retry_count": 3,
    }
    values.update(overrides)
    return UserLearningSettings(**values)


def test_user_profile_to_dict_uses_defaults_and_optional_reminder_weekdays() -> None:
    payload = user_profile_to_dict(make_user(), None, None, None, reminder_weekdays=[3, 1])

    assert payload["language_level_id"] is None
    assert payload["words_per_session"] == 10
    assert payload["daily_reminder_hour"] is None
    assert payload["is_import_google_doc_auto_sync_enabled"] is False
    assert payload["import_google_doc_retry_count"] == 0
    assert payload["reminder_weekdays"] == [1, 3]


def test_get_profile_returns_payload_with_reminder_weekdays_or_none() -> None:
    row = (make_user(), make_level(), make_settings(), "student")
    repository = UserProfileRepository(FakeSessionManager(FakeSession(execute_rows=[[row], []], scalars_rows=[[], [2, 0]])))

    payload = repository.get_profile(42)

    assert payload is not None
    assert payload["language_level_title"] == "A2"
    assert payload["words_per_session"] == 15
    assert payload["reminder_weekdays"] == [0, 2]
    assert repository.get_profile(404) is None


def test_get_profile_preserves_reminder_schedule_title_and_minute_after_reload() -> None:
    user = make_user()
    row = (user, make_level(), make_settings(user_uuid=user.uuid), "student")
    schedule = UserReminderSchedule(
        id=9,
        user_uuid=user.uuid,
        weekday=0,
        hour=8,
        minute=30,
        title="Morning focus",
        status="enabled",
    )
    repository = UserProfileRepository(FakeSessionManager(FakeSession(execute_rows=[[row]], scalars_rows=[[schedule], []])))

    payload = repository.get_profile(42)

    assert payload is not None
    assert payload["reminder_schedule"][0]["title"] == "Morning focus"
    assert payload["reminder_schedule"][0]["minute"] == 30
    assert payload["reminder_weekdays"] == [0]


def test_is_super_admin_matches_group_title() -> None:
    repository = UserProfileRepository(FakeSessionManager(FakeSession(scalar_values=["super_admin", "admin", None])))

    assert repository.is_super_admin(1) is True
    assert repository.is_super_admin(2) is False
    assert repository.is_super_admin(3) is False


def test_list_super_admin_profiles_returns_profiles_without_reminder_weekdays_key() -> None:
    row = (make_user(), make_level(), make_settings(), "super_admin")
    repository = UserProfileRepository(
        FakeSessionManager(
            FakeSession(
                execute_rows=[
                    [row],
                    [(1, None, "super_admin")],
                    [(1, "enabled")],
                ]
            )
        )
    )

    payload = repository.list_super_admin_profiles()

    assert payload[0]["acl_group_title"] == "super_admin"
    assert payload[0]["import_google_doc_id"] == "doc"
    assert "reminder_weekdays" not in payload[0]


def test_upsert_user_updates_existing_user_and_keeps_acl_without_explicit_group() -> None:
    existing_user = make_user(
        telegram_user_id=7,
        username="old",
        acl_group_id=1,
        language_code="pl",
        interface_locale="pl",
    )
    session = FakeSession(row_by_id={7: existing_user})
    repository = UserProfileRepository(FakeSessionManager(session))

    repository.upsert_user(
        {
            "telegram_user_id": 7,
            "username": "CronosHulk",
            "first_name": "Cronos",
            "language_code": "en-US",
            "raw_telegram_json": '{"source":"telegram"}',
        }
    )

    assert existing_user.acl_group_id == 1
    assert existing_user.language_code == "pl"
    assert existing_user.interface_locale == "pl"
    assert existing_user.username == "CronosHulk"
    assert existing_user.first_name == "Cronos"
    assert existing_user.raw_telegram_json == {"source": "telegram"}
    assert isinstance(session.added[-1], UserSubscription)
    assert session.added[-1].user_uuid == existing_user.uuid


def test_upsert_user_creates_user_with_student_acl_and_settings() -> None:
    session = FakeSession(scalar_values=[3, 1])
    repository = UserProfileRepository(FakeSessionManager(session))

    repository.upsert_user({"telegram_user_id": 9, "username": "newbie", "language_code": "pl-PL"})

    assert isinstance(session.added[0], User)
    assert session.added[0].telegram_user_id == 9
    assert session.added[0].acl_group_id == 3
    assert session.added[0].language_level_id == 1
    assert session.added[0].language_code == "pl"
    assert session.added[0].interface_locale == "pl"
    assert isinstance(session.added[1], UserLearningSettings)
    assert session.added[1].user_uuid == session.added[0].uuid
    assert isinstance(session.added[2], UserSubscription)
    assert session.added[2].user_uuid == session.added[0].uuid
    assert session.added[2].plan_key == "free"


def test_upsert_user_defaults_new_user_interface_locale_to_uk_for_unsupported_telegram_language() -> None:
    session = FakeSession(scalar_values=[3, 1])
    repository = UserProfileRepository(FakeSessionManager(session))

    repository.upsert_user({"telegram_user_id": 9, "username": "newbie", "language_code": "en-US"})

    assert session.added[0].language_code == "uk"
    assert session.added[0].interface_locale == "uk"


def test_set_interface_locale_updates_profile_language_fields() -> None:
    existing_user = make_user(telegram_user_id=7, language_code="uk", interface_locale="uk")
    session = FakeSession(row_by_id={7: existing_user})
    repository = UserProfileRepository(FakeSessionManager(session))

    repository.set_interface_locale(7, "pl")

    assert existing_user.language_code == "pl"
    assert existing_user.interface_locale == "pl"


def test_upsert_user_requires_configured_default_language_level() -> None:
    session = FakeSession(scalar_values=[3, None])
    repository = UserProfileRepository(FakeSessionManager(session))

    with pytest.raises(ValueError, match="Language level 'A1' is not configured"):
        repository.upsert_user({"telegram_user_id": 9, "username": "newbie"})


def test_save_user_event_persists_event_payload() -> None:
    session = FakeSession()
    repository = UserProfileRepository(FakeSessionManager(session))

    repository.save_user_event(
        telegram_user_id=42,
        event_type="message",
        raw_update_json={"update_id": 1},
        message_text="/start",
    )

    assert isinstance(session.added[0], UserEvent)
    assert session.added[0].telegram_user_id == 42
    assert session.added[0].raw_update_json == {"update_id": 1}
