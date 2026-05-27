from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from app.application.client_learning.action_payload import parse_int_or_none
from app.contracts import ScreenModel
from app.i18n import translate
from app.subscriptions.learning_caps import is_level_title_allowed, is_words_per_session_allowed
from app.subscriptions.plans import SubscriptionEntitlements

SettingsScreenBuilder = Callable[[int, str, str | None], ScreenModel]
MenuScreenBuilder = Callable[[int, str], ScreenModel]
CourseRepeatPickerBuilder = Callable[[int, str], ScreenModel]
StartLearningCallback = Callable[[int, str], ScreenModel]
RestartLevelRunCallback = Callable[[int, str], None]
LevelLookup = Callable[[str], dict[str, Any] | None]
CountTextBuilder = Callable[[str, int], str]


class LearningLevelRepository(Protocol):
    def save_language_level(self, telegram_user_id: int, level_title: str) -> None:
        ...


class UserLearningSettingsRepository(Protocol):
    def set_words_per_session(self, telegram_user_id: int, words_per_session: int) -> None:
        ...


class ClientLearningSettingsActionService:
    def __init__(
        self,
        learning_levels: LearningLevelRepository,
        user_learning_settings: UserLearningSettingsRepository,
        *,
        build_settings_screen: SettingsScreenBuilder,
        build_menu_screen: MenuScreenBuilder,
        build_course_repeat_level_picker_screen: CourseRepeatPickerBuilder,
        start_learning: StartLearningCallback,
        restart_level_run: RestartLevelRunCallback,
        get_level_by_title: LevelLookup,
        format_count_text: CountTextBuilder,
        words_per_session_options: tuple[int, ...],
        resolve_entitlements: Callable[[int], SubscriptionEntitlements | None] | None = None,
    ) -> None:
        self.learning_levels = learning_levels
        self.user_learning_settings = user_learning_settings
        self.build_settings_screen = build_settings_screen
        self.build_menu_screen = build_menu_screen
        self.build_course_repeat_level_picker_screen = build_course_repeat_level_picker_screen
        self.start_learning = start_learning
        self.restart_level_run = restart_level_run
        self.get_level_by_title = get_level_by_title
        self.format_count_text = format_count_text
        self.words_per_session_options = words_per_session_options
        self.resolve_entitlements = resolve_entitlements or (lambda _telegram_user_id: None)

    def handle_action(self, telegram_user_id: int, locale: str, action: str) -> ScreenModel | None:
        if action.startswith("m:l:"):
            return self._handle_language_level_action(telegram_user_id, locale, action)
        if action.startswith("m:w:"):
            return self._handle_words_per_session_action(telegram_user_id, locale, action)
        if action.startswith("m:level:next:"):
            return self._handle_next_level_action(telegram_user_id, locale, action)
        if action.startswith("m:level:repeat:"):
            return self._handle_repeat_level_action(telegram_user_id, locale, action)
        if action == "m:course:repeat":
            return self.build_course_repeat_level_picker_screen(telegram_user_id, locale)
        if action.startswith("m:course:repeat:"):
            return self._handle_repeat_course_level_action(telegram_user_id, locale, action)
        return None

    def _handle_language_level_action(self, telegram_user_id: int, locale: str, action: str) -> ScreenModel:
        level = action.split(":")[-1]
        if self.get_level_by_title(level) is None:
            return self.build_settings_screen(telegram_user_id, locale, None)
        if not is_level_title_allowed(level, self.resolve_entitlements(telegram_user_id)):
            return self.build_settings_screen(telegram_user_id, locale, None)
        self.learning_levels.save_language_level(telegram_user_id, level)
        return self.build_settings_screen(
            telegram_user_id,
            locale,
            translate(locale, "menu_level_saved", level=level),
        )

    def _handle_words_per_session_action(self, telegram_user_id: int, locale: str, action: str) -> ScreenModel:
        count = parse_int_or_none(action.split(":")[-1])
        if count not in self.words_per_session_options:
            return self.build_settings_screen(telegram_user_id, locale, None)
        if count is None or not is_words_per_session_allowed(count, self.resolve_entitlements(telegram_user_id)):
            return self.build_settings_screen(telegram_user_id, locale, None)
        self.user_learning_settings.set_words_per_session(telegram_user_id, count)
        return self.build_settings_screen(
            telegram_user_id,
            locale,
            translate(locale, "menu_word_count_saved", count_text=self.format_count_text(locale, count)),
        )

    def _handle_next_level_action(self, telegram_user_id: int, locale: str, action: str) -> ScreenModel:
        level = action.split(":")[-1]
        if self.get_level_by_title(level) is None:
            return self.build_menu_screen(telegram_user_id, locale)
        if not is_level_title_allowed(level, self.resolve_entitlements(telegram_user_id)):
            return self.build_menu_screen(telegram_user_id, locale)
        self.learning_levels.save_language_level(telegram_user_id, level)
        return self.start_learning(telegram_user_id, locale)

    def _handle_repeat_level_action(self, telegram_user_id: int, locale: str, action: str) -> ScreenModel:
        level = action.split(":")[-1]
        if self.get_level_by_title(level) is None:
            return self.build_menu_screen(telegram_user_id, locale)
        if not is_level_title_allowed(level, self.resolve_entitlements(telegram_user_id)):
            return self.build_menu_screen(telegram_user_id, locale)
        self.restart_level_run(telegram_user_id, level)
        return self.start_learning(telegram_user_id, locale)

    def _handle_repeat_course_level_action(self, telegram_user_id: int, locale: str, action: str) -> ScreenModel:
        level = action.split(":")[-1]
        if self.get_level_by_title(level) is None:
            return self.build_course_repeat_level_picker_screen(telegram_user_id, locale)
        if not is_level_title_allowed(level, self.resolve_entitlements(telegram_user_id)):
            return self.build_course_repeat_level_picker_screen(telegram_user_id, locale)
        self.restart_level_run(telegram_user_id, level)
        return self.start_learning(telegram_user_id, locale)
