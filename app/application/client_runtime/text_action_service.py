from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Protocol

from app.i18n import translate
from app.reference.scheduling import HOURS_BY_PERIOD, format_hour_label


class TextActionSessionReader(Protocol):
    def get_active_session(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...


class ClientTextActionService:
    def __init__(
        self,
        learning_sessions: TextActionSessionReader,
        *,
        level_catalog_provider: Callable[[], Iterable[dict[str, Any]]],
        count_label_builder: Callable[[str, int], str],
        resume_button_text_builder: Callable[[str, dict[str, Any]], str],
        can_resume_from_menu: Callable[[dict[str, Any] | None], bool],
        single_choice_label_builder: Callable[[str, bool], str],
        words_per_session_options: Iterable[int],
    ) -> None:
        self.learning_sessions = learning_sessions
        self.level_catalog_provider = level_catalog_provider
        self.count_label_builder = count_label_builder
        self.resume_button_text_builder = resume_button_text_builder
        self.can_resume_from_menu = can_resume_from_menu
        self.single_choice_label_builder = single_choice_label_builder
        self.words_per_session_options = tuple(words_per_session_options)

    def build_text_action_map(self, telegram_user_id: int, locale: str) -> dict[str, str]:
        action_map = {
            translate(locale, "menu_select_level"): "m:levels",
            translate(locale, "menu_word_count_button"): "m:modes",
            translate(locale, "menu_notifications_button"): "m:n",
            translate(locale, "menu_import_words_button"): "m:i",
            translate(locale, "reminder_menu_set_button"): "m:n:pick",
            translate(locale, "reminder_menu_days_button"): "m:n:days",
            translate(locale, "reminder_menu_disable_button"): "m:n:disable",
            translate(locale, "menu_start_learning"): "m:s",
            translate(locale, "menu_settings_button"): "m:settings",
            translate(locale, "menu_back"): "m:menu",
            translate(locale, "menu_back_to_menu"): "m:menu",
        }
        for level in [item["title"] for item in self.level_catalog_provider()]:
            action_map[level] = f"m:l:{level}"
            action_map[self.single_choice_label_builder(level, True)] = f"m:l:{level}"
        for count in self.words_per_session_options:
            label = self.count_label_builder(locale, count)
            action_map[label] = f"m:w:{count}"
            action_map[self.single_choice_label_builder(label, True)] = f"m:w:{count}"
        for period_code in HOURS_BY_PERIOD:
            label = translate(locale, f"period_{period_code}")
            action_map[label] = f"m:n:period:{period_code}"
            action_map[self.single_choice_label_builder(label, True)] = (
                f"m:n:period:{period_code}"
            )
            for hour in HOURS_BY_PERIOD[period_code]:
                hour_label = format_hour_label(hour)
                action_map[hour_label] = f"m:n:hour:{hour}"
                action_map[self.single_choice_label_builder(hour_label, True)] = (
                    f"m:n:hour:{hour}"
                )
        active_session = self.learning_sessions.get_active_session(telegram_user_id)
        if self.can_resume_from_menu(active_session) and active_session is not None:
            action_map[self.resume_button_text_builder(locale, active_session)] = "m:r"
        return action_map
