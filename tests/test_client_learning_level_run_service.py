from __future__ import annotations

from typing import Any

import pytest

from app.application.client_learning.level_run_service import ClientLearningLevelRunService


class FakeLearningLevels:
    def __init__(self) -> None:
        self.saved_levels: list[dict[str, Any]] = []
        self.created_runs: list[dict[str, Any]] = []

    def save_language_level(self, telegram_user_id: int, level_title: str) -> None:
        self.saved_levels.append({"telegram_user_id": telegram_user_id, "level_title": level_title})

    def create(self, telegram_user_id: int, language_level_id: int) -> dict[str, Any]:
        run = {"id": 501, "telegram_user_id": telegram_user_id, "language_level_id": language_level_id}
        self.created_runs.append(run)
        return run


class FakeReference:
    def __init__(self) -> None:
        self.levels = {
            "A1": {"id": 1, "title": "A1"},
            "B1": {"id": 3, "title": "B1"},
        }

    def get_level_by_title(self, level_title: str) -> dict[str, Any] | None:
        return self.levels.get(level_title)

    def get_level_by_id(self, level_id: int) -> dict[str, Any] | None:
        return next((level for level in self.levels.values() if level["id"] == level_id), None)


def build_service() -> tuple[ClientLearningLevelRunService, FakeLearningLevels, FakeReference]:
    learning_levels = FakeLearningLevels()
    reference = FakeReference()
    return ClientLearningLevelRunService(learning_levels, reference), learning_levels, reference


def test_get_level_by_title_delegates_to_reference() -> None:
    service, _, _ = build_service()

    assert service.get_level_by_title("B1") == {"id": 3, "title": "B1"}
    assert service.get_level_by_title("C2") is None


def test_get_level_by_id_delegates_to_reference() -> None:
    service, _, _ = build_service()

    assert service.get_level_by_id(1) == {"id": 1, "title": "A1"}
    assert service.get_level_by_id(99) is None


def test_restart_level_run_saves_user_level_and_creates_new_run() -> None:
    service, db, _ = build_service()

    run = service.restart_level_run(telegram_user_id=42, level_title="B1")

    assert run == {"id": 501, "telegram_user_id": 42, "language_level_id": 3}
    assert db.saved_levels == [{"telegram_user_id": 42, "level_title": "B1"}]
    assert db.created_runs == [{"id": 501, "telegram_user_id": 42, "language_level_id": 3}]


def test_restart_level_run_rejects_unknown_level() -> None:
    service, db, _ = build_service()

    with pytest.raises(ValueError, match="Unknown level title: C2"):
        service.restart_level_run(telegram_user_id=42, level_title="C2")

    assert db.saved_levels == []
    assert db.created_runs == []
