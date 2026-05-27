from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.application.client_learning.progress import build_regular_session_word_progress_update

TimeProvider = Callable[[], datetime]


class CompletionSessionRepository(Protocol):
    def get_session_words(self, session_id: int) -> list[dict[str, Any]]:
        ...

    def update_session_state(
        self,
        session_id: int,
        current_stage: str,
        stage_queue: list[int],
        stage_position: int,
    ) -> None:
        ...

    def complete_session(self, session_id: int) -> None:
        ...


class CompletionProgressRepository(Protocol):
    def get(
        self,
        word_id: int,
        *,
        level_run_id: int,
        word_source: str = "core",
    ) -> dict[str, Any] | None:
        ...

    def update(self, telegram_user_id: int, word_id: int, **kwargs: Any) -> None:
        ...


class ClientLearningSessionCompletionService:
    def __init__(
        self,
        learning_sessions: CompletionSessionRepository,
        learning_progress: CompletionProgressRepository,
        *,
        current_time: TimeProvider,
    ) -> None:
        self.learning_sessions = learning_sessions
        self.learning_progress = learning_progress
        self.current_time = current_time

    def complete_session(self, telegram_user_id: int, session: dict[str, Any]) -> None:
        if self._is_already_completed(session):
            return
        self.finalize_regular_session_progress(telegram_user_id, session)
        self.learning_sessions.update_session_state(int(session["id"]), "summary", [], 0)
        self.learning_sessions.complete_session(int(session["id"]))
        session["status"] = "completed"
        session["current_stage"] = "summary"
        session["stage_queue_json"] = []
        session["stage_position"] = 0

    def finalize_regular_session_progress(self, telegram_user_id: int, session: dict[str, Any]) -> None:
        if session.get("session_type") == "followup" or session.get("level_run_id") is None:
            return
        for session_word in self.learning_sessions.get_session_words(int(session["id"])):
            if not session_word.get("gap_correct"):
                continue
            progress = self.learning_progress.get(
                int(session_word["word_id"]),
                level_run_id=int(session["level_run_id"]),
                word_source=session_word.get("word_source", "core"),
            )
            if progress is not None:
                continue
            self._apply_regular_session_word_progress(
                telegram_user_id,
                session,
                session_word,
                gap_attempts=max(int(session_word.get("gap_attempts") or 0), 1),
            )

    def apply_regular_session_word_progress(
        self,
        telegram_user_id: int,
        session: dict[str, Any],
        session_word: dict[str, Any],
        *,
        gap_attempts: int,
    ) -> None:
        self._apply_regular_session_word_progress(telegram_user_id, session, session_word, gap_attempts=gap_attempts)

    def _apply_regular_session_word_progress(
        self,
        telegram_user_id: int,
        session: dict[str, Any],
        session_word: dict[str, Any],
        *,
        gap_attempts: int,
    ) -> None:
        current_time = self.current_time()
        progress = self.learning_progress.get(
            int(session_word["word_id"]),
            level_run_id=int(session["level_run_id"]),
            word_source=session_word.get("word_source", "core"),
        )
        update_kwargs = build_regular_session_word_progress_update(
            session_word=session_word,
            progress=progress,
            gap_attempts=gap_attempts,
            current_time=current_time,
        )
        self.learning_progress.update(
            telegram_user_id,
            int(session_word["word_id"]),
            word_source=session_word.get("word_source", "core"),
            level_run_id=int(session["level_run_id"]),
            **update_kwargs,
        )

    def _is_already_completed(self, session: dict[str, Any]) -> bool:
        return session.get("status") == "completed" and session.get("current_stage") in {"summary", "completed"}
