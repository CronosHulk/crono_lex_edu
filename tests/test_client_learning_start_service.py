from __future__ import annotations

from datetime import datetime
from typing import Any

from app.application.client_learning.start_service import ClientLearningStartService
from app.contracts import ScreenModel


class FakeStartDb:
    def __init__(self) -> None:
        self.profile: dict[str, Any] | None = {
            "telegram_user_id": 1,
            "language_level_id": 3,
            "language_level_title": "B1",
            "words_per_session": 10,
        }
        self.active_level_run: dict[str, Any] | None = None
        self.latest_level_run: dict[str, Any] | None = None
        self.lesson_words = [{"id": 101, "word": "learn"}]
        self.followup_words = [{"id": 201, "word": "repeat"}]
        self.completed_due_schedules: list[dict[str, Any]] = []
        self.completed_level_runs: list[int] = []
        self.cancelled_users: list[int] = []
        self.created_level_runs: list[dict[str, Any]] = []
        self.created_sessions: list[dict[str, Any]] = []
        self.updated_schedules: list[dict[str, Any]] = []

    @property
    def learning_levels(self) -> FakeStartDb:
        return self

    @property
    def user_profiles(self) -> FakeStartDb:
        return self

    @property
    def training_schedules(self) -> FakeStartDb:
        return self

    @property
    def lesson_word_selection(self) -> FakeStartDb:
        return self

    @property
    def learning_sessions(self) -> FakeStartDb:
        return self

    def get_user_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        return self.profile

    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        return self.get_user_profile(telegram_user_id)

    def complete_due_training_schedules(self, telegram_user_id: int, current_time: datetime, *, exclude_schedule_id=None) -> None:
        self.completed_due_schedules.append(
            {
                "telegram_user_id": telegram_user_id,
                "current_time": current_time,
                "exclude_schedule_id": exclude_schedule_id,
            }
        )

    def complete_due(self, telegram_user_id: int, current_time: datetime, *, exclude_schedule_id=None) -> None:
        self.complete_due_training_schedules(
            telegram_user_id,
            current_time,
            exclude_schedule_id=exclude_schedule_id,
        )

    def select_followup_words(self, source_session_id: int) -> list[dict[str, Any]]:
        return self.followup_words

    def get_active(self, telegram_user_id: int, level_id: int) -> dict[str, Any] | None:
        return self.active_level_run

    def get_latest(self, telegram_user_id: int, level_id: int) -> dict[str, Any] | None:
        return self.latest_level_run

    def create(self, telegram_user_id: int, level_id: int) -> dict[str, Any]:
        row = {"id": 301, "telegram_user_id": telegram_user_id, "level_id": level_id}
        self.created_level_runs.append(row)
        return row

    def select_lesson_words(self, *, telegram_user_id: int, level_id: int, words_limit: int) -> list[dict[str, Any]]:
        return self.lesson_words

    def complete(self, level_run_id: int, current_time: datetime | None = None) -> None:
        self.completed_level_runs.append(level_run_id)

    def cancel_active_sessions(self, telegram_user_id: int) -> None:
        self.cancelled_users.append(telegram_user_id)

    def create_learning_session(self, **kwargs: Any) -> dict[str, Any]:
        session = {"id": 77, "current_stage": "card", **kwargs}
        self.created_sessions.append(session)
        return session

    def create_session(self, **kwargs: Any) -> dict[str, Any]:
        return self.create_learning_session(**kwargs)

    def update_training_schedule_status(self, schedule_id: int, status: str) -> None:
        self.updated_schedules.append({"schedule_id": schedule_id, "status": status})

    def update_status(self, schedule_id: int, status: str) -> None:
        self.update_training_schedule_status(schedule_id, status)


class CompletionSpy:
    def __init__(self) -> None:
        self.snapshot = {"B1": {"is_completed": False}}
        self.next_level: str | None = None
        self.lower_levels: list[str] = []

    def get_level_completion_snapshot(self, telegram_user_id: int) -> dict[str, dict[str, Any]]:
        return self.snapshot

    def find_next_unfinished_higher_level(self, telegram_user_id: int, current_level_title: str) -> str | None:
        return self.next_level

    def get_unfinished_lower_levels(self, telegram_user_id: int, current_level_title: str) -> list[str]:
        return self.lower_levels

    def build_level_completed_screen(self, locale: str, current_level: str, next_level: str) -> ScreenModel:
        return ScreenModel(screen_id="level-completed", text=f"{current_level}->{next_level}")

    def build_lower_levels_suggestion_screen(self, locale: str, levels: list[str]) -> ScreenModel:
        return ScreenModel(screen_id="lower-levels", text=",".join(levels))

    def build_course_completed_screen(self, locale: str) -> ScreenModel:
        return ScreenModel(screen_id="course-completed", text="course")


class StartCallbacks:
    def __init__(self) -> None:
        self.menus: list[dict[str, Any]] = []
        self.transient_errors: list[dict[str, Any]] = []
        self.rendered_sessions: list[dict[str, Any]] = []
        self.owned_sessions: dict[int, dict[str, Any] | None] = {}

    def build_menu(self, telegram_user_id: int, locale: str, **kwargs: Any) -> ScreenModel:
        self.menus.append({"telegram_user_id": telegram_user_id, "locale": locale, **kwargs})
        return ScreenModel(screen_id="menu", text=str(kwargs.get("notice") or "menu"))

    def build_transient_error(self, locale: str, **kwargs: Any) -> ScreenModel:
        self.transient_errors.append({"locale": locale, **kwargs})
        return ScreenModel(screen_id="transient:error", text=str(kwargs["message"]))

    def render_session(self, session: dict[str, Any], locale: str) -> ScreenModel:
        self.rendered_sessions.append({"session": session, "locale": locale})
        return ScreenModel(screen_id="session", text=str(session["id"]))

    def get_owned_session(self, telegram_user_id: int, session_id: int) -> dict[str, Any] | None:
        return self.owned_sessions.get(session_id)


def build_service(
    db: FakeStartDb | None = None,
    completion: CompletionSpy | None = None,
    callbacks: StartCallbacks | None = None,
) -> tuple[ClientLearningStartService, FakeStartDb, CompletionSpy, StartCallbacks]:
    db = db or FakeStartDb()
    completion = completion or CompletionSpy()
    callbacks = callbacks or StartCallbacks()
    service = ClientLearningStartService(
        db.user_profiles,
        db.training_schedules,
        db.lesson_word_selection,
        db.learning_sessions,
        db.learning_levels,
        completion,
        current_time=lambda: datetime(2026, 4, 26, 12, 0, 0),
        build_menu_screen=callbacks.build_menu,
        build_transient_error_screen=callbacks.build_transient_error,
        render_session_screen=callbacks.render_session,
        get_owned_learning_session=callbacks.get_owned_session,
    )
    return service, db, completion, callbacks


def test_start_learning_without_level_returns_transient_error() -> None:
    service, db, _, callbacks = build_service()
    db.profile = {"telegram_user_id": 1, "language_level_id": None}

    screen = service.start_learning(1, "uk")

    assert screen.screen_id == "transient:error"
    assert callbacks.transient_errors[0]["message"]
    assert db.completed_due_schedules == []


def test_start_learning_creates_regular_session_and_level_run() -> None:
    service, db, _, callbacks = build_service()

    screen = service.start_learning(1, "uk")

    assert screen.screen_id == "session"
    assert db.completed_due_schedules[0]["exclude_schedule_id"] is None
    assert db.created_level_runs == [{"id": 301, "telegram_user_id": 1, "level_id": 3}]
    assert db.cancelled_users == [1]
    assert db.created_sessions[0]["level_run_id"] == 301
    assert db.created_sessions[0]["session_type"] == "regular"
    assert callbacks.rendered_sessions[0]["session"]["words_target_count"] == 10
    assert callbacks.rendered_sessions[0]["session"]["telegram_user_id"] == 1


def test_start_learning_uses_active_level_run() -> None:
    service, db, _, _ = build_service()
    db.active_level_run = {"id": 88}

    service.start_learning(1, "uk")

    assert db.created_level_runs == []
    assert db.created_sessions[0]["level_run_id"] == 88


def test_start_learning_returns_next_level_completed_screen_before_new_run() -> None:
    service, db, completion, _ = build_service()
    db.latest_level_run = {"id": 55}
    completion.snapshot = {"B1": {"is_completed": True}}
    completion.next_level = "B2"

    screen = service.start_learning(1, "uk")

    assert screen.screen_id == "level-completed"
    assert screen.text == "B1->B2"
    assert db.created_sessions == []


def test_start_learning_completed_level_can_offer_lower_levels_or_course_completed() -> None:
    service, db, completion, _ = build_service()
    db.latest_level_run = {"id": 55}
    completion.snapshot = {"B1": {"is_completed": True}}
    completion.lower_levels = ["A2"]

    lower_screen = service.start_learning(1, "uk")

    assert lower_screen.screen_id == "lower-levels"
    completion.lower_levels = []
    course_screen = service.start_learning(1, "uk")
    assert course_screen.screen_id == "course-completed"


def test_start_learning_without_words_completes_finished_level_run() -> None:
    service, db, completion, _ = build_service()
    db.active_level_run = {"id": 88}
    db.lesson_words = []
    completion.snapshot = {"B1": {"is_completed": True}}
    completion.next_level = "B2"

    screen = service.start_learning(1, "uk")

    assert screen.screen_id == "level-completed"
    assert db.completed_level_runs == [88]
    assert db.created_sessions == []


def test_start_learning_without_words_returns_menu_when_level_is_not_complete() -> None:
    service, db, _, callbacks = build_service()
    db.lesson_words = []

    screen = service.start_learning(1, "uk")

    assert screen.screen_id == "menu"
    assert callbacks.menus[0]["notice"]
    assert db.created_sessions == []


def test_start_learning_followup_missing_source_returns_menu_without_completing_schedule() -> None:
    service, db, _, callbacks = build_service()
    schedule = {"id": 44, "schedule_type": "followup", "source_session_id": 999}

    screen = service.start_learning(1, "uk", schedule=schedule)

    assert screen.screen_id == "menu"
    assert callbacks.menus[0]["notice"]
    assert db.updated_schedules == []


def test_start_learning_followup_creates_session_and_completes_schedule() -> None:
    service, db, _, callbacks = build_service()
    callbacks.owned_sessions[77] = {"id": 77, "level_run_id": 909}
    schedule = {"id": 44, "schedule_type": "followup", "source_session_id": 77}

    screen = service.start_learning(1, "uk", schedule=schedule)

    assert screen.screen_id == "session"
    assert db.completed_due_schedules[0]["exclude_schedule_id"] == 44
    assert db.created_sessions[0]["session_type"] == "followup"
    assert db.created_sessions[0]["source_session_id"] == 77
    assert db.created_sessions[0]["level_run_id"] == 909
    assert db.created_sessions[0]["words_target_count"] == 1
    assert db.updated_schedules == [{"schedule_id": 44, "status": "completed"}]


def test_start_learning_followup_without_words_returns_menu() -> None:
    service, db, _, callbacks = build_service()
    callbacks.owned_sessions[77] = {"id": 77, "level_run_id": 909}
    db.followup_words = []
    schedule = {"id": 44, "schedule_type": "followup", "source_session_id": 77}

    screen = service.start_learning(1, "uk", schedule=schedule)

    assert screen.screen_id == "menu"
    assert callbacks.menus[0]["notice"]
    assert db.created_sessions == []
    assert db.updated_schedules == []
