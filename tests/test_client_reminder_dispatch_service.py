from __future__ import annotations

from datetime import datetime

from app.application.client_reminders.dispatch_service import (
    REMINDER_AUTO_RETURN_AFTER_MS,
    ClientReminderDispatchService,
)
from app.i18n import translate


class FixedTimeService:
    def __init__(self, current_time: datetime) -> None:
        self.current_time = current_time

    def now(self) -> datetime:
        return self.current_time


class FakeReminderTrainingSchedules:
    def __init__(self) -> None:
        self.current_time_seen = None
        self.due_schedules = [
            {"id": 501, "telegram_user_id": 1, "chat_id": 99, "schedule_type": "daily"},
            {"id": 502, "telegram_user_id": 2, "chat_id": 100, "schedule_type": "followup"},
        ]

    def get_due(self, current_time):
        self.current_time_seen = current_time
        return list(self.due_schedules)


class FakeReminderUserProfiles:
    def __init__(self) -> None:
        self.profiles = {
            1: {"language_code": "uk"},
            2: {"language_code": "uk"},
        }

    def get_profile(self, telegram_user_id: int):
        return self.profiles.get(telegram_user_id)


def test_client_reminder_dispatch_service_builds_due_reminder_models() -> None:
    training_schedules = FakeReminderTrainingSchedules()
    user_profiles = FakeReminderUserProfiles()
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    service = ClientReminderDispatchService(training_schedules, FixedTimeService(current_time), user_profiles)

    reminders = service.dispatch_due_reminders()

    assert training_schedules.current_time_seen == current_time
    assert [item.telegram_user_id for item in reminders] == [1, 2]
    assert [item.chat_id for item in reminders] == [99, 100]
    assert [item.screen.screen_id for item in reminders] == ["reminder:501", "reminder:502"]
    assert [item.screen.text for item in reminders] == [
        translate("uk", "reminder_daily_prompt"),
        translate("uk", "reminder_followup_prompt"),
    ]
    assert [[button.action for button in item.screen.buttons] for item in reminders] == [
        ["r:start:501", "r:skip:501"],
        ["r:start:502", "r:skip:502"],
    ]
    assert [item.screen.buttons[1].text for item in reminders] == ["Закрити", "Закрити"]
    assert [item.screen.keyboard_type for item in reminders] == ["inline", "inline"]
    assert [item.screen.metadata for item in reminders] == [
        {"auto_return_after_ms": REMINDER_AUTO_RETURN_AFTER_MS},
        {"auto_return_after_ms": REMINDER_AUTO_RETURN_AFTER_MS},
    ]


def test_client_reminder_dispatch_service_falls_back_to_uk_locale() -> None:
    training_schedules = FakeReminderTrainingSchedules()
    user_profiles = FakeReminderUserProfiles()
    user_profiles.profiles = {}
    service = ClientReminderDispatchService(
        training_schedules,
        FixedTimeService(datetime(2026, 4, 26, 10, 0, 0)),
        user_profiles,
    )

    reminders = service.dispatch_due_reminders()

    assert [item.screen.text for item in reminders] == [
        translate("uk", "reminder_daily_prompt"),
        translate("uk", "reminder_followup_prompt"),
    ]
