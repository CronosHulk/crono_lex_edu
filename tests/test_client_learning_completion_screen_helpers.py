from __future__ import annotations

from app.application.client_learning.completion_screens import (
    build_course_completed_screen,
    build_course_repeat_level_picker_screen,
    build_level_completed_screen,
    build_lower_levels_suggestion_screen,
)


def test_build_level_completed_screen_offers_next_repeat_and_menu() -> None:
    screen = build_level_completed_screen(locale="uk", current_level="A1", next_level="A2")

    assert screen.screen_id == "level:completed"
    assert "A1" in screen.text
    assert "A2" in screen.text
    assert [button.action for button in screen.buttons] == ["m:level:next:A2", "m:level:repeat:A1", "m:menu"]
    assert screen.metadata == {"buttons_per_row": 1}


def test_build_course_repeat_level_picker_screen_adds_current_level_and_compact_rows() -> None:
    screen = build_course_repeat_level_picker_screen(
        locale="uk",
        available_levels=["A1", "B1", "C1"],
        current_level="B1",
    )

    assert screen.screen_id == "course:repeat"
    assert "Поточний рівень: B1" in screen.text
    assert [button.action for button in screen.buttons] == [
        "m:course:repeat:A1",
        "m:course:repeat:B1",
        "m:course:repeat:C1",
        "m:menu",
    ]
    assert screen.metadata == {"button_row_widths": [2, 1, 1]}


def test_build_course_repeat_level_picker_screen_handles_missing_current_level() -> None:
    screen = build_course_repeat_level_picker_screen(
        locale="uk",
        available_levels=["A1"],
        current_level=None,
    )

    assert "Поточний рівень" not in screen.text
    assert [button.action for button in screen.buttons] == ["m:course:repeat:A1", "m:menu"]
    assert screen.metadata == {"button_row_widths": [1, 1]}


def test_build_course_completed_screen_offers_course_repeat() -> None:
    screen = build_course_completed_screen(locale="uk")

    assert screen.screen_id == "course:completed"
    assert "Ви завершили всі рівні." in screen.text
    assert [button.action for button in screen.buttons] == ["m:course:repeat", "m:menu"]
    assert screen.metadata == {"buttons_per_row": 1}


def test_build_lower_levels_suggestion_screen_offers_unfinished_levels() -> None:
    screen = build_lower_levels_suggestion_screen(locale="uk", levels=["A1", "B1"])

    assert screen.screen_id == "course:lower-levels"
    assert [button.action for button in screen.buttons] == ["m:course:repeat:A1", "m:course:repeat:B1", "m:menu"]
    assert "A1" in screen.buttons[0].text
    assert "B1" in screen.buttons[1].text
    assert screen.metadata == {"buttons_per_row": 1}
