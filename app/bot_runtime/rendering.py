from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.contracts import ScreenModel
from app.storage.audio import AudioStorageProvider


def build_keyboard(screen: ScreenModel) -> InlineKeyboardMarkup | None:
    if not screen.buttons:
        return None
    button_row_widths = screen.metadata.get("button_row_widths")
    if isinstance(button_row_widths, list) and button_row_widths:
        rows = []
        button_index = 0
        for row_width in button_row_widths:
            if not isinstance(row_width, int) or row_width <= 0:
                continue
            row_buttons = screen.buttons[button_index : button_index + row_width]
            if not row_buttons:
                break
            rows.append([build_inline_button(button) for button in row_buttons])
            button_index += len(row_buttons)
        if button_index < len(screen.buttons):
            remaining_buttons = screen.buttons[button_index:]
            buttons_per_row = max(int(screen.metadata.get("buttons_per_row", 2)), 1)
            for offset in range(0, len(remaining_buttons), buttons_per_row):
                rows.append(
                    [
                        build_inline_button(button) for button in remaining_buttons[offset : offset + buttons_per_row]
                    ]
                )
        return InlineKeyboardMarkup(rows)
    buttons_per_row = max(int(screen.metadata.get("buttons_per_row", 2)), 1)
    rows = []
    current_row = []
    for button in screen.buttons:
        current_row.append(build_inline_button(button))
        if len(current_row) == buttons_per_row:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    return InlineKeyboardMarkup(rows)


def build_inline_button(button) -> InlineKeyboardButton:
    if button.url:
        return InlineKeyboardButton(button.text, url=button.url)
    return InlineKeyboardButton(button.text, callback_data=button.action)


def build_screen_text(screen: ScreenModel) -> str:
    if screen.notice_text:
        return f"{screen.notice_text}\n\n{screen.text}"
    return screen.text


def build_audio_display_filename(audio_path: str) -> str:
    original_name = Path(audio_path).name
    stem = Path(original_name).stem
    suffix = Path(original_name).suffix
    prefix, separator, remainder = stem.partition("_")
    if separator and prefix.isdigit() and remainder:
        return f"{remainder}{suffix}"
    return original_name


def open_audio_binary(
    audio_path: str,
    storage_provider: AudioStorageProvider,
) -> BinaryIO:
    return storage_provider.open_binary(audio_path)
