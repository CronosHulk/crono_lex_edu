from __future__ import annotations

from app.application.client_learning.ready_action_service import ClientLearningReadyActionService
from app.contracts import ScreenModel


class CaptureReadyCallbacks:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def menu(self, telegram_user_id: int, locale: str, **kwargs) -> ScreenModel:
        self.calls.append(("menu", (telegram_user_id, locale), kwargs))
        return ScreenModel(screen_id="menu", text=str(kwargs.get("notice") or ""))

    def render(self, session, locale: str) -> ScreenModel:
        self.calls.append(("render", (session, locale), {}))
        return ScreenModel(screen_id="render", text="render")

    def start_next(self, telegram_user_id: int, session, locale: str) -> ScreenModel:
        self.calls.append(("start_next", (telegram_user_id, session, locale), {}))
        return ScreenModel(screen_id="quiz", text="quiz")


def build_service(callbacks: CaptureReadyCallbacks) -> ClientLearningReadyActionService:
    return ClientLearningReadyActionService(
        build_menu_screen=callbacks.menu,
        render_session_screen=callbacks.render,
        start_next_quiz_stage=callbacks.start_next,
    )


def test_ready_action_rejects_invalid_stage_to_session_render() -> None:
    callbacks = CaptureReadyCallbacks()
    session = {"id": 77, "current_stage": "ready_en_uk"}

    screen = build_service(callbacks).handle_action(11, session, "uk", "ready_other", "yes")

    assert screen.screen_id == "render"
    assert callbacks.calls == [("render", (session, "uk"), {})]


def test_ready_action_rejects_stale_stage_to_session_render() -> None:
    callbacks = CaptureReadyCallbacks()
    session = {"id": 77, "current_stage": "ready_uk_en"}

    screen = build_service(callbacks).handle_action(11, session, "uk", "ready_en_uk", "yes")

    assert screen.screen_id == "render"
    assert callbacks.calls == [("render", (session, "uk"), {})]


def test_ready_action_no_returns_menu_with_pause_notice() -> None:
    callbacks = CaptureReadyCallbacks()
    session = {"id": 77, "current_stage": "ready_en_uk"}

    screen = build_service(callbacks).handle_action(11, session, "uk", "ready_en_uk", "no")

    assert screen.screen_id == "menu"
    assert screen.text
    assert callbacks.calls[0][0] == "menu"
    assert callbacks.calls[0][1] == (11, "uk")
    assert callbacks.calls[0][2]["notice"] == screen.text


def test_ready_action_unknown_decision_renders_session() -> None:
    callbacks = CaptureReadyCallbacks()
    session = {"id": 77, "current_stage": "ready_en_uk"}

    screen = build_service(callbacks).handle_action(11, session, "uk", "ready_en_uk", "later")

    assert screen.screen_id == "render"
    assert callbacks.calls == [("render", (session, "uk"), {})]


def test_ready_action_yes_starts_next_quiz_stage() -> None:
    callbacks = CaptureReadyCallbacks()
    session = {"id": 77, "current_stage": "ready_en_uk"}

    screen = build_service(callbacks).handle_action(11, session, "uk", "ready_en_uk", "yes")

    assert screen.screen_id == "quiz"
    assert callbacks.calls == [("start_next", (11, session, "uk"), {})]
