from __future__ import annotations

from typing import Any, Protocol

from app.reference.service import AppReference


class LearningLevelRepository(Protocol):
    def save_language_level(self, telegram_user_id: int, level_title: str) -> None:
        ...

    def create(self, telegram_user_id: int, level_id: int) -> dict[str, Any]:
        ...


class ClientLearningLevelRunService:
    def __init__(self, learning_levels: LearningLevelRepository, reference: AppReference) -> None:
        self.learning_levels = learning_levels
        self.reference = reference

    def get_level_by_title(self, level_title: str) -> dict[str, Any] | None:
        return self.reference.get_level_by_title(level_title)

    def get_level_by_id(self, level_id: int) -> dict[str, Any] | None:
        return self.reference.get_level_by_id(level_id)

    def restart_level_run(self, telegram_user_id: int, level_title: str) -> dict[str, Any]:
        level = self.get_level_by_title(level_title)
        if level is None:
            raise ValueError(f"Unknown level title: {level_title}")
        self.learning_levels.save_language_level(telegram_user_id, level_title)
        return self.learning_levels.create(telegram_user_id, level["id"])
