from __future__ import annotations

from app.application.client_learning.ready_screens import build_ready_screen
from app.i18n import translate
from app.reference.learning_flow import READY_STAGE_INTRO_I18N_KEYS


def test_build_ready_screen_uses_stage_intro_and_actions() -> None:
    session = {"id": 42, "current_stage": "ready_en_uk"}

    screen = build_ready_screen(session, "uk")

    assert screen.screen_id == "ready_en_uk"
    assert screen.text == "\n\n".join(
        [
            translate("uk", READY_STAGE_INTRO_I18N_KEYS["ready_en_uk"]),
            translate("uk", "ready_prompt"),
        ]
    )
    assert [button.action for button in screen.buttons] == [
        "s:42:ready:ready_en_uk:yes",
        "s:42:ready:ready_en_uk:no",
    ]
    assert [button.text for button in screen.buttons] == [
        translate("uk", "ready_yes"),
        translate("uk", "ready_no"),
    ]
    assert screen.keyboard_type == "inline"
    assert screen.clear_chat is False
    assert screen.notice_text is None


def test_build_ready_screen_supports_pause_notice_and_previous_card_cleanup() -> None:
    session = {
        "id": 43,
        "current_stage": "ready_uk_en",
        "metadata": {"clear_previous_card": True},
    }

    screen = build_ready_screen(session, "uk", paused=True, notice="Paused")

    assert screen.text == "\n\n".join(
        [
            translate("uk", "ready_pause"),
            translate("uk", "ready_prompt"),
        ]
    )
    assert screen.clear_chat is True
    assert screen.notice_text == "Paused"
