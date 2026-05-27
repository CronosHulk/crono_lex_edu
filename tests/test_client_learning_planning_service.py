from __future__ import annotations

from datetime import datetime

from app.application.client_learning.planning_service import ClientLearningPlanningService
from app.contracts import ScreenModel

USER_UUID = "00000000-0000-0000-0000-000000000011"


class FakePlanningSessions:
    def __init__(self) -> None:
        self.sessions = {77: {"id": 77, "telegram_user_id": 11}}

    def get_session(self, session_id: int):
        return self.sessions.get(session_id)


class FakePlanningSchedules:
    def __init__(self) -> None:
        self.existing_schedule = None
        self.saved_schedules: list[dict[str, object]] = []

    def get_existing_for_date(self, telegram_user_id: int, target_date, *, schedule_types=None):
        return self.existing_schedule

    def create_or_replace(self, **kwargs) -> None:
        self.saved_schedules.append(kwargs)


class FakeTimeService:
    def __init__(self, current_time: datetime) -> None:
        self.current_time = current_time

    def now(self) -> datetime:
        return self.current_time


class CaptureScreens:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def menu(self, telegram_user_id: int, locale: str, notice: str | None) -> ScreenModel:
        self.calls.append(("menu", (telegram_user_id, locale, notice)))
        return ScreenModel(screen_id="menu", text=notice or "menu")

    def summary(self, session_id: int, locale: str, notice: str | None) -> ScreenModel:
        self.calls.append(("summary", (session_id, locale, notice)))
        return ScreenModel(screen_id=f"summary:{session_id}", text=notice or "summary")


def build_service(
    learning_sessions: FakePlanningSessions | None = None,
    training_schedules: FakePlanningSchedules | None = None,
    current_time: datetime = datetime(2026, 4, 26, 12, 0, 0),
    screens: CaptureScreens | None = None,
) -> tuple[ClientLearningPlanningService, FakePlanningSessions, FakePlanningSchedules, CaptureScreens]:
    learning_sessions = learning_sessions or FakePlanningSessions()
    training_schedules = training_schedules or FakePlanningSchedules()
    screens = screens or CaptureScreens()
    return (
        ClientLearningPlanningService(
            learning_sessions,
            training_schedules,
            FakeTimeService(current_time),
            build_menu_screen=screens.menu,
            build_summary_screen=screens.summary,
        ),
        learning_sessions,
        training_schedules,
        screens,
    )


def test_get_owned_learning_session_rejects_foreign_or_missing_session() -> None:
    service, _, _, _ = build_service()

    assert service.get_owned_learning_session(11, 77) == {"id": 77, "telegram_user_id": 11}
    assert service.get_owned_learning_session(12, 77) is None
    assert service.get_owned_learning_session(11, 88) is None


def test_get_owned_learning_session_accepts_uuid_only_session_when_resolver_matches() -> None:
    sessions = FakePlanningSessions()
    sessions.sessions = {77: {"id": 77, "user_id": USER_UUID}}
    service, _, _, _ = build_service(learning_sessions=sessions)
    service.resolve_user_uuid = lambda telegram_user_id: USER_UUID if telegram_user_id == 11 else None

    assert service.get_owned_learning_session(11, 77) == {
        "id": 77,
        "user_id": USER_UUID,
        "telegram_user_id": 11,
    }
    assert service.get_owned_learning_session(12, 77) is None


def test_get_owned_learning_session_keeps_legacy_telegram_check_when_session_has_no_uuid() -> None:
    service, _, _, _ = build_service()
    service.resolve_user_uuid = lambda telegram_user_id: USER_UUID if telegram_user_id == 11 else None

    assert service.get_owned_learning_session(11, 77) == {"id": 77, "telegram_user_id": 11}
    assert service.get_owned_learning_session(12, 77) is None


def test_build_period_screen_marks_existing_period() -> None:
    training_schedules = FakePlanningSchedules()
    training_schedules.existing_schedule = {"period_code": "day"}
    service, _, _, _ = build_service(training_schedules=training_schedules)

    screen = service.build_period_screen(telegram_user_id=11, locale="uk", target_day="tomorrow", session_id=77)

    assert screen.screen_id == "planning:tomorrow:period"
    assert [button.action for button in screen.buttons] == [
        "m:p:tomorrow:77:period:morning",
        "m:p:tomorrow:77:period:day",
        "m:p:tomorrow:77:period:evening",
        "m:menu",
    ]
    assert "✓" in screen.buttons[1].text


def test_build_today_hour_screen_hides_past_hours_and_marks_existing_hour() -> None:
    training_schedules = FakePlanningSchedules()
    training_schedules.existing_schedule = {"period_code": "evening", "scheduled_for": datetime(2026, 4, 26, 20, 0, 0)}
    service, _, _, _ = build_service(
        training_schedules=training_schedules,
        current_time=datetime(2026, 4, 26, 19, 30, 0),
    )

    screen = service.build_hour_screen(telegram_user_id=11, locale="uk", target_day="today", session_id=77, period_code="evening")

    assert screen.screen_id == "planning:today:hours:evening"
    assert [button.action for button in screen.buttons] == [
        "m:p:today:77:hour:evening:20",
        "m:p:today:77:hour:evening:21",
        "m:p:today:77:hour:evening:22",
        "m:p:today:77",
    ]
    assert "✓" in screen.buttons[0].text


def test_build_today_hour_screen_returns_summary_when_no_future_hours() -> None:
    screens = CaptureScreens()
    service, _, _, _ = build_service(current_time=datetime(2026, 4, 26, 22, 0, 0), screens=screens)

    screen = service.build_hour_screen(telegram_user_id=11, locale="uk", target_day="today", session_id=77, period_code="evening")

    assert screen.screen_id == "summary:77"
    assert screens.calls[0][0] == "summary"
    assert "вільний час уже минув" in str(screens.calls[0][1][2])


def test_save_planned_training_rejects_foreign_session() -> None:
    screens = CaptureScreens()
    service, _, training_schedules, _ = build_service(screens=screens)

    screen = service.save_planned_training(telegram_user_id=12, locale="uk", target_day="tomorrow", session_id=77, period_code="morning", hour=9)

    assert screen.screen_id == "menu"
    assert training_schedules.saved_schedules == []
    assert screens.calls == [("menu", (12, "uk", None))]


def test_save_planned_training_rejects_past_today_hour() -> None:
    screens = CaptureScreens()
    service, _, training_schedules, _ = build_service(
        current_time=datetime(2026, 4, 26, 20, 30, 0),
        screens=screens,
    )

    screen = service.save_planned_training(telegram_user_id=11, locale="uk", target_day="today", session_id=77, period_code="evening", hour=20)

    assert screen.screen_id == "summary:77"
    assert training_schedules.saved_schedules == []
    assert "вільний час уже минув" in str(screens.calls[0][1][2])


def test_save_planned_training_persists_followup_and_returns_summary() -> None:
    service, _, training_schedules, screens = build_service(current_time=datetime(2026, 4, 26, 12, 0, 0))

    screen = service.save_planned_training(telegram_user_id=11, locale="uk", target_day="today", session_id=77, period_code="evening", hour=19)

    assert screen.screen_id == "summary:77"
    assert training_schedules.saved_schedules[0]["schedule_type"] == "followup"
    assert training_schedules.saved_schedules[0]["source_session_id"] == 77
    assert screens.calls[0][0] == "summary"


def test_save_planned_training_without_session_returns_menu() -> None:
    service, _, training_schedules, screens = build_service(current_time=datetime(2026, 4, 26, 12, 0, 0))

    screen = service.save_planned_training(telegram_user_id=11, locale="uk", target_day="tomorrow", session_id=0, period_code="morning", hour=9)

    assert screen.screen_id == "menu"
    assert training_schedules.saved_schedules[0]["schedule_type"] == "planned"
    assert training_schedules.saved_schedules[0]["source_session_id"] is None
    assert screens.calls[0][0] == "menu"
