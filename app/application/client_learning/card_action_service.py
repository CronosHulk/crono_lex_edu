from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.application.client_learning.session_identity import resolve_runtime_telegram_user_id
from app.contracts import ScreenModel

TimeProvider = Callable[[], datetime]
SessionScreenRenderer = Callable[[dict[str, Any] | None, str], ScreenModel]
ReadyScreenBuilder = Callable[[dict[str, Any], str], ScreenModel]


class LearningCardSessionRepository(Protocol):
    def get_active_session(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...

    def get_session_word(self, session_word_id: int) -> dict[str, Any] | None:
        ...

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

    def set_card_status(self, session_word_id: int, status: str) -> None:
        ...

    def replace_session_word(
        self,
        session_word_id: int,
        word_id: int,
        *,
        word_source: str = "core",
    ) -> dict[str, Any] | None:
        ...


class LearningCardProgressRepository(Protocol):
    def update(self, telegram_user_id: int, word_id: int, **kwargs: Any) -> None:
        ...


class LearningCardLessonWordSelector(Protocol):
    def select_next_lesson_word(
        self,
        telegram_user_id: int,
        level_id: int,
        excluded_word_ids: list[int],
        excluded_words: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        ...


class ClientLearningCardActionService:
    def __init__(
        self,
        learning_sessions: LearningCardSessionRepository,
        learning_progress: LearningCardProgressRepository,
        lesson_word_selection: LearningCardLessonWordSelector,
        *,
        current_time: TimeProvider,
        render_session_screen: SessionScreenRenderer,
        build_ready_screen: ReadyScreenBuilder,
    ) -> None:
        self.learning_sessions = learning_sessions
        self.learning_progress = learning_progress
        self.lesson_word_selection = lesson_word_selection
        self.current_time = current_time
        self.render_session_screen = render_session_screen
        self.build_ready_screen = build_ready_screen

    def handle_action(
        self,
        active_session: dict[str, Any],
        locale: str,
        session_word_id: int | None,
        card_action: str | None,
        *,
        telegram_user_id: int | None = None,
    ) -> ScreenModel:
        resolved_telegram_user_id = _resolve_telegram_user_id(
            active_session, telegram_user_id
        )
        if session_word_id is None or card_action not in {"known", "next", "back", "quiz"}:
            return self.render_session_screen(active_session, locale)
        word = self.learning_sessions.get_session_word(session_word_id)
        if word is None or word.get("session_id") != active_session["id"]:
            return self.render_session_screen(active_session, locale)
        session_words = self.learning_sessions.get_session_words(active_session["id"])
        current_position = int(active_session.get("stage_position", 0))
        if current_position >= len(session_words):
            return self.render_session_screen(active_session, locale)
        current_word = session_words[current_position]
        if current_word["session_word_id"] != session_word_id:
            return self.render_session_screen(active_session, locale)

        if card_action == "back":
            self.learning_sessions.update_session_state(
                session_id=active_session["id"],
                current_stage="card",
                stage_queue=[],
                stage_position=max(current_position - 1, 0),
            )
            return self.render_session_screen(
                self.learning_sessions.get_active_session(resolved_telegram_user_id),
                locale,
            )
        if card_action == "quiz":
            self.learning_sessions.update_session_state(
                session_id=active_session["id"],
                current_stage="ready_en_uk",
                stage_queue=[],
                stage_position=len(session_words),
            )
            refreshed = self.learning_sessions.get_active_session(resolved_telegram_user_id)
            refreshed["metadata"] = {"clear_previous_card": True}
            return self.build_ready_screen(refreshed, locale)

        self.learning_sessions.set_card_status(
            session_word_id, "known" if card_action == "known" else "next"
        )
        if word is not None and card_action == "known":
            self._mark_word_known(resolved_telegram_user_id, active_session, word)
            replacement = self._select_regular_replacement(
                resolved_telegram_user_id, active_session, session_words
            )
            if replacement is not None:
                self.learning_sessions.replace_session_word(
                    session_word_id,
                    replacement["id"],
                    word_source=replacement.get("word_source", "core"),
                )
                self.learning_sessions.update_session_state(
                    session_id=active_session["id"],
                    current_stage="card",
                    stage_queue=[],
                    stage_position=current_position,
                )
                return self.render_session_screen(
                    self.learning_sessions.get_active_session(resolved_telegram_user_id),
                    locale,
                )

        self.learning_sessions.update_session_state(
            session_id=active_session["id"],
            current_stage="card",
            stage_queue=[],
            stage_position=active_session["stage_position"] + 1,
        )
        return self.render_session_screen(
            self.learning_sessions.get_active_session(resolved_telegram_user_id), locale
        )

    def _mark_word_known(
        self,
        telegram_user_id: int,
        active_session: dict[str, Any],
        word: dict[str, Any],
    ) -> None:
        self.learning_progress.update(
            telegram_user_id,
            word["word_id"],
            word_source=word.get("word_source", "core"),
            level_run_id=active_session["level_run_id"],
            is_known=True,
            learning_state="learned",
            control_success_streak=2,
            completed_now=True,
            current_time=self.current_time(),
        )

    def _select_regular_replacement(
        self,
        telegram_user_id: int,
        active_session: dict[str, Any],
        session_words: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if active_session.get("session_type") != "regular":
            return None
        return self.lesson_word_selection.select_next_lesson_word(
            telegram_user_id=telegram_user_id,
            level_id=active_session["language_level_id"],
            excluded_word_ids=[row["word_id"] for row in session_words],
            excluded_words=session_words,
        )


def _resolve_telegram_user_id(
    session: dict[str, Any], explicit_value: int | None
) -> int:
    return resolve_runtime_telegram_user_id(session, explicit_value)
