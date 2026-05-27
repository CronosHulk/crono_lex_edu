from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.data_access.user_dictionary_constants import (
    USER_WORD_LEARNED,
    USER_WORD_LEARNING,
    USER_WORD_NEEDS_WORK,
    USER_WORD_PRIORITY_CONSUMED,
    USER_WORD_PRIORITY_INTRODUCED,
    USER_WORD_PRIORITY_NONE,
    USER_WORD_PRIORITY_PENDING,
)
from app.domain.user_dictionary.constants import (
    USER_WORD_ASSIGNMENT_ARCHIVED as USER_WORD_ASSIGNMENT_ARCHIVED,
)
from app.domain.user_dictionary.constants import (
    USER_WORD_ASSIGNMENT_AVAILABLE as USER_WORD_ASSIGNMENT_AVAILABLE,
)
from app.domain.user_dictionary.constants import (
    USER_WORD_ASSIGNMENT_HIDDEN as USER_WORD_ASSIGNMENT_HIDDEN,
)
from app.domain.user_dictionary.constants import (
    USER_WORD_ASSIGNMENT_WAITING as USER_WORD_ASSIGNMENT_WAITING,
)
from app.domain.user_dictionary.constants import (
    USER_WORD_SOURCE_CORE as USER_WORD_SOURCE_CORE,
)
from app.domain.user_dictionary.constants import (
    USER_WORD_SOURCE_USER as USER_WORD_SOURCE_USER,
)
from app.helpers.priority_rank import priority_rank_from_datetime
from app.models import UserWordAssignment

SUPPRESSED_ASSIGNMENT_STATUSES = {
    USER_WORD_ASSIGNMENT_ARCHIVED,
    USER_WORD_ASSIGNMENT_HIDDEN,
}


def normalize_user_word_source(value: str) -> str:
    source = str(value or "").strip().lower()
    if source not in {USER_WORD_SOURCE_CORE, USER_WORD_SOURCE_USER}:
        raise ValueError("word_source must be one of: core, user")
    return source


def normalize_learning_state(value: str | None) -> str:
    state = str(value or USER_WORD_LEARNING).strip().lower()
    if state not in {USER_WORD_LEARNING, USER_WORD_NEEDS_WORK, USER_WORD_LEARNED}:
        raise ValueError("learning_state must be one of: learning, needs_work, learned")
    return state


def normalize_priority_state(value: str | None) -> str:
    state = str(value or USER_WORD_PRIORITY_NONE).strip().lower()
    if state not in {
        USER_WORD_PRIORITY_NONE,
        USER_WORD_PRIORITY_PENDING,
        USER_WORD_PRIORITY_INTRODUCED,
        USER_WORD_PRIORITY_CONSUMED,
    }:
        raise ValueError("priority_state must be one of: none, pending, introduced, consumed")
    return state


def user_word_assignment_to_dict(row: UserWordAssignment) -> dict[str, Any]:
    return {
        "id": row.id,
        "level_run_id": row.last_level_run_id,
        "user_uuid": str(row.user_uuid),
        "user_id": str(row.user_uuid),
        "word_source": row.word_source,
        "word_id": row.word_id,
        "status": row.status,
        "priority_rank": int(row.priority_rank or 0),
        "priority_state": normalize_priority_state(getattr(row, "priority_state", None)),
        "is_known": bool(row.is_known),
        "learning_state": row.learning_state,
        "control_success_streak": int(row.control_success_streak or 0),
        "review_priority": int(row.review_priority or 0),
        "last_level_run_id": row.last_level_run_id,
        "last_completed": row.last_completed,
        "last_seen_at": getattr(row, "last_seen_at", None),
        "last_reviewed_at": getattr(row, "last_reviewed_at", None),
        "next_review_at": row.next_review_at,
        "review_stage": int(getattr(row, "review_stage", 0) or 0),
        "mistake_count": int(getattr(row, "mistake_count", 0) or 0),
        "import_job_id": row.import_job_id,
        "import_item_id": row.import_item_id,
        "created": row.created,
        "updated": row.updated,
    }


def count_assignments_for_word(session, *, word_source: str, word_id: int) -> int:
    normalized_source = normalize_user_word_source(word_source)
    return int(
        session.scalar(
            select(func.count(UserWordAssignment.id)).where(
                UserWordAssignment.word_source == normalized_source,
                UserWordAssignment.word_id == int(word_id),
            )
        )
        or 0
    )


def mark_assignments_available_for_entry(session, entry_id: int, *, current_time: datetime) -> int:
    rows = session.scalars(
        select(UserWordAssignment).where(
            UserWordAssignment.word_source == USER_WORD_SOURCE_USER,
            UserWordAssignment.word_id == int(entry_id),
            UserWordAssignment.status == USER_WORD_ASSIGNMENT_WAITING,
        )
    ).all()
    for row in rows:
        row.status = USER_WORD_ASSIGNMENT_AVAILABLE
        if not row.priority_rank:
            row.priority_rank = priority_rank_from_datetime(current_time)
        row.updated = current_time
    return len(rows)


def archive_assignments_for_entry(session, entry_id: int, *, current_time: datetime) -> int:
    rows = session.scalars(
        select(UserWordAssignment).where(
            UserWordAssignment.word_source == USER_WORD_SOURCE_USER,
            UserWordAssignment.word_id == int(entry_id),
            UserWordAssignment.status != USER_WORD_ASSIGNMENT_ARCHIVED,
        )
    ).all()
    for row in rows:
        row.status = USER_WORD_ASSIGNMENT_ARCHIVED
        row.updated = current_time
    return len(rows)


def create_assignment(
    session,
    *,
    user_uuid: UUID,
    word_source: str,
    word_id: int,
    current_time: datetime,
    status: str = USER_WORD_ASSIGNMENT_AVAILABLE,
    import_job_id: int | None = None,
    import_item_id: int | None = None,
    priority_rank: int | None = None,
) -> dict[str, Any]:
    normalized_source = normalize_user_word_source(word_source)
    resolved_priority_rank = priority_rank_from_datetime(current_time) if priority_rank is None else int(priority_rank)
    row = _find_assignment(
        session,
        user_uuid=user_uuid,
        word_source=normalized_source,
        word_id=int(word_id),
    )
    if row is None:
        row = UserWordAssignment(
            user_uuid=user_uuid,
            word_source=normalized_source,
            word_id=int(word_id),
            status=status,
            priority_rank=resolved_priority_rank,
            priority_state=USER_WORD_PRIORITY_PENDING if resolved_priority_rank > 0 else USER_WORD_PRIORITY_NONE,
            learning_state=USER_WORD_LEARNING,
            is_known=False,
            control_success_streak=0,
            review_priority=0,
            review_stage=0,
            mistake_count=0,
            import_job_id=import_job_id,
            import_item_id=import_item_id,
            created=current_time,
            updated=current_time,
        )
        try:
            with session.begin_nested():
                session.add(row)
                session.flush()
        except IntegrityError:
            row = _find_assignment(
                session,
                user_uuid=user_uuid,
                word_source=normalized_source,
                word_id=int(word_id),
            )
            if row is None:
                raise
        else:
            return user_word_assignment_to_dict(row)
    _touch_assignment(
        row,
        status=status,
        resolved_priority_rank=resolved_priority_rank,
        import_job_id=import_job_id,
        import_item_id=import_item_id,
        current_time=current_time,
    )
    return user_word_assignment_to_dict(row)


def _find_assignment(
    session,
    *,
    user_uuid: UUID,
    word_source: str,
    word_id: int,
) -> UserWordAssignment | None:
    return session.scalar(
        select(UserWordAssignment)
        .where(
            UserWordAssignment.user_uuid == user_uuid,
            UserWordAssignment.word_source == word_source,
            UserWordAssignment.word_id == int(word_id),
        )
        .limit(1)
    )


def _touch_assignment(
    row: UserWordAssignment,
    *,
    status: str,
    resolved_priority_rank: int,
    import_job_id: int | None,
    import_item_id: int | None,
    current_time: datetime,
) -> None:
    row.status = _resolve_assignment_status(row.status, status)
    row.priority_rank = max(int(row.priority_rank or 0), resolved_priority_rank)
    if row.priority_rank > 0 and normalize_priority_state(getattr(row, "priority_state", None)) == USER_WORD_PRIORITY_NONE:
        row.priority_state = USER_WORD_PRIORITY_PENDING
    if row.status == USER_WORD_ASSIGNMENT_AVAILABLE:
        row.is_known = False
        if row.learning_state == USER_WORD_LEARNED:
            row.learning_state = USER_WORD_LEARNING
            if normalize_priority_state(getattr(row, "priority_state", None)) == USER_WORD_PRIORITY_CONSUMED:
                row.priority_state = USER_WORD_PRIORITY_PENDING
        elif row.learning_state is None:
            row.learning_state = USER_WORD_LEARNING
    row.import_job_id = import_job_id if import_job_id is not None else row.import_job_id
    row.import_item_id = import_item_id if import_item_id is not None else row.import_item_id
    row.updated = current_time


def _resolve_assignment_status(current_status: str | None, requested_status: str) -> str:
    current = current_status or USER_WORD_ASSIGNMENT_AVAILABLE
    if current in SUPPRESSED_ASSIGNMENT_STATUSES:
        return current
    if requested_status == USER_WORD_ASSIGNMENT_AVAILABLE or current == USER_WORD_ASSIGNMENT_AVAILABLE:
        return USER_WORD_ASSIGNMENT_AVAILABLE
    return USER_WORD_ASSIGNMENT_WAITING


def list_assignments_for_user(session, user_uuid: UUID, *, status: str | None = None) -> list[dict[str, Any]]:
    filters = [UserWordAssignment.user_uuid == user_uuid]
    if status:
        filters.append(UserWordAssignment.status == status)
    rows = session.scalars(
        select(UserWordAssignment)
        .where(*filters)
        .order_by(UserWordAssignment.priority_rank.desc(), UserWordAssignment.updated.desc(), UserWordAssignment.id.desc())
    ).all()
    return [user_word_assignment_to_dict(row) for row in rows]
