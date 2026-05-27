from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.subscriptions.plans import IMPORT_MODE_LOOKUP_ONLY
from app.user_import.services.validation_service import UserImportValidationOutcome


class UserImportManualBindImportModeResolver(Protocol):
    def __call__(self, user_uuid: str, *, current_time: datetime) -> str | None: ...


class UserImportManualBindValidationService:
    def __init__(
        self,
        *,
        validation_service: Any | None,
        import_mode_for_user: UserImportManualBindImportModeResolver,
    ) -> None:
        self._validation_service = validation_service
        self._import_mode_for_user = import_mode_for_user

    def validate_parsed_words(
        self,
        parsed_words: list[Any],
        *,
        user_uuid: str,
        current_time: datetime,
    ) -> UserImportValidationOutcome:
        if self._resolve_import_mode_for_user(user_uuid, current_time=current_time) == IMPORT_MODE_LOOKUP_ONLY:
            return UserImportValidationOutcome(parsed_words, [], None)
        if self._validation_service is None:
            return UserImportValidationOutcome(parsed_words, [], None)
        return self._validation_service.validate_words(parsed_words)

    def record_usage(
        self,
        validation_outcome: UserImportValidationOutcome,
        *,
        task_scope: str,
        actor_user_uuid: str,
        source_type: str,
        source_identifier: str,
        import_job_id: int | None,
        task_log_id: int | None,
        batch_key: str,
        current_time: datetime,
    ) -> None:
        if self._validation_service is None:
            return
        self._validation_service.record_usage(
            validation_outcome.validation_result,
            task_scope=task_scope,
            actor_user_uuid=actor_user_uuid,
            source_type=source_type,
            source_identifier=source_identifier,
            import_job_id=import_job_id,
            task_log_id=task_log_id,
            batch_key=batch_key,
            current_time=current_time,
        )

    def rejected_fragments(self, rejected_items: list[dict[str, str]]) -> list[str]:
        return [
            f"{item.get('lookup_word') or item.get('raw_value')}: {item.get('error_text')}"
            for item in rejected_items
            if item.get("lookup_word") or item.get("raw_value")
        ]

    def _resolve_import_mode_for_user(self, user_uuid: str, *, current_time: datetime) -> str | None:
        if not user_uuid:
            return None
        return self._import_mode_for_user(user_uuid, current_time=current_time)
