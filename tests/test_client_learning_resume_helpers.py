from __future__ import annotations

from app.application.client_learning.resume import (
    build_resume_choice_screen,
    get_menu_resume_button_text,
    should_confirm_resume_choice,
)


def test_get_menu_resume_button_text_uses_summary_label_for_finished_sessions() -> None:
    assert get_menu_resume_button_text("uk", {"current_stage": "summary"}) == "📊 Відкрити підсумок заняття"
    assert get_menu_resume_button_text("uk", {"current_stage": "completed"}) == "📊 Відкрити підсумок заняття"
    assert get_menu_resume_button_text("uk", {"current_stage": "cards"}) == "⏯️ Продовжити поточне заняття"


def test_should_confirm_resume_choice_returns_false_for_missing_or_non_regular_state() -> None:
    assert not should_confirm_resume_choice({"current_stage": "cards"}, None)
    assert not should_confirm_resume_choice(
        {"current_stage": "cards", "session_type": "followup"},
        {"language_level_id": 1, "words_per_session": 10},
    )
    assert not should_confirm_resume_choice(
        {"current_stage": "summary", "session_type": "regular"},
        {"language_level_id": 1, "words_per_session": 10},
    )


def test_should_confirm_resume_choice_detects_changed_settings() -> None:
    profile = {"language_level_id": 1, "words_per_session": 10}

    assert not should_confirm_resume_choice(
        {"current_stage": "cards", "session_type": "regular", "language_level_id": 1, "words_target_count": 10},
        profile,
    )
    assert should_confirm_resume_choice(
        {"current_stage": "cards", "session_type": "regular", "language_level_id": 2, "words_target_count": 10},
        profile,
    )
    assert should_confirm_resume_choice(
        {"current_stage": "cards", "session_type": "regular", "language_level_id": 1, "words_target_count": 20},
        profile,
    )


def test_build_resume_choice_screen_includes_changed_level_and_word_count() -> None:
    screen = build_resume_choice_screen(
        locale="uk",
        session={"language_level_id": 2, "words_target_count": 20},
        profile={"language_level_id": 1, "language_level_title": "A1", "words_per_session": 10},
        session_level="A2",
    )

    assert screen.screen_id == "resume:choice"
    assert "A2" in screen.text
    assert "A1" in screen.text
    assert "20 слів" in screen.text
    assert "10 слів" in screen.text
    assert [button.action for button in screen.buttons] == ["m:r:continue", "m:r:restart", "m:menu"]
    assert screen.metadata == {"buttons_per_row": 1}


def test_build_resume_choice_screen_handles_missing_profile() -> None:
    screen = build_resume_choice_screen(
        locale="uk",
        session={"language_level_id": 2, "words_target_count": 20},
        profile=None,
        session_level="A2",
    )

    assert "A2" in screen.text
    assert "—" in screen.text
