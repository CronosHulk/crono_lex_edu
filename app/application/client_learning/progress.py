from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

CONTROL_REVIEW_DELAY_HOURS = 48
NEEDS_WORK_REVIEW_DELAY_HOURS = 6
REPEATED_NEEDS_WORK_REVIEW_DELAY_HOURS = 24
SRS_REVIEW_INTERVAL_DAYS = (2, 4, 7, 14, 30)


def next_review_stage(progress: dict[str, Any] | None) -> int:
    payload = progress or {}
    current_stage = max(int(payload.get("review_stage") or 0), int(payload.get("control_success_streak") or 0))
    return min(current_stage + 1, len(SRS_REVIEW_INTERVAL_DAYS))


def next_review_at_for_stage(stage: int, current_time: datetime) -> datetime:
    interval_index = min(max(int(stage), 1), len(SRS_REVIEW_INTERVAL_DAYS)) - 1
    return current_time + timedelta(days=SRS_REVIEW_INTERVAL_DAYS[interval_index])


def needs_work_review_at(*, attempts: int, current_time: datetime) -> datetime:
    delay_hours = REPEATED_NEEDS_WORK_REVIEW_DELAY_HOURS if attempts > 2 else NEEDS_WORK_REVIEW_DELAY_HOURS
    return current_time + timedelta(hours=delay_hours)


def word_had_any_errors(session_word: dict[str, Any], gap_attempts: int) -> bool:
    return (
        int(session_word.get("en_uk_attempts", 0)) > 1
        or int(session_word.get("uk_en_attempts", 0)) > 1
        or gap_attempts > 1
    )


def word_had_many_errors(session_word: dict[str, Any], gap_attempts: int) -> bool:
    return (
        int(session_word.get("en_uk_attempts", 0)) > 2
        or int(session_word.get("uk_en_attempts", 0)) > 2
        or gap_attempts > 2
    )


def is_due_control_review(progress: dict[str, Any] | None, current_time: datetime) -> bool:
    return (
        progress is not None
        and progress.get("next_review_at") is not None
        and progress["next_review_at"] <= current_time
        and progress.get("learning_state") in {"learning", "needs_work"}
    )


def build_wrong_quiz_answer_progress_update(
    *,
    attempts: int,
    session_type: str | None,
    is_control_review: bool,
    current_time: datetime,
) -> dict[str, Any] | None:
    if session_type == "followup":
        return None
    if attempts == 1:
        if not is_control_review:
            return None
        return {
            "learning_state": "needs_work",
            "control_success_streak": 0,
            "next_review_at": needs_work_review_at(attempts=attempts, current_time=current_time),
            "last_reviewed_at": current_time,
            "mistake_count_delta": 1,
            "current_time": current_time,
        }
    update_kwargs: dict[str, Any] = {
        "review_priority_delta": 2,
        "learning_state": "needs_work",
        "next_review_at": needs_work_review_at(attempts=attempts, current_time=current_time),
        "last_reviewed_at": current_time,
        "mistake_count_delta": 1,
        "current_time": current_time,
    }
    if is_control_review:
        update_kwargs["control_success_streak"] = 0
    return update_kwargs


def build_regular_session_word_progress_update(
    *,
    session_word: dict[str, Any],
    progress: dict[str, Any] | None,
    gap_attempts: int,
    current_time: datetime,
    control_review_delay_hours: int = CONTROL_REVIEW_DELAY_HOURS,
) -> dict[str, Any]:
    _ = control_review_delay_hours
    had_any_errors = word_had_any_errors(session_word, gap_attempts)
    attempts = max(
        int(session_word.get("en_uk_attempts", 0) or 0),
        int(session_word.get("uk_en_attempts", 0) or 0),
        int(gap_attempts or 0),
    )
    control_review = is_due_control_review(progress, current_time)

    if had_any_errors:
        return {
            "is_known": False,
            "learning_state": "needs_work",
            "control_success_streak": 0,
            "review_stage": max(int((progress or {}).get("review_stage") or 0) - 1, 0),
            "mistake_count_delta": 1,
            "review_priority_delta": 1,
            "next_review_at": needs_work_review_at(attempts=attempts, current_time=current_time),
            "last_reviewed_at": current_time,
            "current_time": current_time,
        }

    stage = next_review_stage(progress)
    review_at = next_review_at_for_stage(stage, current_time)
    is_learned = stage >= len(SRS_REVIEW_INTERVAL_DAYS)
    learning_state = "learned" if is_learned else "learning"
    success_update = {
        "is_known": is_learned,
        "learning_state": learning_state,
        "control_success_streak": stage,
        "review_stage": stage,
        "completed_now": is_learned,
        "next_review_at": review_at,
        "last_reviewed_at": current_time,
        "current_time": current_time,
    }

    if control_review:
        return success_update

    return success_update
