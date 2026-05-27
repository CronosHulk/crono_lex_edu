from __future__ import annotations

from app.application.client_learning.session_action_service import (
    ClientLearningSessionActionService,
)
from app.contracts import ScreenModel


class FakeSessionActionReader:
    def __init__(self) -> None:
        self.active_sessions = {11: {"id": 77, "telegram_user_id": 11, "current_stage": "card"}}
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def get_active_session(self, telegram_user_id: int):
        self.calls.append(("get_active_session", (telegram_user_id,)))
        return self.active_sessions.get(telegram_user_id)


class CaptureSessionCallbacks:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def menu(self, telegram_user_id: int, locale: str) -> ScreenModel:
        self.calls.append(("menu", (telegram_user_id, locale)))
        return ScreenModel(screen_id="menu", text="menu")

    def render(self, session, locale: str) -> ScreenModel:
        self.calls.append(("render", (session, locale)))
        return ScreenModel(screen_id=f"session:{session['id'] if session else 'none'}", text="session")

    def card(
        self,
        telegram_user_id: int,
        active_session,
        locale: str,
        session_word_id: int | None,
        card_action: str | None,
    ) -> ScreenModel:
        self.calls.append(("card", (telegram_user_id, active_session, locale, session_word_id, card_action)))
        return ScreenModel(screen_id="card", text="card")

    def ready(self, telegram_user_id: int, active_session, locale: str, expected_stage: str | None, decision: str | None) -> ScreenModel:
        self.calls.append(("ready", (telegram_user_id, active_session, locale, expected_stage, decision)))
        return ScreenModel(screen_id="ready", text="ready")

    def answer(
        self,
        telegram_user_id: int,
        active_session,
        locale: str,
        session_word_id: int | None,
        option_index: int | None,
    ) -> ScreenModel:
        self.calls.append(("answer", (telegram_user_id, active_session, locale, session_word_id, option_index)))
        return ScreenModel(screen_id="answer", text="answer")


def build_service(learning_sessions: FakeSessionActionReader, callbacks: CaptureSessionCallbacks) -> ClientLearningSessionActionService:
    return ClientLearningSessionActionService(
        learning_sessions,
        build_menu_screen=callbacks.menu,
        render_session_screen=callbacks.render,
        handle_card_action=callbacks.card,
        handle_ready_action=callbacks.ready,
        handle_answer_action=callbacks.answer,
    )


def test_session_action_ignores_unrelated_action() -> None:
    learning_sessions = FakeSessionActionReader()
    callbacks = CaptureSessionCallbacks()

    assert build_service(learning_sessions, callbacks).handle_action(11, "uk", "m:s") is None
    assert learning_sessions.calls == []
    assert callbacks.calls == []


def test_session_action_rejects_malformed_payload_to_menu() -> None:
    learning_sessions = FakeSessionActionReader()
    callbacks = CaptureSessionCallbacks()

    screen = build_service(learning_sessions, callbacks).handle_action(11, "uk", "s:not-a-session:next")

    assert screen is not None
    assert screen.screen_id == "menu"
    assert callbacks.calls == [("menu", (11, "uk"))]
    assert learning_sessions.calls == []


def test_session_action_rejects_stale_session_to_menu() -> None:
    learning_sessions = FakeSessionActionReader()
    callbacks = CaptureSessionCallbacks()

    screen = build_service(learning_sessions, callbacks).handle_action(11, "uk", "s:99:next")

    assert screen is not None
    assert screen.screen_id == "menu"
    assert callbacks.calls == [("menu", (11, "uk"))]


def test_session_action_next_refreshes_and_renders_active_session() -> None:
    learning_sessions = FakeSessionActionReader()
    callbacks = CaptureSessionCallbacks()

    screen = build_service(learning_sessions, callbacks).handle_action(11, "uk", "s:77:next")

    assert screen is not None
    assert screen.screen_id == "session:77"
    assert [call[0] for call in learning_sessions.calls] == ["get_active_session", "get_active_session"]
    assert callbacks.calls == [("render", (learning_sessions.active_sessions[11], "uk"))]


def test_session_action_routes_card_payload_to_card_callback() -> None:
    learning_sessions = FakeSessionActionReader()
    callbacks = CaptureSessionCallbacks()

    screen = build_service(learning_sessions, callbacks).handle_action(11, "uk", "s:77:c:501:known")

    assert screen is not None
    assert screen.screen_id == "card"
    assert callbacks.calls == [("card", (11, learning_sessions.active_sessions[11], "uk", 501, "known"))]


def test_session_action_routes_ready_payload_to_ready_callback() -> None:
    learning_sessions = FakeSessionActionReader()
    callbacks = CaptureSessionCallbacks()

    screen = build_service(learning_sessions, callbacks).handle_action(11, "uk", "s:77:ready:ready_en_uk:yes")

    assert screen is not None
    assert screen.screen_id == "ready"
    assert callbacks.calls == [("ready", (11, learning_sessions.active_sessions[11], "uk", "ready_en_uk", "yes"))]


def test_session_action_routes_answer_payload_to_answer_callback() -> None:
    learning_sessions = FakeSessionActionReader()
    callbacks = CaptureSessionCallbacks()

    screen = build_service(learning_sessions, callbacks).handle_action(11, "uk", "s:77:a:501:2")

    assert screen is not None
    assert screen.screen_id == "answer"
    assert callbacks.calls == [("answer", (11, learning_sessions.active_sessions[11], "uk", 501, 2))]
