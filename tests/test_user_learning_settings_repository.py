from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID

from app.data_access.user_learning_settings import UserLearningSettingsRepository
from app.models import (
    AppVersion,
    User,
    UserLearningSettings,
    UserReminderSchedule,
    UserReminderWeekday,
)


class FakeScalarsResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(self, *, row_by_key=None, scalars_rows=None) -> None:
        self.row_by_key = row_by_key or {}
        self.scalars_rows = list(scalars_rows or [])
        self.added = []
        self.deleted = []
        self.user = User(telegram_user_id=42, uuid=UUID("11111111-1111-4111-8111-111111111111"))

    def get(self, model, primary_key):
        if model is User and primary_key == self.user.telegram_user_id:
            return self.user
        return self.row_by_key.get((model, primary_key))

    def add(self, row) -> None:
        self.added.append(row)

    def delete(self, row) -> None:
        self.deleted.append(row)

    def scalars(self, statement):
        if self.scalars_rows and isinstance(self.scalars_rows[0], list):
            return FakeScalarsResult(self.scalars_rows.pop(0))
        return FakeScalarsResult(self.scalars_rows)


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def test_get_current_app_version_returns_active_version_only() -> None:
    active = AppVersion(key="current", version="1.2.3", is_active=True)
    inactive = AppVersion(key="current", version="1.2.4", is_active=False)

    active_repo = UserLearningSettingsRepository(
        FakeSessionManager(FakeSession(row_by_key={(AppVersion, "current"): active}))
    )
    inactive_repo = UserLearningSettingsRepository(
        FakeSessionManager(FakeSession(row_by_key={(AppVersion, "current"): inactive}))
    )
    missing_repo = UserLearningSettingsRepository(FakeSessionManager(FakeSession()))

    assert active_repo.get_current_app_version() == "1.2.3"
    assert inactive_repo.get_current_app_version() is None
    assert missing_repo.get_current_app_version() is None


def test_set_words_and_daily_reminder_create_missing_settings() -> None:
    session = FakeSession()
    repository = UserLearningSettingsRepository(FakeSessionManager(session))

    repository.set_words_per_session(42, 12)

    assert len(session.added) == 1
    assert session.added[0].user_uuid == session.user.uuid
    assert session.added[0].words_per_session == 12

    existing = UserLearningSettings(user_uuid=session.user.uuid, daily_reminder_hour=8)
    repository = UserLearningSettingsRepository(
        FakeSessionManager(FakeSession(row_by_key={(UserLearningSettings, session.user.uuid): existing}))
    )
    repository.set_daily_reminder_hour(42, 19)

    assert existing.daily_reminder_hour == 19


def test_get_and_set_reminder_weekdays() -> None:
    existing_rows = [
        UserReminderWeekday(user_uuid=UUID("11111111-1111-4111-8111-111111111111"), weekday=1),
        UserReminderWeekday(user_uuid=UUID("11111111-1111-4111-8111-111111111111"), weekday=3),
    ]
    read_repository = UserLearningSettingsRepository(FakeSessionManager(FakeSession(scalars_rows=[[], [1, 3]])))

    assert read_repository.get_reminder_weekdays(42) == [1, 3]

    session = FakeSession(scalars_rows=[[], existing_rows, []])
    repository = UserLearningSettingsRepository(FakeSessionManager(session))
    repository.set_reminder_weekdays(42, [6, 1, 7, -1, 1])

    assert session.deleted == existing_rows
    added_weekdays = [row.weekday for row in session.added if isinstance(row, UserReminderWeekday)]
    assert added_weekdays == [1, 6]


def test_set_reminder_weekdays_preserves_existing_schedule_hours() -> None:
    user_uuid = UUID("11111111-1111-4111-8111-111111111111")
    settings = UserLearningSettings(user_uuid=user_uuid, daily_reminder_hour=8)
    existing_schedule = [
        UserReminderSchedule(user_uuid=user_uuid, weekday=0, hour=9, status="enabled"),
        UserReminderSchedule(user_uuid=user_uuid, weekday=0, hour=12, status="enabled"),
    ]
    session = FakeSession(
        row_by_key={(UserLearningSettings, user_uuid): settings},
        scalars_rows=[existing_schedule, [], []],
    )
    repository = UserLearningSettingsRepository(FakeSessionManager(session))

    repository.set_reminder_weekdays(42, [1, 3])

    added_schedule = [row for row in session.added if isinstance(row, UserReminderSchedule)]
    assert [(row.weekday, row.hour, row.status) for row in added_schedule] == [
        (1, 9, "enabled"),
        (1, 12, "enabled"),
        (3, 9, "enabled"),
        (3, 12, "enabled"),
    ]


def test_clear_daily_reminder_settings_clears_hour_and_weekdays() -> None:
    user_uuid = UUID("11111111-1111-4111-8111-111111111111")
    settings = UserLearningSettings(user_uuid=user_uuid, daily_reminder_hour=8)
    weekdays = [UserReminderWeekday(user_uuid=user_uuid, weekday=2)]
    session = FakeSession(row_by_key={(UserLearningSettings, user_uuid): settings}, scalars_rows=[weekdays, []])
    repository = UserLearningSettingsRepository(FakeSessionManager(session))

    repository.clear_daily_reminder_settings(42)

    assert settings.daily_reminder_hour is None
    assert session.deleted == weekdays
