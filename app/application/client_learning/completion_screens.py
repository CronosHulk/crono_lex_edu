from __future__ import annotations

from app.application.client_ui.choice_controls import build_button_row_widths
from app.contracts import ButtonModel, ScreenModel
from app.i18n import translate


def build_level_completed_screen(*, locale: str, current_level: str, next_level: str) -> ScreenModel:
    lines = [
        translate(locale, "level_complete_title", level=current_level),
        translate(locale, "level_complete_next_prompt", next_level=next_level),
    ]
    return ScreenModel(
        screen_id="level:completed",
        text="\n\n".join(lines),
        buttons=[
            ButtonModel(action=f"m:level:next:{next_level}", text=translate(locale, "level_complete_next_button", level=next_level)),
            ButtonModel(action=f"m:level:repeat:{current_level}", text=translate(locale, "level_complete_repeat_button", level=current_level)),
            ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")),
        ],
        keyboard_type="inline",
        metadata={"buttons_per_row": 1},
    )


def build_course_repeat_level_picker_screen(
    *,
    locale: str,
    available_levels: list[str],
    current_level: str | None,
) -> ScreenModel:
    lines = [translate(locale, "course_repeat_prompt")]
    if current_level:
        lines.append(translate(locale, "menu_level_line", level=current_level))
    return ScreenModel(
        screen_id="course:repeat",
        text="\n\n".join(lines),
        buttons=[
            *[ButtonModel(action=f"m:course:repeat:{level}", text=level) for level in available_levels],
            ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")),
        ],
        keyboard_type="inline",
        metadata={"button_row_widths": build_button_row_widths(len(available_levels), trailing_full_width_buttons=1)},
    )


def build_course_completed_screen(*, locale: str) -> ScreenModel:
    return ScreenModel(
        screen_id="course:completed",
        text="\n\n".join(
            [
                translate(locale, "course_complete_title"),
                translate(locale, "course_complete_text"),
            ]
        ),
        buttons=[
            ButtonModel(action="m:course:repeat", text=translate(locale, "course_repeat_button")),
            ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")),
        ],
        keyboard_type="inline",
        metadata={"buttons_per_row": 1},
    )


def build_lower_levels_suggestion_screen(*, locale: str, levels: list[str]) -> ScreenModel:
    return ScreenModel(
        screen_id="course:lower-levels",
        text="\n\n".join(
            [
                translate(locale, "course_lower_levels_title"),
                translate(locale, "course_lower_levels_text"),
            ]
        ),
        buttons=[
            *[
                ButtonModel(
                    action=f"m:course:repeat:{level}",
                    text=translate(locale, "course_lower_level_button", level=level),
                )
                for level in levels
            ],
            ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")),
        ],
        keyboard_type="inline",
        metadata={"buttons_per_row": 1},
    )
