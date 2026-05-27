from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from app.application.client_learning.settings_screens import (
    build_level_menu_screen,
    build_mode_menu_screen,
    build_settings_screen,
)
from app.contracts import ScreenModel
from app.reference.service import AppReference
from app.subscriptions.learning_caps import filter_level_rows, filter_words_per_session_options
from app.subscriptions.plans import SubscriptionEntitlements


class LearningSettingsProfileReader(Protocol):
    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...


class ClientLearningSettingsScreenService:
    def __init__(
        self,
        user_profiles: LearningSettingsProfileReader,
        reference: AppReference,
        build_days_suffix: Callable[[str, int | None, list[int]], str],
        resolve_entitlements: Callable[[int], SubscriptionEntitlements | None] | None = None,
    ) -> None:
        self.user_profiles = user_profiles
        self.reference = reference
        self.build_days_suffix = build_days_suffix
        self.resolve_entitlements = resolve_entitlements or (lambda _telegram_user_id: None)

    def build_settings_screen(self, telegram_user_id: int, locale: str, notice: str | None = None) -> ScreenModel:
        profile = self.user_profiles.get_profile(telegram_user_id)
        reminder_hour = profile.get("daily_reminder_hour") if profile else None
        reminder_weekdays = profile.get("reminder_weekdays", []) if profile else []
        return build_settings_screen(
            locale=locale,
            profile=profile,
            reminder_days_suffix=self.build_days_suffix(locale, reminder_hour, reminder_weekdays),
            notice=notice,
        )

    def build_level_menu_screen(self, telegram_user_id: int, locale: str, notice: str | None = None) -> ScreenModel:
        profile = self.user_profiles.get_profile(telegram_user_id)
        current_level = profile.get("language_level_title") if profile else None
        entitlements = self.resolve_entitlements(telegram_user_id)
        available_levels = [level["title"] for level in filter_level_rows(self.reference.language_levels(), entitlements)]
        return build_level_menu_screen(
            locale=locale,
            current_level=current_level,
            available_levels=available_levels,
            notice=notice,
        )

    def build_mode_menu_screen(self, telegram_user_id: int, locale: str, notice: str | None = None) -> ScreenModel:
        profile = self.user_profiles.get_profile(telegram_user_id)
        words_count = profile.get("words_per_session", 10) if profile else 10
        entitlements = self.resolve_entitlements(telegram_user_id)
        return build_mode_menu_screen(
            locale=locale,
            words_count=words_count,
            words_per_session_options=filter_words_per_session_options(
                self.reference.words_per_session_options(),
                entitlements,
            ),
            notice=notice,
        )
