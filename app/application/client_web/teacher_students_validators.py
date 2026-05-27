from __future__ import annotations

from app.application.client_web.teacher_students_errors import (
    ClientWebTeacherStudentValidationError,
)


def normalize_teacher_alias(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    if not normalized:
        return None
    if len(normalized) > 80:
        raise ClientWebTeacherStudentValidationError("teacher_alias must be at most 80 characters")
    return normalized


def normalize_group_title(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise ClientWebTeacherStudentValidationError("group title is required")
    if len(normalized) > 80:
        raise ClientWebTeacherStudentValidationError("group title must be at most 80 characters")
    return normalized
