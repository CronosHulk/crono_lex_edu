from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Protocol

from app.reference.scheduling import format_weekday_labels
from app.time_utils import build_schedule_datetime


class TrainingScheduleReader(Protocol):
    def get_next(self, telegram_user_id: int, current_time: datetime) -> dict[str, Any] | None:
        ...


class ClientReminderDisplayService:
    def __init__(self, training_schedules: TrainingScheduleReader) -> None:
        self.training_schedules = self._resolve_training_schedules(training_schedules)

    def _resolve_training_schedules(self, training_schedules: TrainingScheduleReader) -> TrainingScheduleReader:
        return getattr(training_schedules, "training_schedules", training_schedules)

    def build_days_suffix(self, locale: str, reminder_hour: int | None, reminder_weekdays: list[int]) -> str:
        if reminder_hour is None or not reminder_weekdays:
            return ""
        return f" • {format_weekday_labels(locale, reminder_weekdays)}"

    def get_display_next_training(
        self,
        *,
        telegram_user_id: int,
        current_time: datetime,
        reminder_hour: int | None,
        reminder_weekdays: list[int],
    ) -> dict[str, Any] | None:
        ensure_daily = getattr(self.training_schedules, "ensure_daily", None)
        if callable(ensure_daily):
            ensure_daily(current_time)
        next_schedule = self.training_schedules.get_next(telegram_user_id, current_time)
        if next_schedule is not None:
            return next_schedule

        next_daily = self.build_next_daily_training(reminder_hour, reminder_weekdays, current_time)
        if next_daily is None:
            return None
        return {
            "id": None,
            "telegram_user_id": telegram_user_id,
            "schedule_type": "daily_config",
            "scheduled_for": next_daily,
        }

    def build_next_daily_training(
        self,
        reminder_hour: int | None,
        reminder_weekdays: list[int],
        current_time: datetime,
    ) -> datetime | None:
        if reminder_hour is None or not reminder_weekdays:
            return None

        allowed_weekdays = sorted(set(reminder_weekdays))
        for offset in range(0, 8):
            candidate_date = current_time.date() + timedelta(days=offset)
            if candidate_date.weekday() not in allowed_weekdays:
                continue
            scheduled_for = build_schedule_datetime(current_time, candidate_date, reminder_hour)
            if scheduled_for >= current_time:
                return scheduled_for
        return None
