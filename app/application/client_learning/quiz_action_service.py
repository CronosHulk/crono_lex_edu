from __future__ import annotations

import random
from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.application.client_learning.content import QuizPayload, build_quiz_payload
from app.application.client_learning.progress import (
    build_wrong_quiz_answer_progress_update,
    is_due_control_review,
)
from app.application.client_learning.quiz_screens import (
    build_quiz_feedback_screen,
    build_quiz_prompt_screen,
)
from app.application.client_learning.session_completion_service import (
    ClientLearningSessionCompletionService,
)
from app.application.client_learning.session_identity import resolve_runtime_telegram_user_id
from app.contracts import ScreenModel
from app.reference.learning_flow import (
    FINAL_QUIZ_STAGE,
    NEXT_READY_STAGE,
    READY_STAGE_TO_QUIZ_STAGE,
)

TimeProvider = Callable[[], datetime]
SessionScreenRenderer = Callable[[dict[str, Any] | None, str], ScreenModel]
ReadyScreenBuilder = Callable[[dict[str, Any], str], ScreenModel]
SummaryScreenBuilder = Callable[..., ScreenModel]
QuizQueueRandomizer = Callable[[list[int]], list[int]]


def randomize_quiz_stage_queue(queue: list[int]) -> list[int]:
    randomized_queue = list(queue)
    random.shuffle(randomized_queue)
    return randomized_queue


class QuizSessionRepository(Protocol):
    def get_active_session(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...

    def get_session_words(self, session_id: int) -> list[dict[str, Any]]:
        ...

    def get_session_word(self, session_word_id: int) -> dict[str, Any] | None:
        ...

    def update_session_state(
        self,
        session_id: int,
        current_stage: str,
        stage_queue: list[int],
        stage_position: int,
    ) -> None:
        ...

    def record_answer(
        self,
        *,
        session_id: int,
        session_word_id: int,
        exercise_type: str,
        prompt_text: str,
        correct_answer: str,
        user_answer: str,
        is_correct: bool,
        attempt_no: int,
    ) -> None:
        ...

    def update_exercise_result(
        self,
        session_word_id: int,
        exercise_type: str,
        attempts: int,
        is_correct: bool,
    ) -> None:
        ...

    def complete_session(self, session_id: int) -> None:
        ...


class QuizProgressRepository(Protocol):
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


class SimilarWordRepository(Protocol):
    def find_similar_words(
        self,
        word_id: int,
        level_id: int,
        excluded_word_ids: list[int],
        limit: int,
        *,
        word_source: str = "core",
        telegram_user_id: int | None = None,
    ) -> list[dict[str, Any]]:
        ...


class ClientLearningQuizActionService:
    def __init__(
        self,
        learning_sessions: QuizSessionRepository,
        learning_progress: QuizProgressRepository,
        similar_words: SimilarWordRepository,
        *,
        current_time: TimeProvider,
        render_session_screen: SessionScreenRenderer,
        build_ready_screen: ReadyScreenBuilder,
        build_summary_screen: SummaryScreenBuilder,
        session_completion: ClientLearningSessionCompletionService | None = None,
        quiz_queue_randomizer: QuizQueueRandomizer = randomize_quiz_stage_queue,
    ) -> None:
        self.learning_sessions = learning_sessions
        self.learning_progress = learning_progress
        self.similar_words = similar_words
        self.current_time = current_time
        self.render_session_screen = render_session_screen
        self.build_ready_screen = build_ready_screen
        self.build_summary_screen = build_summary_screen
        self.quiz_queue_randomizer = quiz_queue_randomizer
        self.session_completion = session_completion or ClientLearningSessionCompletionService(
            learning_sessions,
            learning_progress,
            current_time=current_time,
        )

    def handle_answer_action(
        self,
        active_session: dict[str, Any],
        locale: str,
        session_word_id: int | None,
        option_index: int | None,
        *,
        telegram_user_id: int | None = None,
    ) -> ScreenModel:
        if session_word_id is None or option_index is None:
            return self.render_session_screen(active_session, locale)
        return self.handle_answer(
            active_session,
            locale,
            session_word_id,
            option_index,
            telegram_user_id=telegram_user_id,
        )

    def start_next_stage(
        self,
        session: dict[str, Any],
        locale: str,
        *,
        telegram_user_id: int | None = None,
    ) -> ScreenModel:
        resolved_telegram_user_id = _resolve_telegram_user_id(session, telegram_user_id)
        current_stage = str(session.get("current_stage") or "")
        if current_stage not in READY_STAGE_TO_QUIZ_STAGE:
            refreshed = self.learning_sessions.get_active_session(resolved_telegram_user_id)
            return self.render_session_screen(refreshed, locale)
        next_stage = READY_STAGE_TO_QUIZ_STAGE[current_stage]
        queue = [
            row["session_word_id"]
            for row in self.learning_sessions.get_session_words(session["id"])
            if row.get("card_status") != "known"
        ]
        queue = self.quiz_queue_randomizer(queue)
        self.learning_sessions.update_session_state(session["id"], next_stage, queue, 0)
        refreshed = self.learning_sessions.get_active_session(resolved_telegram_user_id)
        return self.render_screen(refreshed, locale, telegram_user_id=resolved_telegram_user_id)

    def render_screen(
        self,
        session: dict[str, Any],
        locale: str,
        notice: str | None = None,
        *,
        telegram_user_id: int | None = None,
    ) -> ScreenModel:
        resolved_telegram_user_id = _resolve_telegram_user_id(session, telegram_user_id)
        queue = session["stage_queue_json"]
        position = session["stage_position"]
        if position >= len(queue):
            if session["current_stage"] == FINAL_QUIZ_STAGE:
                self.session_completion.complete_session(resolved_telegram_user_id, session)
                return self.build_summary_screen(
                    session["id"],
                    locale,
                    notice=notice,
                    telegram_user_id=resolved_telegram_user_id,
                )

            next_ready_stage = NEXT_READY_STAGE[session["current_stage"]]
            self.learning_sessions.update_session_state(session["id"], next_ready_stage, [], 0)
            refreshed = self.learning_sessions.get_active_session(resolved_telegram_user_id)
            return self.build_ready_screen(refreshed, locale)

        session_word_id = queue[position]
        session_word = self.learning_sessions.get_session_word(session_word_id)
        if session_word is None:
            self.session_completion.complete_session(resolved_telegram_user_id, session)
            return self.build_summary_screen(session["id"], locale, telegram_user_id=resolved_telegram_user_id)

        quiz = self.build_quiz_payload(
            session,
            session_word,
            locale,
            telegram_user_id=resolved_telegram_user_id,
        )
        session_words_by_id = {
            row["session_word_id"]: row for row in self.learning_sessions.get_session_words(session["id"])
        }
        return build_quiz_prompt_screen(
            session=session,
            locale=locale,
            quiz=quiz,
            session_word_id=session_word_id,
            queue=queue,
            position=position,
            session_words_by_id=session_words_by_id,
            notice=notice,
        )

    def handle_answer(
        self,
        session: dict[str, Any],
        locale: str,
        session_word_id: int,
        option_index: int,
        *,
        max_options: int | None = None,
        telegram_user_id: int | None = None,
    ) -> ScreenModel:
        resolved_telegram_user_id = _resolve_telegram_user_id(session, telegram_user_id)
        queue = list(session["stage_queue_json"])
        position = int(session.get("stage_position", 0))
        if position >= len(queue) or queue[position] != session_word_id:
            refreshed = self.learning_sessions.get_active_session(resolved_telegram_user_id)
            return self.render_session_screen(refreshed, locale)
        session_word = self.learning_sessions.get_session_word(session_word_id)
        if session_word is None or session_word.get("session_id") != session["id"]:
            return self.build_summary_screen(session["id"], locale, telegram_user_id=resolved_telegram_user_id)

        quiz = self.build_quiz_payload(
            session,
            session_word,
            locale,
            max_options=max_options,
            telegram_user_id=resolved_telegram_user_id,
        )
        if option_index < 0 or option_index >= len(quiz.options):
            return self.render_session_screen(
                self.learning_sessions.get_active_session(resolved_telegram_user_id),
                locale,
            )
        selected_answer = quiz.options[option_index]
        is_correct = selected_answer == quiz.correct_answer
        attempts_field = f"{quiz.exercise_type}_attempts"
        attempts = session_word[attempts_field] + 1

        self.learning_sessions.record_answer(
            session_id=session["id"],
            session_word_id=session_word_id,
            exercise_type=quiz.exercise_type,
            prompt_text=quiz.prompt_text,
            correct_answer=quiz.correct_answer,
            user_answer=selected_answer,
            is_correct=is_correct,
            attempt_no=attempts,
        )
        self.learning_sessions.update_exercise_result(session_word_id, quiz.exercise_type, attempts, is_correct)

        current_time = self.current_time()
        progress = self.learning_progress.get(
            session_word["word_id"],
            level_run_id=session["level_run_id"],
            word_source=session_word.get("word_source", "core"),
        )
        control_review_due = is_due_control_review(progress, current_time)
        if is_correct:
            if quiz.exercise_type == "gap" and session.get("session_type") != "followup":
                self.session_completion.apply_regular_session_word_progress(
                    resolved_telegram_user_id,
                    session,
                    session_word,
                    gap_attempts=attempts,
                )
        else:
            queue.append(session_word_id)
            update_kwargs = build_wrong_quiz_answer_progress_update(
                attempts=attempts,
                session_type=session.get("session_type"),
                is_control_review=control_review_due,
                current_time=current_time,
            )
            if update_kwargs is not None:
                self.learning_progress.update(
                    resolved_telegram_user_id,
                    session_word["word_id"],
                    word_source=session_word.get("word_source", "core"),
                    level_run_id=session["level_run_id"],
                    **update_kwargs,
                )

        self.learning_sessions.update_session_state(
            session_id=session["id"],
            current_stage=session["current_stage"],
            stage_queue=queue,
            stage_position=session["stage_position"] + 1,
        )
        return self.build_feedback_screen(
            session=session,
            locale=locale,
            quiz=quiz,
            session_word_id=session_word_id,
            selected_index=option_index,
            is_correct=is_correct,
            attempts=attempts,
        )

    def build_quiz_payload(
        self,
        session: dict[str, Any],
        session_word: dict[str, Any],
        locale: str,
        *,
        max_options: int | None = None,
        telegram_user_id: int | None = None,
    ) -> QuizPayload:
        resolved_telegram_user_id = telegram_user_id if telegram_user_id is not None else session.get("telegram_user_id")
        distractors = self.similar_words.find_similar_words(
            word_id=session_word["word_id"],
            level_id=session_word.get("level_id") or session["language_level_id"],
            excluded_word_ids=[session_word["word_id"]],
            limit=6,
            word_source=session_word.get("word_source", "core"),
            telegram_user_id=resolved_telegram_user_id,
        )
        return build_quiz_payload(
            stage=session["current_stage"],
            session_word=session_word,
            distractors=distractors,
            locale=locale,
            max_options=max_options,
        )

    def build_feedback_screen(
        self,
        *,
        session: dict[str, Any],
        locale: str,
        quiz: QuizPayload,
        session_word_id: int,
        selected_index: int,
        is_correct: bool,
        attempts: int,
    ) -> ScreenModel:
        return build_quiz_feedback_screen(
            session=session,
            locale=locale,
            quiz=quiz,
            session_word_id=session_word_id,
            selected_index=selected_index,
            is_correct=is_correct,
            attempts=attempts,
            session_word=self.learning_sessions.get_session_word(session_word_id),
            session_words=self.learning_sessions.get_session_words(session["id"]),
        )


def _resolve_telegram_user_id(session: dict[str, Any], explicit_value: int | None) -> int:
    return resolve_runtime_telegram_user_id(session, explicit_value)
