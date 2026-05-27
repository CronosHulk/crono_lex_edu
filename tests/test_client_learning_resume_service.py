from __future__ import annotations

from app.application.client_learning.resume_service import ClientLearningResumeService
from app.contracts import ScreenModel


class FakeResumeDb:
    def __init__(self) -> None:
        self.session: dict | None = None
        self.profile: dict | None = {"language_level_id": 1, "words_per_session": 10}

    def get_active_session(self, telegram_user_id: int):
        return self.session

    def get_profile(self, telegram_user_id: int):
        return self.profile


class CaptureCallbacks:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.should_confirm = False

    def menu_screen(self, telegram_user_id: int, locale: str) -> ScreenModel:
        self.calls.append(("menu", (telegram_user_id, locale)))
        return ScreenModel(screen_id="menu", text="menu")

    def choice_screen(self, telegram_user_id: int, locale: str, session: dict, profile: dict | None) -> ScreenModel:
        self.calls.append(("choice", (telegram_user_id, locale, session["id"], profile)))
        return ScreenModel(screen_id="choice", text="choice")

    def render_session(self, session: dict, locale: str) -> ScreenModel:
        self.calls.append(("render", (session["id"], session.get("telegram_user_id"), locale)))
        return ScreenModel(screen_id="session", text="session")

    def start_learning(self, telegram_user_id: int, locale: str) -> ScreenModel:
        self.calls.append(("start", (telegram_user_id, locale)))
        return ScreenModel(screen_id="start", text="start")

    def should_confirm_choice(self, session: dict, profile: dict | None) -> bool:
        self.calls.append(("confirm", (session["id"], profile)))
        return self.should_confirm

    def continue_ready_stage(self, telegram_user_id: int, session: dict, locale: str) -> ScreenModel:
        self.calls.append(("ready", (telegram_user_id, session["id"], locale)))
        return ScreenModel(screen_id="quiz", text="quiz")


def build_service(db: FakeResumeDb, callbacks: CaptureCallbacks) -> ClientLearningResumeService:
    return ClientLearningResumeService(
        db,
        db,
        build_menu_screen=callbacks.menu_screen,
        build_resume_choice_screen=callbacks.choice_screen,
        render_session_screen=callbacks.render_session,
        start_learning=callbacks.start_learning,
        should_confirm_resume_choice=callbacks.should_confirm_choice,
        continue_ready_stage=callbacks.continue_ready_stage,
    )


def test_learning_resume_service_renders_continue_session() -> None:
    db = FakeResumeDb()
    db.session = {"id": 77}
    callbacks = CaptureCallbacks()

    screen = build_service(db, callbacks).handle_action(11, "uk", "m:r:continue")

    assert screen is not None
    assert screen.screen_id == "session"
    assert callbacks.calls == [("render", (77, 11, "uk"))]


def test_learning_resume_service_continues_ready_stage_from_menu_resume() -> None:
    db = FakeResumeDb()
    db.session = {"id": 77, "current_stage": "ready_en_uk"}
    callbacks = CaptureCallbacks()
    callbacks.should_confirm = True

    screen = build_service(db, callbacks).handle_action(11, "uk", "m:r")

    assert screen is not None
    assert screen.screen_id == "quiz"
    assert callbacks.calls == [("ready", (11, 77, "uk"))]


def test_learning_resume_service_continues_ready_stage_from_choice_continue() -> None:
    db = FakeResumeDb()
    db.session = {"id": 77, "current_stage": "ready_uk_en"}
    callbacks = CaptureCallbacks()

    screen = build_service(db, callbacks).handle_action(11, "uk", "m:r:continue")

    assert screen is not None
    assert screen.screen_id == "quiz"
    assert callbacks.calls == [("ready", (11, 77, "uk"))]


def test_learning_resume_service_opens_menu_when_no_session() -> None:
    db = FakeResumeDb()
    callbacks = CaptureCallbacks()

    screen = build_service(db, callbacks).handle_action(11, "uk", "m:r")

    assert screen is not None
    assert screen.screen_id == "menu"
    assert callbacks.calls == [("menu", (11, "uk"))]


def test_learning_resume_service_opens_choice_when_settings_changed() -> None:
    db = FakeResumeDb()
    db.session = {"id": 77}
    callbacks = CaptureCallbacks()
    callbacks.should_confirm = True

    screen = build_service(db, callbacks).handle_action(11, "uk", "m:r")

    assert screen is not None
    assert screen.screen_id == "choice"
    assert [call[0] for call in callbacks.calls] == ["confirm", "choice"]


def test_learning_resume_service_restarts_learning() -> None:
    db = FakeResumeDb()
    callbacks = CaptureCallbacks()

    screen = build_service(db, callbacks).handle_action(11, "uk", "m:r:restart")

    assert screen is not None
    assert screen.screen_id == "start"
    assert callbacks.calls == [("start", (11, "uk"))]


def test_learning_resume_service_ignores_unrelated_action() -> None:
    db = FakeResumeDb()
    callbacks = CaptureCallbacks()

    screen = build_service(db, callbacks).handle_action(11, "uk", "m:s")

    assert screen is None
    assert callbacks.calls == []
