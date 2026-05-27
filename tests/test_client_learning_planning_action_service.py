from __future__ import annotations

from app.application.client_learning.planning_action_service import (
    ClientLearningPlanningActionService,
)
from app.contracts import ScreenModel


class CapturePlanningCallbacks:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.sessions = {77: {"id": 77}}

    def menu(self, telegram_user_id: int, locale: str) -> ScreenModel:
        self.calls.append(("menu", (telegram_user_id, locale)))
        return ScreenModel(screen_id="menu", text="menu")

    def summary(self, session_id: int, locale: str) -> ScreenModel:
        self.calls.append(("summary", (session_id, locale)))
        return ScreenModel(screen_id="summary", text="summary")

    def period(self, telegram_user_id: int, locale: str, target_day: str, session_id: int) -> ScreenModel:
        self.calls.append(("period", (telegram_user_id, locale, target_day, session_id)))
        return ScreenModel(screen_id="period", text="period")

    def hour(self, telegram_user_id: int, locale: str, target_day: str, session_id: int, period_code: str) -> ScreenModel:
        self.calls.append(("hour", (telegram_user_id, locale, target_day, session_id, period_code)))
        return ScreenModel(screen_id="hour", text="hour")

    def save(self, telegram_user_id: int, locale: str, target_day: str, session_id: int, period_code: str, hour: int) -> ScreenModel:
        self.calls.append(("save", (telegram_user_id, locale, target_day, session_id, period_code, hour)))
        return ScreenModel(screen_id="save", text="save")

    def get_session(self, telegram_user_id: int, session_id: int):
        self.calls.append(("get_session", (telegram_user_id, session_id)))
        return self.sessions.get(session_id)


def build_service(callbacks: CapturePlanningCallbacks) -> ClientLearningPlanningActionService:
    return ClientLearningPlanningActionService(
        build_menu_screen=callbacks.menu,
        build_summary_screen=callbacks.summary,
        build_planning_period_screen=callbacks.period,
        build_planning_hour_screen=callbacks.hour,
        save_planned_training=callbacks.save,
        get_owned_learning_session=callbacks.get_session,
    )


def test_planning_action_routes_today_to_evening_hours() -> None:
    callbacks = CapturePlanningCallbacks()

    screen = build_service(callbacks).handle_action(11, "uk", "m:p:today:77")

    assert screen is not None
    assert screen.screen_id == "hour"
    assert callbacks.calls == [
        ("get_session", (11, 77)),
        ("hour", (11, "uk", "today", 77, "evening")),
    ]


def test_planning_action_routes_tomorrow_to_period_picker() -> None:
    callbacks = CapturePlanningCallbacks()

    screen = build_service(callbacks).handle_action(11, "uk", "m:p:tomorrow:77")

    assert screen is not None
    assert screen.screen_id == "period"
    assert callbacks.calls[-1] == ("period", (11, "uk", "tomorrow", 77))


def test_planning_action_routes_valid_hour_submission() -> None:
    callbacks = CapturePlanningCallbacks()

    screen = build_service(callbacks).handle_action(11, "uk", "m:p:today:77:hour:evening:19")

    assert screen is not None
    assert screen.screen_id == "save"
    assert callbacks.calls[-1] == ("save", (11, "uk", "today", 77, "evening", 19))


def test_planning_action_rejects_invalid_period_to_summary() -> None:
    callbacks = CapturePlanningCallbacks()

    screen = build_service(callbacks).handle_action(11, "uk", "m:p:today:77:period:morning")

    assert screen is not None
    assert screen.screen_id == "summary"
    assert callbacks.calls[-1] == ("summary", (77, "uk"))


def test_planning_action_rejects_invalid_payload_to_menu() -> None:
    callbacks = CapturePlanningCallbacks()

    screen = build_service(callbacks).handle_action(11, "uk", "m:p:today:not-a-session")

    assert screen is not None
    assert screen.screen_id == "menu"
    assert callbacks.calls == [("menu", (11, "uk"))]


def test_planning_action_ignores_unrelated_action() -> None:
    callbacks = CapturePlanningCallbacks()

    assert build_service(callbacks).handle_action(11, "uk", "m:r") is None
    assert callbacks.calls == []
