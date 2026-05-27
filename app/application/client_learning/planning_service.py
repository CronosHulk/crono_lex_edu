from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any, Protocol

from app.application.client_learning.session_identity import with_runtime_telegram_user_id
from app.application.client_ui.choice_controls import build_single_choice_label
from app.contracts import ButtonModel, ScreenModel
from app.i18n import translate
from app.reference.scheduling import HOURS_BY_PERIOD, format_hour_label
from app.time_utils import TimeService, build_schedule_datetime

MenuScreenBuilder = Callable[[int, str, str | None], ScreenModel]
SummaryScreenBuilder = Callable[[int, str, str | None], ScreenModel]
UserUuidResolver = Callable[[int], str | None]


class LearningSessionReader(Protocol):
    def get_session(self, session_id: int) -> dict[str, Any] | None:
        ...


class TrainingSchedulePlanner(Protocol):
    def get_existing_for_date(
        self,
        telegram_user_id: int,
        target_date: date,
        *,
        schedule_types: tuple[str, ...] | None = None,
    ) -> dict[str, Any] | None:
        ...

    def create_or_replace(
        self,
        telegram_user_id: int,
        schedule_type: str,
        scheduled_for: datetime,
        period_code: str | None = None,
        source_session_id: int | None = None,
    ) -> dict[str, Any]:
        ...


class ClientLearningPlanningService:
    def __init__(
        self,
        learning_sessions: LearningSessionReader,
        training_schedules: TrainingSchedulePlanner,
        time_service: TimeService,
        *,
        build_menu_screen: MenuScreenBuilder,
        build_summary_screen: SummaryScreenBuilder,
        resolve_user_uuid: UserUuidResolver | None = None,
    ) -> None:
        self.learning_sessions = learning_sessions
        self.training_schedules = training_schedules
        self.time_service = time_service
        self.build_menu_screen = build_menu_screen
        self.build_summary_screen = build_summary_screen
        self.resolve_user_uuid = resolve_user_uuid

    def get_owned_learning_session(self, telegram_user_id: int, session_id: int) -> dict[str, Any] | None:
        session = self.learning_sessions.get_session(session_id)
        if session is None:
            return None
        if self.resolve_user_uuid is not None:
            user_uuid = self.resolve_user_uuid(telegram_user_id)
            session_user_uuid = str(session.get("user_id") or session.get("user_uuid") or "")
            if user_uuid and session_user_uuid and str(user_uuid) == session_user_uuid:
                return with_runtime_telegram_user_id(session, telegram_user_id)
            if user_uuid and session_user_uuid:
                return None
        if session.get("telegram_user_id") != telegram_user_id:
            return None
        return with_runtime_telegram_user_id(session, telegram_user_id)

    def build_period_screen(self, telegram_user_id: int, locale: str, target_day: str, session_id: int) -> ScreenModel:
        current_date = self.time_service.now().date()
        allowed_periods = ("evening",) if target_day == "today" else ("morning", "day", "evening")
        target_date = current_date if target_day == "today" else current_date + timedelta(days=1)
        existing_schedule = self.training_schedules.get_existing_for_date(telegram_user_id, target_date)
        buttons = [
            ButtonModel(
                action=f"m:p:{target_day}:{session_id}:period:{period}",
                text=build_single_choice_label(
                    translate(locale, f"period_{period}"),
                    existing_schedule is not None and existing_schedule.get("period_code") == period,
                ),
            )
            for period in allowed_periods
        ]
        buttons.append(ButtonModel(action="m:menu", text=translate(locale, "menu_back")))
        return ScreenModel(
            screen_id=f"planning:{target_day}:period",
            text=translate(locale, "planning_period_prompt", day=translate(locale, f"planning_day_{target_day}")),
            buttons=buttons,
            keyboard_type="inline",
        )

    def build_hour_screen(
        self,
        telegram_user_id: int,
        locale: str,
        target_day: str,
        session_id: int,
        period_code: str,
    ) -> ScreenModel:
        current_time = self.time_service.now()
        target_date = current_time.date() if target_day == "today" else current_time.date() + timedelta(days=1)
        existing_schedule = self.training_schedules.get_existing_for_date(telegram_user_id, target_date)
        available_hours = [
            hour
            for hour in HOURS_BY_PERIOD[period_code]
            if target_day != "today" or build_schedule_datetime(current_time, target_date, hour) > current_time
        ]
        if not available_hours:
            return self.build_summary_screen(
                session_id,
                locale,
                translate(locale, "planning_today_time_passed_notice"),
            )
        buttons = [
            ButtonModel(
                action=f"m:p:{target_day}:{session_id}:hour:{period_code}:{hour}",
                text=build_single_choice_label(
                    format_hour_label(hour),
                    existing_schedule is not None
                    and existing_schedule.get("period_code") == period_code
                    and int(existing_schedule["scheduled_for"].hour) == hour,
                ),
            )
            for hour in available_hours
        ]
        buttons.append(
            ButtonModel(
                action=f"m:p:{target_day}:{session_id}",
                text=translate(locale, "menu_back"),
            )
        )
        return ScreenModel(
            screen_id=f"planning:{target_day}:hours:{period_code}",
            text=translate(
                locale,
                "planning_hour_prompt",
                day=translate(locale, f"planning_day_{target_day}"),
                period=translate(locale, f"period_{period_code}"),
            ),
            buttons=buttons,
            keyboard_type="inline",
        )

    def save_planned_training(
        self,
        telegram_user_id: int,
        locale: str,
        target_day: str,
        session_id: int,
        period_code: str,
        hour: int,
    ) -> ScreenModel:
        current_time = self.time_service.now()
        owned_session = self.get_owned_learning_session(telegram_user_id, session_id) if session_id else None
        if session_id and owned_session is None:
            return self.build_menu_screen(telegram_user_id, locale, None)
        target_date = current_time.date() if target_day == "today" else current_time.date() + timedelta(days=1)
        scheduled_for = build_schedule_datetime(current_time, target_date, hour)
        if target_day == "today" and scheduled_for <= current_time:
            return self.build_summary_screen(
                session_id,
                locale,
                translate(locale, "planning_today_time_passed_notice"),
            )
        schedule_type = "followup" if target_day == "today" else "planned"
        self.training_schedules.create_or_replace(
            telegram_user_id=telegram_user_id,
            schedule_type=schedule_type,
            scheduled_for=scheduled_for,
            period_code=period_code,
            source_session_id=session_id or None,
        )
        notice = translate(
            locale,
            "planning_saved_notice",
            day=translate(locale, f"planning_day_{target_day}"),
            time=format_hour_label(hour),
        )
        if session_id:
            return self.build_summary_screen(session_id, locale, notice)
        return self.build_menu_screen(telegram_user_id, locale, notice)
