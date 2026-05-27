from __future__ import annotations

from typing import Any

from app.application.client_learning.resume import (
    can_resume_from_telegram_menu,
    get_menu_resume_button_text,
)
from app.application.client_runtime.text_action_service import ClientTextActionService
from app.application.client_ui.choice_controls import build_single_choice_label
from app.data_access.learning_sessions import LearningSessionRepository
from app.i18n import translate
from app.reference.service import format_count_text


def configure_client_text_action_runtime(service: Any, db: Any) -> None:
    learning_sessions_repo = getattr(db, "learning_sessions", None) or LearningSessionRepository(db)
    service.client_text_action_service = ClientTextActionService(
        learning_sessions_repo,
        level_catalog_provider=lambda: service.reference.language_levels(),
        count_label_builder=lambda locale, count: translate(
            locale,
            "menu_word_count_option",
            count_text=format_count_text(locale, count),
        ),
        resume_button_text_builder=lambda locale, session: get_menu_resume_button_text(
            locale, session
        ),
        can_resume_from_menu=can_resume_from_telegram_menu,
        single_choice_label_builder=build_single_choice_label,
        words_per_session_options=service.reference.words_per_session_options(),
    )
