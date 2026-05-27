from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.application.client_learning.session_completion_service import (
    ClientLearningSessionCompletionService,
)


class FakeCompletionSessions:
    def __init__(self) -> None:
        self.words = [
            {
                "session_word_id": 501,
                "word_id": 1001,
                "word_source": "core",
                "gap_attempts": 1,
                "gap_correct": True,
                "en_uk_attempts": 1,
                "uk_en_attempts": 1,
            }
        ]
        self.state_updates: list[dict[str, Any]] = []
        self.completed: list[int] = []

    def get_session_words(self, session_id: int) -> list[dict[str, Any]]:
        assert session_id == 77
        return self.words

    def update_session_state(
        self,
        session_id: int,
        current_stage: str,
        stage_queue: list[int],
        stage_position: int,
    ) -> None:
        self.state_updates.append(
            {
                "session_id": session_id,
                "current_stage": current_stage,
                "stage_queue": stage_queue,
                "stage_position": stage_position,
            }
        )

    def complete_session(self, session_id: int) -> None:
        self.completed.append(session_id)


class FakeCompletionProgress:
    def __init__(self) -> None:
        self.progress: dict[str, Any] | None = None
        self.updates: list[dict[str, Any]] = []

    def get(self, word_id: int, *, level_run_id: int, word_source: str = "core") -> dict[str, Any] | None:
        return self.progress

    def update(self, telegram_user_id: int, word_id: int, **kwargs: Any) -> None:
        self.updates.append({"telegram_user_id": telegram_user_id, "word_id": word_id, **kwargs})


def test_complete_session_finalizes_missing_progress_and_marks_session_completed() -> None:
    now = datetime(2026, 4, 26, 12, 0, 0)
    sessions = FakeCompletionSessions()
    progress = FakeCompletionProgress()
    service = ClientLearningSessionCompletionService(sessions, progress, current_time=lambda: now)
    session = {"id": 77, "status": "active", "current_stage": "quiz_gap", "session_type": "regular", "level_run_id": 9}

    service.complete_session(42, session)

    assert sessions.state_updates == [{"session_id": 77, "current_stage": "summary", "stage_queue": [], "stage_position": 0}]
    assert sessions.completed == [77]
    assert session["status"] == "completed"
    assert session["current_stage"] == "summary"
    assert progress.updates[0]["next_review_at"] == now + timedelta(days=2)


def test_complete_session_is_idempotent_for_completed_summary() -> None:
    sessions = FakeCompletionSessions()
    progress = FakeCompletionProgress()
    service = ClientLearningSessionCompletionService(
        sessions,
        progress,
        current_time=lambda: datetime(2026, 4, 26, 12, 0, 0),
    )
    session = {"id": 77, "status": "completed", "current_stage": "summary", "session_type": "regular", "level_run_id": 9}

    service.complete_session(42, session)

    assert sessions.state_updates == []
    assert sessions.completed == []
    assert progress.updates == []
