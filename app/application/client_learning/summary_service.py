from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, Protocol

from app.application.client_learning.display import build_section_title
from app.contracts import ButtonModel, ScreenModel
from app.i18n import translate
from app.plurals import format_exercise_error_count
from app.reference.service import format_count_text

MenuScreenBuilder = Callable[[int, str], ScreenModel]

_UPCOMING_REMINDER_WINDOW = timedelta(hours=2)
_UPCOMING_REMINDER_STATUSES = {"pending", "sent"}


class SummaryLearningSessionRepository(Protocol):
    def get_session(self, session_id: int) -> dict[str, Any] | None:
        ...

    def get_session_words(self, session_id: int) -> list[dict[str, Any]]:
        ...


class SummaryUserProfileRepository(Protocol):
    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...


class SummaryLearningProgressRepository(Protocol):
    def get_user_assignment_summary(self, telegram_user_id: int) -> dict[str, int]:
        ...


class SummaryTimeService(Protocol):
    def now(self) -> datetime:
        ...


class SummaryReminderDisplayService(Protocol):
    def get_display_next_training(
        self,
        *,
        telegram_user_id: int,
        current_time: datetime,
        reminder_hour: int | None,
        reminder_weekdays: list[int],
    ) -> dict[str, Any] | None:
        ...


def _is_actionable_upcoming_reminder(
    schedule: dict[str, Any],
    current_time: datetime,
    *,
    window: timedelta = _UPCOMING_REMINDER_WINDOW,
) -> bool:
    scheduled_for = schedule.get("scheduled_for")
    if not isinstance(scheduled_for, datetime):
        return False
    if scheduled_for.date() != current_time.date():
        return False
    if str(schedule.get("status") or "pending") not in _UPCOMING_REMINDER_STATUSES:
        return False
    return current_time <= scheduled_for <= current_time + window


class ClientLearningSummaryService:
    def __init__(
        self,
        learning_sessions: SummaryLearningSessionRepository,
        user_profiles: SummaryUserProfileRepository,
        learning_progress: SummaryLearningProgressRepository,
        time_service: SummaryTimeService,
        reminder_display_service: SummaryReminderDisplayService,
        *,
        build_menu_screen: MenuScreenBuilder,
    ) -> None:
        self.learning_sessions = learning_sessions
        self.user_profiles = user_profiles
        self.learning_progress = learning_progress
        self.time_service = time_service
        self.reminder_display_service = reminder_display_service
        self.build_menu_screen = build_menu_screen

    def build_summary_screen(
        self,
        session_id: int,
        locale: str,
        notice: str | None = None,
        *,
        telegram_user_id: int | None = None,
    ) -> ScreenModel:
        session = self.learning_sessions.get_session(session_id)
        if session is None:
            return self.build_menu_screen(0, locale)
        resolved_telegram_user_id = telegram_user_id
        if resolved_telegram_user_id is None:
            resolved_telegram_user_id = session.get("telegram_user_id")
        if resolved_telegram_user_id is None:
            return self.build_menu_screen(0, locale)
        resolved_telegram_user_id = int(resolved_telegram_user_id)
        progress = self.learning_progress.get_user_assignment_summary(resolved_telegram_user_id)
        error_count, error_word_count = self._count_session_errors(session_id)

        lines = [
            build_section_title(translate(locale, "summary_title")),
            "",
            translate(locale, "summary_training_done_title"),
            (
                translate(
                    locale,
                    "summary_training_errors_line",
                    error_count_text=format_exercise_error_count(locale, error_count),
                    word_count_text=format_count_text(locale, error_word_count),
                )
                if error_count
                else translate(locale, "summary_training_no_errors_line")
            ),
            *([translate(locale, "summary_training_repeat_later")] if error_word_count else []),
            "",
            translate(locale, "summary_learned_title"),
            translate(
                locale,
                "summary_in_progress_line",
                count_text=format_count_text(locale, progress["in_progress_count"]),
            ),
            translate(
                locale,
                "summary_needs_work_line",
                count_text=format_count_text(locale, progress["needs_work_count"]),
            ),
            translate(
                locale,
                "summary_learned_line",
                learned=progress["learned_count"],
                total=progress["total_count"],
            ),
            translate(locale, "summary_mastery_rule"),
            "",
        ]
        if session.get("session_type") == "followup":
            lines.insert(-1, translate(locale, "summary_followup_notice"))
            lines.insert(-1, "")

        upcoming_reminder = self._get_upcoming_reminder(resolved_telegram_user_id)
        if upcoming_reminder is not None:
            lines.extend(
                [
                    "",
                    translate(
                        locale,
                        "reminder_upcoming_prompt",
                        time=upcoming_reminder["scheduled_for"].strftime("%H:%M"),
                    ),
                ]
            )

        buttons = self._build_summary_buttons(upcoming_reminder, locale)

        return ScreenModel(
            screen_id=f"summary:{session_id}",
            text="\n".join(lines),
            buttons=buttons,
            keyboard_type="inline",
            notice_text=notice,
        )

    def _build_summary_buttons(
        self,
        upcoming_reminder: dict[str, Any] | None,
        locale: str,
    ) -> list[ButtonModel]:
        if upcoming_reminder is None:
            return [ButtonModel(action="m:menu", text=translate(locale, "summary_finish_training_button"))]
        return [
            ButtonModel(
                action=f"r:complete:{upcoming_reminder['id']}",
                text=translate(locale, "reminder_upcoming_skip_button"),
            ),
            ButtonModel(
                action=f"r:keep:{upcoming_reminder['id']}",
                text=translate(locale, "reminder_upcoming_keep_button"),
            ),
        ]

    def _get_upcoming_reminder(self, telegram_user_id: int) -> dict[str, Any] | None:
        current_time = self.time_service.now()
        profile = self.user_profiles.get_profile(telegram_user_id)
        next_training = self.reminder_display_service.get_display_next_training(
            telegram_user_id=telegram_user_id,
            current_time=current_time,
            reminder_hour=profile.get("daily_reminder_hour") if profile else None,
            reminder_weekdays=profile.get("reminder_weekdays", []) if profile else [],
        )
        if next_training is None or next_training.get("id") is None:
            return None
        scheduled_for = next_training.get("scheduled_for")
        if not isinstance(scheduled_for, datetime):
            return None
        if not _is_actionable_upcoming_reminder(next_training, current_time):
            return None
        return next_training

    def _count_session_errors(self, session_id: int) -> tuple[int, int]:
        error_count = 0
        error_word_count = 0
        for word in self.learning_sessions.get_session_words(session_id):
            word_errors = sum(
                max(int(word.get(attempts_field) or 0) - 1, 0)
                for attempts_field in ("en_uk_attempts", "uk_en_attempts", "gap_attempts")
            )
            error_count += word_errors
            if word_errors:
                error_word_count += 1
        return error_count, error_word_count
