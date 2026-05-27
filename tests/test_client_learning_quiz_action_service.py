from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from app.application.client_learning.quiz_action_service import ClientLearningQuizActionService
from app.contracts import ScreenModel


class FakeQuizDb:
    def __init__(self) -> None:
        self.session = {
            "id": 77,
            "telegram_user_id": 1,
            "current_stage": "quiz_en_uk",
            "stage_queue_json": [501],
            "stage_position": 0,
            "language_level_id": 3,
            "level_run_id": 9,
            "session_type": "regular",
        }
        self.session_words = [
            {
                "session_word_id": 501,
                "session_id": 77,
                "word_id": 1001,
                "word": "learn",
                "translation_uk": "вивчати",
                "translation_ru": None,
                "translation_pl": None,
                "examples_json": ["We learn daily."],
                "level_id": 3,
                "card_status": "next",
                "en_uk_attempts": 0,
                "uk_en_attempts": 0,
                "gap_attempts": 0,
                "gap_correct": False,
            },
            {
                "session_word_id": 502,
                "session_id": 77,
                "word_id": 1002,
                "word": "read",
                "translation_uk": "читати",
                "translation_ru": None,
                "translation_pl": None,
                "examples_json": ["Read more."],
                "level_id": 3,
                "card_status": "known",
                "en_uk_attempts": 0,
                "uk_en_attempts": 0,
                "gap_attempts": 0,
                "gap_correct": False,
            },
        ]
        self.session_words_by_id = {row["session_word_id"]: row for row in self.session_words}
        self.progress: dict[str, Any] | None = None
        self.state_updates: list[dict[str, Any]] = []
        self.recorded_answers: list[dict[str, Any]] = []
        self.exercise_updates: list[dict[str, Any]] = []
        self.progress_updates: list[dict[str, Any]] = []
        self.completed_sessions: list[int] = []
        self.similar_word_calls: list[dict[str, Any]] = []

    def get_active_session(self, telegram_user_id: int) -> dict[str, Any]:
        return self.session

    def get_session_words(self, session_id: int) -> list[dict[str, Any]]:
        return self.session_words

    def get_session_word(self, session_word_id: int) -> dict[str, Any] | None:
        return self.session_words_by_id.get(session_word_id)

    def update_session_state(
        self,
        session_id: int,
        current_stage: str,
        stage_queue: list[int],
        stage_position: int,
    ) -> None:
        self.session.update(
            {
                "current_stage": current_stage,
                "stage_queue_json": stage_queue,
                "stage_position": stage_position,
            }
        )
        self.state_updates.append(
            {
                "session_id": session_id,
                "current_stage": current_stage,
                "stage_queue": stage_queue,
                "stage_position": stage_position,
            }
        )

    def complete_session(self, session_id: int) -> None:
        self.completed_sessions.append(session_id)

    def find_similar_words(self, **kwargs: Any) -> list[dict[str, Any]]:
        self.similar_word_calls.append(kwargs)
        return [
            {"word": "read", "translation_uk": "читати"},
            {"word": "write", "translation_uk": "писати"},
        ]

    def record_answer(self, **kwargs: Any) -> None:
        self.recorded_answers.append(kwargs)

    def update_exercise_result(
        self,
        session_word_id: int,
        exercise_type: str,
        attempts: int,
        is_correct: bool,
    ) -> None:
        self.exercise_updates.append(
            {
                "session_word_id": session_word_id,
                "exercise_type": exercise_type,
                "attempts": attempts,
                "is_correct": is_correct,
            }
        )
        self.session_words_by_id[session_word_id][f"{exercise_type}_attempts"] = attempts
        self.session_words_by_id[session_word_id][f"{exercise_type}_correct"] = is_correct

    def get_assignment_progress(
        self,
        word_id: int,
        *,
        level_run_id: int,
        word_source: str = "core",
    ) -> dict[str, Any] | None:
        return self.progress

    def get(self, word_id: int, *, level_run_id: int, word_source: str = "core") -> dict[str, Any] | None:
        return self.get_assignment_progress(word_id, level_run_id=level_run_id, word_source=word_source)

    def update_assignment_progress(
        self,
        telegram_user_id: int,
        word_id: int,
        *,
        level_run_id: int,
        **kwargs: Any,
    ) -> None:
        self.progress_updates.append(
            {
                "telegram_user_id": telegram_user_id,
                "word_id": word_id,
                "level_run_id": level_run_id,
                **kwargs,
            }
        )

    def update(self, telegram_user_id: int, word_id: int, **kwargs: Any) -> None:
        self.update_assignment_progress(telegram_user_id, word_id, **kwargs)


class QuizCallbacks:
    def __init__(self) -> None:
        self.rendered: list[tuple[dict[str, Any] | None, str]] = []
        self.ready: list[tuple[dict[str, Any], str]] = []
        self.summary: list[dict[str, Any]] = []

    def render(self, session: dict[str, Any] | None, locale: str) -> ScreenModel:
        self.rendered.append((session, locale))
        return ScreenModel(screen_id="render", text="render")

    def build_ready(self, session: dict[str, Any], locale: str) -> ScreenModel:
        self.ready.append((session, locale))
        return ScreenModel(screen_id="ready", text="ready")

    def build_summary(
        self,
        session_id: int,
        locale: str,
        notice: str | None = None,
        *,
        telegram_user_id: int | None = None,
    ) -> ScreenModel:
        assert telegram_user_id in {None, 1}
        self.summary.append({"session_id": session_id, "locale": locale, "notice": notice})
        return ScreenModel(screen_id="summary", text="summary")


def identity_quiz_queue_randomizer(queue: list[int]) -> list[int]:
    return list(queue)


def build_service(
    db: FakeQuizDb,
    callbacks: QuizCallbacks,
    *,
    quiz_queue_randomizer: Callable[[list[int]], list[int]] = identity_quiz_queue_randomizer,
) -> ClientLearningQuizActionService:
    return ClientLearningQuizActionService(
        db,
        db,
        db,
        current_time=lambda: datetime(2026, 4, 26, 12, 0, 0),
        render_session_screen=callbacks.render,
        build_ready_screen=callbacks.build_ready,
        build_summary_screen=callbacks.build_summary,
        quiz_queue_randomizer=quiz_queue_randomizer,
    )


def test_handle_answer_action_with_missing_payload_renders_current_session() -> None:
    db = FakeQuizDb()
    callbacks = QuizCallbacks()

    screen = build_service(db, callbacks).handle_answer_action(db.session, "uk", None, 0)

    assert screen.screen_id == "render"
    assert callbacks.rendered == [(db.session, "uk")]


def test_start_next_stage_ignores_non_ready_stage() -> None:
    db = FakeQuizDb()
    callbacks = QuizCallbacks()
    db.session["current_stage"] = "card"

    screen = build_service(db, callbacks).start_next_stage(db.session, "uk")

    assert screen.screen_id == "render"
    assert callbacks.rendered == [(db.session, "uk")]


def test_start_next_stage_builds_quiz_queue_without_known_cards() -> None:
    db = FakeQuizDb()
    callbacks = QuizCallbacks()
    db.session["current_stage"] = "ready_en_uk"

    screen = build_service(db, callbacks).start_next_stage(db.session, "uk")

    assert screen.screen_id == "quiz_en_uk:501"
    assert db.state_updates[-1]["current_stage"] == "quiz_en_uk"
    assert db.state_updates[-1]["stage_queue"] == [501]


def test_start_next_stage_randomizes_non_known_queue_before_rendering_first_item() -> None:
    db = FakeQuizDb()
    callbacks = QuizCallbacks()
    db.session["current_stage"] = "ready_en_uk"
    db.session_words_by_id[503] = {
        **db.session_words_by_id[501],
        "session_word_id": 503,
        "word_id": 1003,
        "word": "write",
        "translation_uk": "писати",
        "examples_json": ["Write often."],
        "card_status": "next",
    }
    db.session_words.append(db.session_words_by_id[503])
    randomized_inputs: list[list[int]] = []

    def reverse_queue(queue: list[int]) -> list[int]:
        randomized_inputs.append(list(queue))
        return list(reversed(queue))

    screen = build_service(db, callbacks, quiz_queue_randomizer=reverse_queue).start_next_stage(db.session, "uk")

    assert randomized_inputs == [[501, 503]]
    assert db.state_updates[-1]["current_stage"] == "quiz_en_uk"
    assert db.state_updates[-1]["stage_queue"] == [503, 501]
    assert db.session["stage_queue_json"] == [503, 501]
    assert 502 not in db.session["stage_queue_json"]
    assert screen.screen_id == "quiz_en_uk:503"
    assert "write" in screen.text


def test_render_screen_advances_non_final_empty_queue_to_ready() -> None:
    db = FakeQuizDb()
    callbacks = QuizCallbacks()
    db.session.update({"current_stage": "quiz_en_uk", "stage_queue_json": [], "stage_position": 0})

    screen = build_service(db, callbacks).render_screen(db.session, "uk")

    assert screen.screen_id == "ready"
    assert db.state_updates[-1]["current_stage"] == "ready_uk_en"
    assert callbacks.ready[0][0]["current_stage"] == "ready_uk_en"


def test_render_screen_completes_final_empty_queue_with_notice() -> None:
    db = FakeQuizDb()
    callbacks = QuizCallbacks()
    db.session.update({"current_stage": "quiz_gap", "stage_queue_json": [], "stage_position": 0})

    screen = build_service(db, callbacks).render_screen(db.session, "uk", notice="done")

    assert screen.screen_id == "summary"
    assert db.completed_sessions == [77]
    assert callbacks.summary == [{"session_id": 77, "locale": "uk", "notice": "done"}]


def test_render_screen_backfills_missing_progress_for_completed_gap_words() -> None:
    db = FakeQuizDb()
    callbacks = QuizCallbacks()
    db.session.update({"current_stage": "quiz_gap", "stage_queue_json": [], "stage_position": 0})
    db.session_words_by_id[501].update({"gap_attempts": 1, "gap_correct": True})
    db.session_words_by_id[502].update({"gap_attempts": 3, "gap_correct": True})

    screen = build_service(db, callbacks).render_screen(db.session, "uk")

    assert screen.screen_id == "summary"
    assert [update["word_id"] for update in db.progress_updates] == [1001, 1002]
    assert db.progress_updates[0]["learning_state"] == "learning"
    assert db.progress_updates[1]["learning_state"] == "needs_work"


def test_render_screen_does_not_duplicate_existing_progress_on_completion() -> None:
    db = FakeQuizDb()
    callbacks = QuizCallbacks()
    db.session.update({"current_stage": "quiz_gap", "stage_queue_json": [], "stage_position": 0})
    db.session_words_by_id[501].update({"gap_attempts": 1, "gap_correct": True})
    db.progress = {"learning_state": "learning", "next_review_at": None}

    screen = build_service(db, callbacks).render_screen(db.session, "uk")

    assert screen.screen_id == "summary"
    assert db.progress_updates == []


def test_render_screen_completes_when_current_session_word_is_missing() -> None:
    db = FakeQuizDb()
    callbacks = QuizCallbacks()
    db.session_words_by_id.pop(501)

    screen = build_service(db, callbacks).render_screen(db.session, "uk", notice="ignored")

    assert screen.screen_id == "summary"
    assert db.completed_sessions == [77]
    assert callbacks.summary == [{"session_id": 77, "locale": "uk", "notice": None}]


def test_handle_answer_ignores_stale_and_invalid_callbacks() -> None:
    db = FakeQuizDb()
    callbacks = QuizCallbacks()
    service = build_service(db, callbacks)

    stale_screen = service.handle_answer(db.session, "uk", 999, 0)
    invalid_screen = service.handle_answer(db.session, "uk", 501, 99)

    assert stale_screen.screen_id == "render"
    assert invalid_screen.screen_id == "render"
    assert db.recorded_answers == []


def test_handle_answer_missing_session_word_returns_summary() -> None:
    db = FakeQuizDb()
    callbacks = QuizCallbacks()
    db.session_words_by_id[501] = {**db.session_words_by_id[501], "session_id": 88}

    screen = build_service(db, callbacks).handle_answer(db.session, "uk", 501, 0)

    assert screen.screen_id == "summary"
    assert callbacks.summary == [{"session_id": 77, "locale": "uk", "notice": None}]


def test_handle_answer_accepts_explicit_user_id_without_session_telegram_id() -> None:
    db = FakeQuizDb()
    callbacks = QuizCallbacks()
    session = {key: value for key, value in db.session.items() if key != "telegram_user_id"}
    service = build_service(db, callbacks)
    quiz = service.build_quiz_payload(session, db.session_words_by_id[501], "uk", telegram_user_id=1)
    correct_index = quiz.options.index(quiz.correct_answer)

    screen = service.handle_answer(session, "uk", 501, correct_index, telegram_user_id=1)

    assert screen.screen_id == "quiz_en_uk:501:feedback"
    assert db.similar_word_calls[-1]["telegram_user_id"] == 1


def test_handle_wrong_answer_requeues_and_updates_priority_progress() -> None:
    db = FakeQuizDb()
    callbacks = QuizCallbacks()
    db.progress = {
        "learning_state": "learning",
        "next_review_at": datetime(2026, 4, 26, 11, 0, 0),
        "control_success_streak": 1,
    }
    service = build_service(db, callbacks)
    quiz = service.build_quiz_payload(db.session, db.session_words_by_id[501], "uk")
    wrong_index = next(index for index, option in enumerate(quiz.options) if option != quiz.correct_answer)

    screen = service.handle_answer(db.session, "uk", 501, wrong_index)

    assert screen.screen_id == "quiz_en_uk:501:feedback"
    assert db.state_updates[-1]["stage_queue"] == [501, 501]
    assert db.exercise_updates == [
        {"session_word_id": 501, "exercise_type": "en_uk", "attempts": 1, "is_correct": False}
    ]
    assert db.progress_updates[0]["learning_state"] == "needs_work"
    assert db.progress_updates[0]["control_success_streak"] == 0


def test_build_quiz_payload_uses_combined_similar_lookup_for_user_source() -> None:
    db = FakeQuizDb()
    callbacks = QuizCallbacks()
    db.session_words_by_id[501]["word_source"] = "user"
    service = build_service(db, callbacks)

    quiz = service.build_quiz_payload(db.session, db.session_words_by_id[501], "uk")

    assert quiz.options
    assert db.similar_word_calls == [
        {
            "word_id": 1001,
            "level_id": 3,
            "excluded_word_ids": [1001],
            "limit": 6,
            "word_source": "user",
            "telegram_user_id": 1,
        }
    ]


def test_handle_correct_gap_answer_updates_regular_progress() -> None:
    db = FakeQuizDb()
    callbacks = QuizCallbacks()
    db.session.update({"current_stage": "quiz_gap"})
    db.session_words_by_id[501]["gap_attempts"] = 0
    db.progress = {
        "learning_state": "learning",
        "next_review_at": datetime(2026, 4, 26, 11, 0, 0),
        "control_success_streak": 1,
    }
    service = build_service(db, callbacks)
    quiz = service.build_quiz_payload(db.session, db.session_words_by_id[501], "uk")
    correct_index = quiz.options.index(quiz.correct_answer)

    screen = service.handle_answer(db.session, "uk", 501, correct_index)

    assert screen.screen_id == "quiz_gap:501:feedback"
    assert db.recorded_answers[0]["is_correct"] is True
    assert db.progress_updates[0]["learning_state"] == "learning"
    assert db.progress_updates[0]["review_stage"] == 2
    assert db.progress_updates[0]["next_review_at"] == datetime(2026, 4, 26, 12, 0, 0) + timedelta(days=4)
