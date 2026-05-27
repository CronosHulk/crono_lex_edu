from __future__ import annotations

from typing import Any

from app.application.client_runtime.text_fallback_service import (
    ClientRuntimeTextFallbackService,
)
from app.contracts import ScreenModel


class FakeLearningSessions:
    def __init__(self, active_session: dict[str, Any] | None) -> None:
        self.active_session = active_session
        self.requested_telegram_user_id: int | None = None

    def get_active_session(self, telegram_user_id: int) -> dict[str, Any] | None:
        self.requested_telegram_user_id = telegram_user_id
        return self.active_session


def test_text_fallback_restores_active_telegram_session_with_force_resend() -> None:
    active_session = {
        "id": 77,
        "active_interface": "telegram_user",
    }
    learning_sessions = FakeLearningSessions(active_session)
    rendered_sessions: list[dict[str, Any]] = []

    def attach_runtime_telegram_user_id(
        session: dict[str, Any], telegram_user_id: int
    ) -> dict[str, Any]:
        return {**session, "runtime_telegram_user_id": telegram_user_id}

    def render_session_screen(session: dict[str, Any], locale: str) -> ScreenModel:
        rendered_sessions.append({"session": session, "locale": locale})
        return ScreenModel(screen_id="card:77", text="Card")

    service = ClientRuntimeTextFallbackService(
        learning_sessions,
        attach_runtime_telegram_user_id=attach_runtime_telegram_user_id,
        build_menu_screen=_raise_unexpected_menu_call,
        render_session_screen=render_session_screen,
    )

    screen = service.build_text_fallback_screen(telegram_user_id=123, locale="uk")

    assert learning_sessions.requested_telegram_user_id == 123
    assert rendered_sessions == [
        {
            "session": {
                "id": 77,
                "active_interface": "telegram_user",
                "runtime_telegram_user_id": 123,
            },
            "locale": "uk",
        }
    ]
    assert screen.screen_id == "card:77"
    assert screen.metadata["force_resend"] is True


def test_text_fallback_uses_forced_menu_when_active_session_is_not_telegram() -> None:
    learning_sessions = FakeLearningSessions(
        {
            "id": 77,
            "active_interface": "client_web",
        }
    )
    menu_calls: list[dict[str, Any]] = []
    service = ClientRuntimeTextFallbackService(
        learning_sessions,
        attach_runtime_telegram_user_id=_raise_unexpected_attach_call,
        build_menu_screen=_build_recording_menu_screen(menu_calls),
        render_session_screen=_raise_unexpected_render_call,
    )

    screen = service.build_text_fallback_screen(telegram_user_id=123, locale="uk")

    assert screen.screen_id == "menu"
    assert menu_calls == [
        {
            "telegram_user_id": 123,
            "locale": "uk",
            "kwargs": {"force_resend": True},
        }
    ]


def test_text_fallback_uses_forced_menu_without_active_session() -> None:
    menu_calls: list[dict[str, Any]] = []
    service = ClientRuntimeTextFallbackService(
        FakeLearningSessions(None),
        attach_runtime_telegram_user_id=_raise_unexpected_attach_call,
        build_menu_screen=_build_recording_menu_screen(menu_calls),
        render_session_screen=_raise_unexpected_render_call,
    )

    screen = service.build_text_fallback_screen(telegram_user_id=123, locale="uk")

    assert screen.screen_id == "menu"
    assert menu_calls == [
        {
            "telegram_user_id": 123,
            "locale": "uk",
            "kwargs": {"force_resend": True},
        }
    ]


def _build_recording_menu_screen(menu_calls: list[dict[str, Any]]):
    def build_menu_screen(
        telegram_user_id: int,
        locale: str,
        **kwargs: Any,
    ) -> ScreenModel:
        menu_calls.append(
            {
                "telegram_user_id": telegram_user_id,
                "locale": locale,
                "kwargs": kwargs,
            }
        )
        return ScreenModel(screen_id="menu", text="Menu")

    return build_menu_screen


def _raise_unexpected_attach_call(
    session: dict[str, Any], telegram_user_id: int
) -> dict[str, Any]:
    raise AssertionError("attach_runtime_telegram_user_id should not be called")


def _raise_unexpected_render_call(
    session: dict[str, Any], locale: str
) -> ScreenModel:
    raise AssertionError("render_session_screen should not be called")


def _raise_unexpected_menu_call(
    telegram_user_id: int,
    locale: str,
    **kwargs: Any,
) -> ScreenModel:
    raise AssertionError("build_menu_screen should not be called")
