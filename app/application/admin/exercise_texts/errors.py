from __future__ import annotations

from typing import Any


class AdminExerciseTextServiceError(Exception):
    def __init__(self, detail: Any) -> None:
        self.detail = detail
        super().__init__(str(detail))


class AdminExerciseTextServiceValidationError(AdminExerciseTextServiceError):
    pass


class AdminExerciseTextServiceAccessDeniedError(AdminExerciseTextServiceError):
    pass


class AdminExerciseTextServiceNotFoundError(AdminExerciseTextServiceError):
    pass


class AdminExerciseTextServiceConflictError(AdminExerciseTextServiceError):
    pass


def admin_exercise_text_service_error_status_code(error: AdminExerciseTextServiceError) -> int:
    if isinstance(error, AdminExerciseTextServiceAccessDeniedError):
        return 403
    if isinstance(error, AdminExerciseTextServiceConflictError):
        return 409
    if isinstance(error, AdminExerciseTextServiceNotFoundError):
        return 404
    return 400


class AdminExerciseTextGenerationError(Exception):
    def __init__(self, detail: Any) -> None:
        self.detail = detail
        super().__init__(str(detail))


class AdminExerciseTextGenerationValidationError(AdminExerciseTextGenerationError):
    pass


class AdminExerciseTextGenerationAccessDeniedError(AdminExerciseTextGenerationError):
    pass


class AdminExerciseTextGenerationNotFoundError(AdminExerciseTextGenerationError):
    pass


class AdminExerciseTextGenerationConflictError(AdminExerciseTextGenerationError):
    pass


def admin_exercise_text_generation_error_status_code(error: AdminExerciseTextGenerationError) -> int:
    if isinstance(error, AdminExerciseTextGenerationAccessDeniedError):
        return 403
    if isinstance(error, AdminExerciseTextGenerationConflictError):
        return 409
    if isinstance(error, AdminExerciseTextGenerationNotFoundError):
        return 404
    return 400


class AdminExerciseTextTTSError(Exception):
    def __init__(self, detail: Any) -> None:
        self.detail = detail
        super().__init__(str(detail))


class AdminExerciseTextTTSValidationError(AdminExerciseTextTTSError):
    pass


class AdminExerciseTextTTSAccessDeniedError(AdminExerciseTextTTSError):
    pass


class AdminExerciseTextTTSNotFoundError(AdminExerciseTextTTSError):
    pass


class AdminExerciseTextTTSConflictError(AdminExerciseTextTTSError):
    pass


def admin_exercise_text_tts_error_status_code(error: AdminExerciseTextTTSError) -> int:
    if isinstance(error, AdminExerciseTextTTSAccessDeniedError):
        return 403
    if isinstance(error, AdminExerciseTextTTSConflictError):
        return 409
    if isinstance(error, AdminExerciseTextTTSNotFoundError):
        return 404
    return 400
