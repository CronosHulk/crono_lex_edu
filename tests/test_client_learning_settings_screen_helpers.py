from __future__ import annotations

from app.application.client_learning.settings_screens import (
    build_level_menu_screen,
    build_mode_menu_screen,
    build_settings_screen,
)


def test_build_settings_screen_renders_profile_notice_doc_and_buttons() -> None:
    screen = build_settings_screen(
        locale="uk",
        profile={
            "language_level_title": "A2",
            "words_per_session": 20,
            "daily_reminder_hour": 9,
            "import_google_doc_id": "https://docs.google.com/document/d/abc123/edit",
        },
        reminder_days_suffix=" у будні",
        notice="Saved",
    )

    assert screen.screen_id == "menu:settings"
    assert "Saved" in screen.text
    assert "Поточний рівень: A2" in screen.text
    assert "20 слів" in screen.text
    assert "09:00 у будні" in screen.text
    assert "https://docs.google.com/document/d/***/..." in screen.text
    assert [button.action for button in screen.buttons] == ["m:levels", "m:modes", "m:n", "m:i", "m:menu"]
    assert screen.metadata == {"buttons_per_row": 1}


def test_build_settings_screen_defaults_and_escapes_import_error() -> None:
    screen = build_settings_screen(
        locale="uk",
        profile={
            "language_level_title": "A1",
            "import_google_doc_last_error": "<boom>",
        },
        reminder_days_suffix="",
    )

    assert "10 слів" in screen.text
    assert "не налаштовано" in screen.text
    assert "&lt;boom&gt;" in screen.text
    assert "<boom>" not in screen.text


def test_build_level_menu_screen_marks_current_level_and_adds_back_buttons() -> None:
    screen = build_level_menu_screen(
        locale="uk",
        current_level="A2",
        available_levels=["A1", "A2", "B1"],
        notice="Saved",
    )

    assert screen.screen_id == "menu:levels"
    assert "Saved" in screen.text
    assert "Поточний рівень: A2" in screen.text
    assert [button.action for button in screen.buttons] == ["m:l:A1", "m:l:A2", "m:l:B1", "m:settings", "m:menu"]
    assert "✓" in screen.buttons[1].text
    assert screen.metadata == {"button_row_widths": [2, 1, 1, 1]}


def test_build_level_menu_screen_handles_missing_current_level() -> None:
    screen = build_level_menu_screen(
        locale="uk",
        current_level=None,
        available_levels=[],
    )

    assert "Поточний рівень: —" in screen.text
    assert [button.action for button in screen.buttons] == ["m:settings", "m:menu"]
    assert screen.metadata == {"button_row_widths": [1, 1]}


def test_build_mode_menu_screen_marks_current_word_count_and_adds_back_buttons() -> None:
    screen = build_mode_menu_screen(
        locale="uk",
        words_count=20,
        words_per_session_options=(10, 20, 30),
        notice="Saved",
    )

    assert screen.screen_id == "menu:modes"
    assert "Saved" in screen.text
    assert "20 слів" in screen.text
    assert [button.action for button in screen.buttons] == ["m:w:10", "m:w:20", "m:w:30", "m:settings", "m:menu"]
    assert "✓" in screen.buttons[1].text
    assert screen.metadata == {"button_row_widths": [2, 1, 1, 1]}


def test_build_mode_menu_screen_handles_empty_options() -> None:
    screen = build_mode_menu_screen(
        locale="uk",
        words_count=10,
        words_per_session_options=(),
    )

    assert [button.action for button in screen.buttons] == ["m:settings", "m:menu"]
    assert screen.metadata == {"button_row_widths": [1, 1]}
