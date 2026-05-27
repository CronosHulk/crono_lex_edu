from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.contracts import ButtonModel, ReminderScreenModel, ScreenModel
from app.helpers.locale import resolve_user_locale
from app.i18n import translate
from app.reference.telegram_timing import TELEGRAM_LONG_WAIT_MS
from app.screen_delivery_policy import with_screen_delivery_policy
from app.time_utils import TimeService

REMINDER_AUTO_RETURN_AFTER_MS = TELEGRAM_LONG_WAIT_MS


class TrainingScheduleDueReader(Protocol):
    def get_due(self, current_time: datetime) -> list[dict[str, Any]]:
        ...


class UserProfileReader(Protocol):
    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...


class ClientReminderDispatchService:
    def __init__(
        self,
        training_schedules: TrainingScheduleDueReader,
        time_service: TimeService,
        user_profiles: UserProfileReader | None = None,
    ) -> None:
        self.training_schedules = self._resolve_training_schedules(training_schedules)
        self.user_profiles = self._resolve_user_profiles(training_schedules, user_profiles)
        self.time_service = time_service

    def _resolve_training_schedules(self, training_schedules: TrainingScheduleDueReader) -> TrainingScheduleDueReader:
        return getattr(training_schedules, "training_schedules", training_schedules)

    def _resolve_user_profiles(
        self,
        training_schedules: TrainingScheduleDueReader,
        user_profiles: UserProfileReader | None,
    ) -> UserProfileReader:
        if user_profiles is not None:
            return user_profiles
        resolved = getattr(training_schedules, "user_profiles", None)
        if resolved is not None:
            return resolved
        raise ValueError("user_profiles repository is required")

    def dispatch_due_reminders(self) -> list[ReminderScreenModel]:
        current_time = self.time_service.now()
        reminders: list[ReminderScreenModel] = []
        for row in self.training_schedules.get_due(current_time):
            profile = self.user_profiles.get_profile(row["telegram_user_id"])
            locale = resolve_user_locale(profile)
            reminders.append(
                ReminderScreenModel(
                    telegram_user_id=row["telegram_user_id"],
                    chat_id=row["chat_id"],
                    screen=self._build_due_reminder_screen(row, locale),
                )
            )
        return reminders

    def _build_due_reminder_screen(self, schedule: dict[str, Any], locale: str) -> ScreenModel:
        text_key = "reminder_followup_prompt" if schedule["schedule_type"] == "followup" else "reminder_daily_prompt"
        screen = ScreenModel(
            screen_id=f"reminder:{schedule['id']}",
            text=translate(locale, text_key),
            buttons=[
                ButtonModel(action=f"r:start:{schedule['id']}", text=translate(locale, "reminder_start_button")),
                ButtonModel(action=f"r:skip:{schedule['id']}", text=translate(locale, "reminder_skip_button")),
            ],
            keyboard_type="inline",
        )
        return with_screen_delivery_policy(screen, auto_return_after_ms=REMINDER_AUTO_RETURN_AFTER_MS)
