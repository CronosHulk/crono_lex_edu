from __future__ import annotations

import html
from typing import Any

from app.application.client_ui.choice_controls import (
    build_button_row_widths,
    build_single_choice_label,
)
from app.contracts import ButtonModel, ScreenModel
from app.i18n import translate
from app.reference.scheduling import format_hour_label
from app.reference.service import format_count_text
from app.validators.google_docs import mask_google_doc_url


def build_settings_screen(
    *,
    locale: str,
    profile: dict[str, Any] | None,
    reminder_days_suffix: str,
    notice: str | None = None,
) -> ScreenModel:
    reminder_hour = profile.get("daily_reminder_hour") if profile else None
    lines = [translate(locale, "settings_title")]
    if notice:
        lines.append(notice)
    lines.append(translate(locale, "menu_level_line", level=profile.get("language_level_title") if profile else "—"))
    lines.append(
        translate(
            locale,
            "menu_word_count_line",
            count_text=format_count_text(locale, profile.get("words_per_session", 10) if profile else 10),
        )
    )
    lines.append(
        translate(
            locale,
            "menu_reminder_line",
            time=format_hour_label(reminder_hour) if reminder_hour is not None else translate(locale, "reminder_not_set"),
            days_suffix=reminder_days_suffix,
        )
    )
    lines.append(
        translate(
            locale,
            "import_words_bound_doc_notice" if profile and profile.get("import_google_doc_id") else "import_words_bound_doc_missing",
            source=html.escape(mask_google_doc_url(str(profile.get("import_google_doc_id")))) if profile and profile.get("import_google_doc_id") else "",
        )
    )
    if profile and profile.get("import_google_doc_last_error"):
        lines.append(
            translate(
                locale,
                "import_words_last_error_notice",
                error=html.escape(str(profile.get("import_google_doc_last_error"))),
            )
        )
    return ScreenModel(
        screen_id="menu:settings",
        text="\n\n".join(lines),
        buttons=[
            ButtonModel(action="m:levels", text=translate(locale, "menu_select_level")),
            ButtonModel(action="m:modes", text=translate(locale, "menu_word_count_button")),
            ButtonModel(action="m:n", text=translate(locale, "menu_notifications_button")),
            ButtonModel(action="m:i", text=translate(locale, "menu_import_words_button")),
            ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")),
        ],
        keyboard_type="inline",
        metadata={"buttons_per_row": 1},
    )


def build_level_menu_screen(
    *,
    locale: str,
    current_level: str | None,
    available_levels: list[str],
    notice: str | None = None,
) -> ScreenModel:
    lines = [translate(locale, "menu_level_prompt")]
    if notice:
        lines.append(notice)
    lines.append(translate(locale, "menu_level_line", level=current_level or "—"))
    buttons = [
        ButtonModel(action=f"m:l:{level}", text=build_single_choice_label(level, level == current_level))
        for level in available_levels
    ]
    buttons.append(ButtonModel(action="m:settings", text=translate(locale, "menu_back")))
    buttons.append(ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")))
    return ScreenModel(
        screen_id="menu:levels",
        text="\n\n".join(lines),
        buttons=buttons,
        keyboard_type="inline",
        metadata={"button_row_widths": build_button_row_widths(len(available_levels), trailing_full_width_buttons=2)},
    )


def build_mode_menu_screen(
    *,
    locale: str,
    words_count: int,
    words_per_session_options: tuple[int, ...],
    notice: str | None = None,
) -> ScreenModel:
    lines = [translate(locale, "menu_mode_prompt")]
    if notice:
        lines.append(notice)
    lines.append(translate(locale, "menu_word_count_line", count_text=format_count_text(locale, words_count)))
    buttons = [
        ButtonModel(
            action=f"m:w:{count}",
            text=build_single_choice_label(
                translate(locale, "menu_word_count_option", count_text=format_count_text(locale, count)),
                count == words_count,
            ),
        )
        for count in words_per_session_options
    ]
    buttons.append(ButtonModel(action="m:settings", text=translate(locale, "menu_back")))
    buttons.append(ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")))
    return ScreenModel(
        screen_id="menu:modes",
        text="\n\n".join(lines),
        buttons=buttons,
        keyboard_type="inline",
        metadata={"button_row_widths": build_button_row_widths(len(words_per_session_options), trailing_full_width_buttons=2)},
    )
