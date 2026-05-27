from __future__ import annotations

from datetime import datetime

from telegram import InlineKeyboardMarkup

from app.bot_runtime.auto_advance import calculate_reminder_poll_sleep_seconds
from app.bot_runtime.rendering import (
    build_audio_display_filename,
    build_keyboard,
    build_screen_text,
)
from app.contracts import ButtonModel, ScreenModel


def test_build_inline_keyboard_groups_buttons_by_two() -> None:
    keyboard = build_keyboard(
        ScreenModel(
            screen_id="menu",
            text="text",
            keyboard_type="inline",
            buttons=[
                ButtonModel(action="1", text="one"),
                ButtonModel(action="2", text="two"),
                ButtonModel(action="3", text="three"),
            ],
        )
    )

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 2


def test_build_inline_keyboard_supports_single_column_layout() -> None:
    keyboard = build_keyboard(
        ScreenModel(
            screen_id="menu",
            text="text",
            buttons=[
                ButtonModel(action="1", text="one"),
                ButtonModel(action="2", text="two"),
                ButtonModel(action="3", text="three"),
            ],
            metadata={"buttons_per_row": 1},
        )
    )

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 3
    assert all(len(row) == 1 for row in keyboard.inline_keyboard)


def test_build_inline_keyboard_supports_mixed_row_widths() -> None:
    keyboard = build_keyboard(
        ScreenModel(
            screen_id="menu",
            text="text",
            buttons=[
                ButtonModel(action="1", text="one"),
                ButtonModel(action="2", text="two"),
                ButtonModel(action="3", text="three"),
                ButtonModel(action="4", text="four"),
                ButtonModel(action="5", text="back"),
                ButtonModel(action="6", text="home"),
            ],
            metadata={"button_row_widths": [2, 2, 1, 1]},
        )
    )

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert [len(row) for row in keyboard.inline_keyboard] == [2, 2, 1, 1]


def test_build_reply_keyboard_request_is_rendered_as_inline_keyboard() -> None:
    keyboard = build_keyboard(
        ScreenModel(
            screen_id="menu",
            text="text",
            keyboard_type="reply",
            buttons=[
                ButtonModel(action="1", text="one"),
                ButtonModel(action="2", text="two"),
                ButtonModel(action="3", text="three"),
            ],
        )
    )

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 2


def test_build_screen_text_merges_notice_and_main_text() -> None:
    screen_text = build_screen_text(ScreenModel(screen_id="menu", text="Основний екран", notice_text="Оновлено"))

    assert screen_text == "Оновлено\n\nОсновний екран"


def test_build_audio_display_filename_strips_numeric_prefix() -> None:
    filename = build_audio_display_filename("audio/0001_abandon.mp3")

    assert filename == "abandon.mp3"


def test_calculate_reminder_poll_sleep_seconds_targets_next_hour_boundary() -> None:
    current_time = datetime(2026, 4, 6, 19, 25, 15)

    sleep_seconds = calculate_reminder_poll_sleep_seconds(current_time)

    assert sleep_seconds == 4 * 60 + 45


def test_calculate_reminder_poll_sleep_seconds_rolls_over_after_five_minute_boundary() -> None:
    current_time = datetime(2026, 4, 6, 19, 0, 0)

    sleep_seconds = calculate_reminder_poll_sleep_seconds(current_time)

    assert sleep_seconds == 5 * 60
