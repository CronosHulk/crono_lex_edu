from __future__ import annotations

from datetime import datetime

from app.application.client_reminders.display_service import ClientReminderDisplayService


class FakeReminderTrainingSchedules:
    def __init__(self) -> None:
        self.next_schedule = None

    def get_next(self, telegram_user_id: int, current_time: datetime):
        return self.next_schedule


def test_reminder_display_service_prefers_explicit_schedule() -> None:
    db = FakeReminderTrainingSchedules()
    db.next_schedule = {
        "id": 501,
        "telegram_user_id": 1,
        "schedule_type": "planned",
        "scheduled_for": datetime(2026, 4, 7, 19, 0, 0),
    }
    service = ClientReminderDisplayService(db)

    next_training = service.get_display_next_training(
        telegram_user_id=1,
        current_time=datetime(2026, 4, 6, 10, 0, 0),
        reminder_hour=10,
        reminder_weekdays=[0],
    )

    assert next_training == db.next_schedule


def test_reminder_display_service_falls_back_to_same_day_daily_config() -> None:
    service = ClientReminderDisplayService(FakeReminderTrainingSchedules())

    next_training = service.get_display_next_training(
        telegram_user_id=1,
        current_time=datetime(2026, 4, 6, 9, 0, 0),
        reminder_hour=10,
        reminder_weekdays=[0],
    )

    assert next_training["schedule_type"] == "daily_config"
    assert next_training["scheduled_for"] == datetime(2026, 4, 6, 10, 0, 0)


def test_reminder_display_service_rolls_daily_config_to_next_selected_weekday() -> None:
    service = ClientReminderDisplayService(FakeReminderTrainingSchedules())

    next_training = service.get_display_next_training(
        telegram_user_id=1,
        current_time=datetime(2026, 4, 6, 11, 0, 0),
        reminder_hour=10,
        reminder_weekdays=[0, 2],
    )

    assert next_training["scheduled_for"] == datetime(2026, 4, 8, 10, 0, 0)


def test_reminder_display_service_returns_none_without_daily_config() -> None:
    service = ClientReminderDisplayService(FakeReminderTrainingSchedules())

    assert (
        service.get_display_next_training(
            telegram_user_id=1,
            current_time=datetime(2026, 4, 6, 9, 0, 0),
            reminder_hour=None,
            reminder_weekdays=[0],
        )
        is None
    )
    assert (
        service.get_display_next_training(
            telegram_user_id=1,
            current_time=datetime(2026, 4, 6, 9, 0, 0),
            reminder_hour=10,
            reminder_weekdays=[],
        )
        is None
    )


def test_reminder_display_service_builds_days_suffix() -> None:
    service = ClientReminderDisplayService(FakeReminderTrainingSchedules())

    assert service.build_days_suffix("uk", None, [0]) == ""
    assert service.build_days_suffix("uk", 10, []) == ""
    assert service.build_days_suffix("uk", 10, [0, 2, 4]) == " • Пн, Ср, Пт"
