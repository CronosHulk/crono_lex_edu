from __future__ import annotations

from typing import Any

from app.application.client_learning.menu_screen_service import ClientLearningMenuScreenService


class FakeMenuSessionReader:
    def __init__(
        self,
        *,
        active_session: dict[str, Any] | None = None,
    ) -> None:
        self.active_session = active_session
        self.active_session_requests: list[int] = []

    def get_active_session(self, telegram_user_id: int) -> dict[str, Any] | None:
        self.active_session_requests.append(telegram_user_id)
        return self.active_session


def test_build_menu_screen_loads_active_session_and_builds_two_part_menu() -> None:
    learning_sessions = FakeMenuSessionReader(
        active_session={"current_stage": "card"},
    )
    service = ClientLearningMenuScreenService(
        learning_sessions,
    )

    screen = service.build_menu_screen(telegram_user_id=42, locale="uk", notice="Saved", clear_chat=True, force_resend=True)

    assert learning_sessions.active_session_requests == [42]
    assert "Saved" in screen.text
    assert "Почати тренування можна" in screen.text
    assert [button.action for button in screen.buttons] == ["m:s", "m:r"]
    assert screen.clear_chat is True
    assert screen.metadata["buttons_per_row"] == 1
    assert screen.metadata["force_resend"] is True
    assert screen.metadata["auxiliary_after_active"] is True
    assert "налаштуваннях" in screen.metadata["auxiliary_message_text"]
    assert screen.metadata["auxiliary_message_buttons"] == [{"action": "m:settings", "text": "⚙️ Налаштування", "url": None}]


def test_build_menu_screen_skips_progress_without_level_id() -> None:
    learning_sessions = FakeMenuSessionReader()
    service = ClientLearningMenuScreenService(
        learning_sessions,
    )

    screen = service.build_menu_screen(telegram_user_id=77, locale="uk")

    assert screen.text == "Почати тренування можна будь-коли, навіть без нагадування."


def test_build_close_to_menu_screen_applies_close_delivery_policy() -> None:
    learning_sessions = FakeMenuSessionReader()
    service = ClientLearningMenuScreenService(
        learning_sessions,
    )

    screen = service.build_close_to_menu_screen(telegram_user_id=77, locale="uk")

    assert learning_sessions.active_session_requests == [77]
    assert screen.clear_chat is True
    assert screen.metadata["force_resend"] is True
    assert screen.metadata["delete_cached_active_screen"] is True
