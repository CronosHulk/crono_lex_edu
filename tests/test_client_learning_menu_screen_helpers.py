from __future__ import annotations

from app.application.client_learning.menu_screens import build_main_menu_screen


def test_build_main_menu_screen_renders_learning_message_and_buttons() -> None:
    screen = build_main_menu_screen(
        locale="uk",
        active_session={"current_stage": "card"},
        notice="Saved",
        clear_chat=True,
        force_resend=True,
    )

    assert screen.screen_id == "menu"
    assert "Saved" in screen.text
    assert screen.text.endswith("Почати тренування можна будь-коли, навіть без нагадування.")
    assert [button.action for button in screen.buttons] == ["m:s", "m:r"]
    assert screen.clear_chat is True
    assert screen.metadata["buttons_per_row"] == 1
    assert screen.metadata["force_resend"] is True
    assert screen.metadata["auxiliary_after_active"] is True
    assert screen.metadata["auxiliary_message_text"] == "Графік і рівень тренувань можна змінити в налаштуваннях."
    assert screen.metadata["auxiliary_message_buttons"] == [{"action": "m:settings", "text": "⚙️ Налаштування", "url": None}]


def test_build_main_menu_screen_uses_defaults_without_profile_or_schedule() -> None:
    screen = build_main_menu_screen(
        locale="uk",
        active_session={"current_stage": "completed"},
    )

    assert screen.text == "Почати тренування можна будь-коли, навіть без нагадування."
    assert [button.action for button in screen.buttons] == ["m:s", "m:r"]
    assert "підсумок" in screen.buttons[1].text
    assert screen.clear_chat is False
    assert screen.metadata["buttons_per_row"] == 1
    assert screen.metadata["force_resend"] is False
    assert screen.metadata["auxiliary_message_text"] == "Графік і рівень тренувань можна змінити в налаштуваннях."


def test_build_main_menu_screen_shows_resume_for_web_owned_session() -> None:
    screen = build_main_menu_screen(
        locale="uk",
        active_session={"current_stage": "card", "active_interface": "client_web"},
    )

    assert [button.action for button in screen.buttons] == ["m:s", "m:r"]


def test_build_main_menu_screen_hides_resume_for_empty_session() -> None:
    screen = build_main_menu_screen(
        locale="uk",
        active_session={"current_stage": "card", "session_words_count": 0},
    )

    assert [button.action for button in screen.buttons] == ["m:s"]
