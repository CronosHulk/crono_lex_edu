from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol


class _UserImportItemsEntryContextPort(Protocol):
    def list_by_user_dictionary_entry(self, entry_id: int) -> list[dict[str, Any]]: ...


class _LogPipelineErrorPort(Protocol):
    def __call__(
        self,
        *,
        stage: str,
        error_text: str | None = None,
        error: Exception | None = None,
        level: str = "warn",
        task_key: str | None = None,
        provider_key: str | None = None,
        user_dictionary_entry_id: int | None = None,
        import_item_id: int | None = None,
        import_job_id: int | None = None,
        task_log_id: int | None = None,
        telegram_user_id: int | None = None,
        lookup_word: str | None = None,
        attempt_count: int | None = None,
        current_time: datetime | None = None,
        context_json: dict[str, Any] | None = None,
    ) -> None: ...


class UserDictionaryBuildLogger:
    def __init__(
        self,
        *,
        user_import_items: _UserImportItemsEntryContextPort,
        log_pipeline_error: _LogPipelineErrorPort,
    ) -> None:
        self.user_import_items = user_import_items
        self._log_pipeline_error = log_pipeline_error

    def entry_import_context(self, entry_id: int) -> dict[str, Any]:
        items = self.user_import_items.list_by_user_dictionary_entry(entry_id)
        if not items:
            return {}
        return items[0]

    def log_pipeline_error(
        self,
        entry: dict[str, Any],
        *,
        stage: str,
        error_text: str | None = None,
        error: Exception | None = None,
        attempt_count: int | None = None,
        current_time: datetime,
        task_key: str | None = None,
        provider_key: str | None = None,
        import_context: dict[str, Any] | None = None,
        context_json: dict[str, Any] | None = None,
    ) -> None:
        context = (
            import_context
            if import_context is not None
            else self.entry_import_context(int(entry["id"]))
        )
        self._log_pipeline_error(
            stage=stage,
            error_text=error_text,
            error=error,
            task_key=task_key,
            provider_key=provider_key,
            user_dictionary_entry_id=int(entry["id"]),
            import_item_id=_optional_int(context.get("id")),
            import_job_id=_optional_int(context.get("import_job_id")),
            task_log_id=_optional_int(context.get("task_log_id")),
            telegram_user_id=_optional_int(context.get("telegram_user_id")),
            lookup_word=str(entry.get("word") or ""),
            attempt_count=attempt_count,
            current_time=current_time,
            context_json=context_json,
        )

    def log_logging_failure(
        self,
        entry: dict[str, Any],
        *,
        stage: str,
        error: Exception,
        current_time: datetime,
    ) -> None:
        try:
            self._log_pipeline_error(
                stage=stage,
                error_text=f"user import {stage} error logging failed: {error}",
                error=error,
                user_dictionary_entry_id=int(entry["id"]),
                lookup_word=str(entry.get("word") or ""),
                current_time=current_time,
                context_json={
                    "logging_failure": True,
                    "user_dictionary_entry_id": int(entry["id"]),
                },
            )
        except Exception:
            return

    @staticmethod
    def provider_key_from_status(provider_status: dict[str, Any], fallback: str) -> str:
        for key, value in provider_status.items():
            if isinstance(value, dict) and value.get("status") == "error":
                return str(key)
        return fallback


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
