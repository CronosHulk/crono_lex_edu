from __future__ import annotations

from typing import Any

from app.contracts import ButtonModel, ScreenModel
from app.i18n import translate
from app.reference.learning_flow import QUIZ_STAGES, READY_STAGES
from app.reference.service import format_count_text

RESUMABLE_SESSION_STAGES = {"card", "summary", "completed", *READY_STAGES, *QUIZ_STAGES}


def get_menu_resume_button_text(locale: str, session: dict[str, Any]) -> str:
    if session.get("current_stage") in {"summary", "completed"}:
        return translate(locale, "menu_open_summary")
    return translate(locale, "menu_resume_learning")


def can_resume_from_telegram_menu(session: dict[str, Any] | None) -> bool:
    if session is None:
        return False
    if str(session.get("current_stage") or "") not in RESUMABLE_SESSION_STAGES:
        return False
    session_words_count = session.get("session_words_count")
    if session_words_count is None:
        return True
    try:
        return int(session_words_count) > 0
    except (TypeError, ValueError):
        return False


def should_confirm_resume_choice(
    session: dict[str, Any],
    profile: dict[str, Any] | None,
) -> bool:
    if profile is None:
        return False
    if str(session.get("session_type", "regular")) != "regular":
        return False
    if session.get("current_stage") in {"summary", "completed"}:
        return False
    if session.get("language_level_id") != profile.get("language_level_id"):
        return True
    if session.get("words_target_count") != profile.get("words_per_session"):
        return True
    return False


def build_resume_choice_screen(
    *,
    locale: str,
    session: dict[str, Any],
    profile: dict[str, Any] | None,
    session_level: str,
) -> ScreenModel:
    current_level = profile.get("language_level_title") if profile else "—"
    current_words = profile.get("words_per_session", "—") if profile else "—"
    session_words = session.get("words_target_count", "—")

    lines = [
        translate(locale, "resume_choice_title"),
        translate(locale, "resume_choice_notice"),
    ]
    if session.get("language_level_id") != (
        profile.get("language_level_id") if profile else None
    ):
        lines.append(
            translate(
                locale,
                "resume_choice_level_line",
                session_level=session_level,
                current_level=current_level,
            )
        )
    if session.get("words_target_count") != (
        profile.get("words_per_session") if profile else None
    ):
        lines.append(
            translate(
                locale,
                "resume_choice_words_line",
                session_words_text=format_count_text(locale, session_words),
                current_words_text=format_count_text(locale, current_words),
            )
        )

    return ScreenModel(
        screen_id="resume:choice",
        text="\n\n".join(lines),
        buttons=[
            ButtonModel(action="m:r:continue", text=translate(locale, "resume_choice_continue_button")),
            ButtonModel(action="m:r:restart", text=translate(locale, "resume_choice_restart_button")),
            ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")),
        ],
        keyboard_type="inline",
        metadata={"buttons_per_row": 1},
    )
