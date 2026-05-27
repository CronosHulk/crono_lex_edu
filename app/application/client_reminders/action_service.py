from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.application.client_reminders.action_payload import parse_int_or_none
from app.application.client_reminders.upcoming import is_actionable_upcoming_reminder
from app.contracts import ScreenModel
from app.i18n import translate

MenuScreenBuilder = Callable[..., ScreenModel]
StartLearningCallback = Callable[..., ScreenModel]
TimeProvider = Callable[[], datetime]


class TrainingScheduleWriter(Protocol):
    def get(self, schedule_id: int) -> dict[str, Any] | None:
        ...

    def update_status(self, schedule_id: int, status: str) -> None:
        ...


class ClientReminderActionService:
    def __init__(
        self,
        training_schedules: TrainingScheduleWriter,
        *,
        current_time: TimeProvider,
        build_menu_screen: MenuScreenBuilder,
        start_learning: StartLearningCallback,
    ) -> None:
        self.training_schedules = self._resolve_training_schedules(training_schedules)
        self.current_time = current_time
        self.build_menu_screen = build_menu_screen
        self.start_learning = start_learning

    def _resolve_training_schedules(self, training_schedules: TrainingScheduleWriter) -> TrainingScheduleWriter:
        return getattr(training_schedules, "training_schedules", training_schedules)

    def handle_action(self, telegram_user_id: int, locale: str, action: str) -> ScreenModel | None:
        if not action.startswith("r:"):
            return None
        parts = action.split(":")
        if len(parts) < 3:
            return self.build_menu_screen(telegram_user_id, locale)
        reminder_action = parts[1]
        schedule_id = parse_int_or_none(parts[2])
        if reminder_action not in {"start", "skip", "complete", "keep"} or schedule_id is None:
            return self.build_menu_screen(telegram_user_id, locale)
        schedule = self.training_schedules.get(schedule_id)
        if schedule is None or schedule["telegram_user_id"] != telegram_user_id:
            return self.build_menu_screen(telegram_user_id, locale)

        current_time = self.current_time()
        if reminder_action == "start":
            return self.start_learning(telegram_user_id, locale, schedule=schedule)
        if reminder_action == "skip":
            return self._skip_reminder(telegram_user_id, locale, schedule_id)
        if reminder_action == "complete":
            return self._complete_reminder(telegram_user_id, locale, schedule, schedule_id, current_time)
        if reminder_action == "keep":
            if not self._is_upcoming_today(schedule, current_time):
                return self.build_menu_screen(telegram_user_id, locale)
            return self.build_menu_screen(telegram_user_id, locale, force_resend=True)
        return self.build_menu_screen(telegram_user_id, locale)

    def _skip_reminder(self, telegram_user_id: int, locale: str, schedule_id: int) -> ScreenModel:
        self.training_schedules.update_status(schedule_id, "skipped")
        return self.build_menu_screen(
            telegram_user_id,
            locale,
            force_resend=True,
        )

    def _complete_reminder(
        self,
        telegram_user_id: int,
        locale: str,
        schedule: dict[str, Any],
        schedule_id: int,
        current_time: datetime,
    ) -> ScreenModel:
        if not self._is_upcoming_today(schedule, current_time):
            return self.build_menu_screen(telegram_user_id, locale)
        self.training_schedules.update_status(schedule_id, "completed")
        return self.build_menu_screen(
            telegram_user_id,
            locale,
            notice=translate(locale, "reminder_completed_notice"),
            force_resend=True,
        )

    def _is_upcoming_today(self, schedule: dict[str, Any], current_time: datetime) -> bool:
        return is_actionable_upcoming_reminder(schedule, current_time)
