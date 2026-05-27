from __future__ import annotations

from datetime import datetime, timedelta

from app.application.client_learning.progress import (
    CONTROL_REVIEW_DELAY_HOURS,
    NEEDS_WORK_REVIEW_DELAY_HOURS,
    SRS_REVIEW_INTERVAL_DAYS,
    build_regular_session_word_progress_update,
    build_wrong_quiz_answer_progress_update,
    is_due_control_review,
    word_had_any_errors,
    word_had_many_errors,
)


def test_control_review_delay_policy_is_two_days() -> None:
    assert CONTROL_REVIEW_DELAY_HOURS == 48
    assert SRS_REVIEW_INTERVAL_DAYS == (2, 4, 7, 14, 30)


def test_word_had_any_errors_detects_second_attempt_in_any_exercise() -> None:
    assert not word_had_any_errors({"en_uk_attempts": 1, "uk_en_attempts": 1}, gap_attempts=1)
    assert word_had_any_errors({"en_uk_attempts": 2, "uk_en_attempts": 1}, gap_attempts=1)
    assert word_had_any_errors({"en_uk_attempts": 1, "uk_en_attempts": 2}, gap_attempts=1)
    assert word_had_any_errors({"en_uk_attempts": 1, "uk_en_attempts": 1}, gap_attempts=2)


def test_word_had_many_errors_detects_third_attempt_in_any_exercise() -> None:
    assert not word_had_many_errors({"en_uk_attempts": 2, "uk_en_attempts": 2}, gap_attempts=2)
    assert word_had_many_errors({"en_uk_attempts": 3, "uk_en_attempts": 2}, gap_attempts=2)
    assert word_had_many_errors({"en_uk_attempts": 2, "uk_en_attempts": 3}, gap_attempts=2)
    assert word_had_many_errors({"en_uk_attempts": 2, "uk_en_attempts": 2}, gap_attempts=3)


def test_word_error_helpers_treat_missing_attempts_as_zero() -> None:
    assert not word_had_any_errors({}, gap_attempts=0)
    assert not word_had_many_errors({}, gap_attempts=0)


def test_is_due_control_review_requires_due_review_time_and_learning_state() -> None:
    now = datetime(2026, 4, 26, 12, 0, 0)

    assert is_due_control_review({"next_review_at": now, "learning_state": "learning"}, now)
    assert is_due_control_review({"next_review_at": now - timedelta(seconds=1), "learning_state": "needs_work"}, now)
    assert not is_due_control_review(None, now)
    assert not is_due_control_review({"next_review_at": now + timedelta(seconds=1), "learning_state": "learning"}, now)
    assert not is_due_control_review({"next_review_at": now, "learning_state": "learned"}, now)


def test_wrong_quiz_answer_progress_update_skips_followup_and_first_non_control_error() -> None:
    now = datetime(2026, 4, 26, 12, 0, 0)

    assert build_wrong_quiz_answer_progress_update(
        attempts=2,
        session_type="followup",
        is_control_review=True,
        current_time=now,
    ) is None
    assert build_wrong_quiz_answer_progress_update(
        attempts=1,
        session_type="regular",
        is_control_review=False,
        current_time=now,
    ) is None


def test_wrong_quiz_answer_progress_update_resets_control_review_or_raises_priority() -> None:
    now = datetime(2026, 4, 26, 12, 0, 0)

    assert build_wrong_quiz_answer_progress_update(
        attempts=1,
        session_type="regular",
        is_control_review=True,
        current_time=now,
    ) == {
        "learning_state": "needs_work",
        "control_success_streak": 0,
        "next_review_at": now + timedelta(hours=NEEDS_WORK_REVIEW_DELAY_HOURS),
        "last_reviewed_at": now,
        "mistake_count_delta": 1,
        "current_time": now,
    }
    assert build_wrong_quiz_answer_progress_update(
        attempts=2,
        session_type="regular",
        is_control_review=True,
        current_time=now,
    ) == {
        "review_priority_delta": 2,
        "learning_state": "needs_work",
        "next_review_at": now + timedelta(hours=NEEDS_WORK_REVIEW_DELAY_HOURS),
        "last_reviewed_at": now,
        "mistake_count_delta": 1,
        "current_time": now,
        "control_success_streak": 0,
    }
    assert build_wrong_quiz_answer_progress_update(
        attempts=2,
        session_type="regular",
        is_control_review=False,
        current_time=now,
    ) == {
        "review_priority_delta": 2,
        "learning_state": "needs_work",
        "next_review_at": now + timedelta(hours=NEEDS_WORK_REVIEW_DELAY_HOURS),
        "last_reviewed_at": now,
        "mistake_count_delta": 1,
        "current_time": now,
    }


def test_regular_session_word_progress_update_marks_new_word_learning_or_needs_work() -> None:
    now = datetime(2026, 4, 26, 12, 0, 0)

    assert build_regular_session_word_progress_update(
        session_word={"en_uk_attempts": 1, "uk_en_attempts": 1},
        progress=None,
        gap_attempts=1,
        current_time=now,
    ) == {
        "is_known": False,
        "learning_state": "learning",
        "control_success_streak": 1,
        "review_stage": 1,
        "completed_now": False,
        "next_review_at": now + timedelta(days=2),
        "last_reviewed_at": now,
        "current_time": now,
    }
    assert build_regular_session_word_progress_update(
        session_word={"en_uk_attempts": 3, "uk_en_attempts": 1},
        progress=None,
        gap_attempts=1,
        current_time=now,
    )["learning_state"] == "needs_work"


def test_regular_session_word_progress_update_handles_control_review_success_and_failure() -> None:
    now = datetime(2026, 4, 26, 12, 0, 0)
    progress = {"next_review_at": now, "learning_state": "learning", "control_success_streak": 1}

    assert build_regular_session_word_progress_update(
        session_word={"en_uk_attempts": 1, "uk_en_attempts": 1},
        progress=progress,
        gap_attempts=1,
        current_time=now,
    ) == {
        "is_known": False,
        "learning_state": "learning",
        "control_success_streak": 2,
        "review_stage": 2,
        "completed_now": False,
        "next_review_at": now + timedelta(days=4),
        "last_reviewed_at": now,
        "current_time": now,
    }
    assert build_regular_session_word_progress_update(
        session_word={"en_uk_attempts": 2, "uk_en_attempts": 1},
        progress=progress,
        gap_attempts=1,
        current_time=now,
    ) == {
        "is_known": False,
        "learning_state": "needs_work",
        "control_success_streak": 0,
        "review_stage": 0,
        "mistake_count_delta": 1,
        "review_priority_delta": 1,
        "next_review_at": now + timedelta(hours=NEEDS_WORK_REVIEW_DELAY_HOURS),
        "last_reviewed_at": now,
        "current_time": now,
    }


def test_regular_session_word_progress_update_marks_word_learned_after_final_srs_stage() -> None:
    now = datetime(2026, 4, 26, 12, 0, 0)
    progress = {"next_review_at": now, "learning_state": "learning", "review_stage": 4}

    assert build_regular_session_word_progress_update(
        session_word={"en_uk_attempts": 1, "uk_en_attempts": 1},
        progress=progress,
        gap_attempts=1,
        current_time=now,
    ) == {
        "is_known": True,
        "learning_state": "learned",
        "control_success_streak": 5,
        "review_stage": 5,
        "completed_now": True,
        "next_review_at": now + timedelta(days=30),
        "last_reviewed_at": now,
        "current_time": now,
    }
