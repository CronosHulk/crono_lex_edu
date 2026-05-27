from __future__ import annotations

from fastapi import HTTPException

from app.application.admin.exercise_texts.errors import (
    AdminExerciseTextGenerationError,
    AdminExerciseTextServiceError,
    AdminExerciseTextTTSError,
    admin_exercise_text_generation_error_status_code,
    admin_exercise_text_service_error_status_code,
    admin_exercise_text_tts_error_status_code,
)


def admin_exercise_text_service_http_exception(error: AdminExerciseTextServiceError) -> HTTPException:
    return HTTPException(status_code=admin_exercise_text_service_error_status_code(error), detail=error.detail)


def admin_exercise_text_generation_http_exception(error: AdminExerciseTextGenerationError) -> HTTPException:
    return HTTPException(status_code=admin_exercise_text_generation_error_status_code(error), detail=error.detail)


def admin_exercise_text_tts_http_exception(error: AdminExerciseTextTTSError) -> HTTPException:
    return HTTPException(status_code=admin_exercise_text_tts_error_status_code(error), detail=error.detail)
