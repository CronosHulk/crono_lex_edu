from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from app.application.client_learning.completion_screens import (
    build_course_completed_screen,
    build_course_repeat_level_picker_screen,
    build_level_completed_screen,
    build_lower_levels_suggestion_screen,
)
from app.contracts import ScreenModel
from app.i18n import translate
from app.reference.service import LEVEL_ORDER, AppReference
from app.subscriptions.learning_caps import filter_level_titles
from app.subscriptions.plans import SubscriptionEntitlements

MenuScreenBuilder = Callable[[int, str, str | None], ScreenModel]


class LearningCompletionProfileReader(Protocol):
    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...


class LearningCompletionProgressReader(Protocol):
    def get_level_word_totals(self) -> dict[int, int]:
        ...

    def get_user_level_summary(self, telegram_user_id: int, level_id: int) -> dict[str, int]:
        ...


class ClientLearningCompletionService:
    def __init__(
        self,
        user_profiles: LearningCompletionProfileReader,
        learning_progress: LearningCompletionProgressReader,
        reference: AppReference,
        *,
        build_menu_screen: MenuScreenBuilder,
        resolve_entitlements: Callable[[int], SubscriptionEntitlements | None] | None = None,
    ) -> None:
        self.user_profiles = user_profiles
        self.learning_progress = learning_progress
        self.reference = reference
        self.build_menu_screen = build_menu_screen
        self.resolve_entitlements = resolve_entitlements or (lambda _telegram_user_id: None)

    def get_level_completion_snapshot(self, telegram_user_id: int) -> dict[str, dict[str, Any]]:
        totals = self.learning_progress.get_level_word_totals()
        snapshot: dict[str, dict[str, Any]] = {}
        for level in self.reference.language_levels():
            total = totals.get(level["id"], 0)
            progress = self.learning_progress.get_user_level_summary(telegram_user_id, level["id"])
            snapshot[level["title"]] = {
                "level_id": level["id"],
                "total_words": total,
                "progress": progress,
                "has_words": total > 0,
                "is_completed": total > 0 and progress["learned_count"] >= total,
            }
        return snapshot

    def get_learnable_level_titles(self, telegram_user_id: int) -> list[str]:
        snapshot = self.get_level_completion_snapshot(telegram_user_id)
        available_titles = self.reference.available_level_titles()
        learnable_titles = [
            level for level in LEVEL_ORDER if level in available_titles and snapshot.get(level, {}).get("has_words")
        ]
        return filter_level_titles(learnable_titles, self.resolve_entitlements(telegram_user_id))

    def find_next_unfinished_higher_level(self, telegram_user_id: int, current_level_title: str) -> str | None:
        snapshot = self.get_level_completion_snapshot(telegram_user_id)
        try:
            start_index = LEVEL_ORDER.index(current_level_title)
        except ValueError:
            return None
        allowed_levels = set(filter_level_titles(LEVEL_ORDER[start_index + 1 :], self.resolve_entitlements(telegram_user_id)))
        for level in LEVEL_ORDER[start_index + 1 :]:
            if level not in allowed_levels:
                continue
            state = snapshot.get(level)
            if state is not None and state["has_words"] and not state["is_completed"]:
                return level
        return None

    def get_unfinished_lower_levels(self, telegram_user_id: int, current_level_title: str) -> list[str]:
        snapshot = self.get_level_completion_snapshot(telegram_user_id)
        try:
            stop_index = LEVEL_ORDER.index(current_level_title)
        except ValueError:
            return []
        lower_levels = [
            level
            for level in LEVEL_ORDER[:stop_index]
            if snapshot.get(level, {}).get("has_words") and snapshot.get(level, {}).get("is_completed") is False
        ]
        return filter_level_titles(lower_levels, self.resolve_entitlements(telegram_user_id))

    def build_level_completed_screen(self, locale: str, current_level: str, next_level: str) -> ScreenModel:
        return build_level_completed_screen(
            locale=locale,
            current_level=current_level,
            next_level=next_level,
        )

    def build_course_repeat_level_picker_screen(self, telegram_user_id: int, locale: str) -> ScreenModel:
        available_levels = self.get_learnable_level_titles(telegram_user_id)
        if not available_levels:
            return self.build_menu_screen(
                telegram_user_id,
                locale,
                translate(locale, "menu_no_words"),
            )
        profile = self.user_profiles.get_profile(telegram_user_id)
        current_level = str(profile["language_level_title"]) if profile and profile.get("language_level_title") else None
        return build_course_repeat_level_picker_screen(
            locale=locale,
            available_levels=available_levels,
            current_level=current_level,
        )

    def build_course_completed_screen(self, locale: str) -> ScreenModel:
        return build_course_completed_screen(locale=locale)

    def build_lower_levels_suggestion_screen(self, locale: str, levels: list[str]) -> ScreenModel:
        return build_lower_levels_suggestion_screen(locale=locale, levels=levels)
