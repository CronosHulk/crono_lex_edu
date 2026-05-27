from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.application.client_learning.action_payload import parse_int_or_none
from app.contracts import ScreenModel
from app.reference.scheduling import HOURS_BY_PERIOD

MenuScreenBuilder = Callable[[int, str], ScreenModel]
SummaryScreenBuilder = Callable[[int, str], ScreenModel]
PlanningPeriodScreenBuilder = Callable[[int, str, str, int], ScreenModel]
PlanningHourScreenBuilder = Callable[[int, str, str, int, str], ScreenModel]
PlannedTrainingSaver = Callable[[int, str, str, int, str, int], ScreenModel]
OwnedSessionGetter = Callable[[int, int], dict[str, Any] | None]


class ClientLearningPlanningActionService:
    def __init__(
        self,
        *,
        build_menu_screen: MenuScreenBuilder,
        build_summary_screen: SummaryScreenBuilder,
        build_planning_period_screen: PlanningPeriodScreenBuilder,
        build_planning_hour_screen: PlanningHourScreenBuilder,
        save_planned_training: PlannedTrainingSaver,
        get_owned_learning_session: OwnedSessionGetter,
    ) -> None:
        self.build_menu_screen = build_menu_screen
        self.build_summary_screen = build_summary_screen
        self.build_planning_period_screen = build_planning_period_screen
        self.build_planning_hour_screen = build_planning_hour_screen
        self.save_planned_training = save_planned_training
        self.get_owned_learning_session = get_owned_learning_session

    def handle_action(self, telegram_user_id: int, locale: str, action: str) -> ScreenModel | None:
        if not action.startswith("m:p:"):
            return None
        parts = action.split(":")
        if len(parts) < 4:
            return self.build_menu_screen(telegram_user_id, locale)
        target_day = parts[2]
        session_id = parse_int_or_none(parts[3])
        if target_day not in {"today", "tomorrow"} or session_id is None:
            return self.build_menu_screen(telegram_user_id, locale)
        session = self.get_owned_learning_session(telegram_user_id, session_id)
        if session is None:
            return self.build_menu_screen(telegram_user_id, locale)
        if len(parts) == 4:
            if target_day == "today":
                return self.build_planning_hour_screen(telegram_user_id, locale, target_day, session["id"], "evening")
            return self.build_planning_period_screen(telegram_user_id, locale, target_day, session_id)
        if len(parts) == 6 and parts[4] == "period":
            period_code = parts[5]
            allowed_periods = {"evening"} if target_day == "today" else set(HOURS_BY_PERIOD)
            if period_code not in allowed_periods:
                return self.build_summary_screen(session["id"], locale)
            return self.build_planning_hour_screen(telegram_user_id, locale, target_day, session_id, period_code)
        if len(parts) == 7 and parts[4] == "hour":
            period_code = parts[5]
            hour = parse_int_or_none(parts[6])
            if hour is None or period_code not in HOURS_BY_PERIOD or hour not in HOURS_BY_PERIOD[period_code]:
                return self.build_summary_screen(session["id"], locale)
            return self.save_planned_training(telegram_user_id, locale, target_day, session_id, period_code, hour)
        return self.build_summary_screen(session["id"], locale)
