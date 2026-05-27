from __future__ import annotations

from datetime import datetime
from typing import Any

from app.helpers.external_error_text import format_external_error, sanitize_external_error_text


def log_user_import_pipeline_error(
    db: Any,
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
) -> None:
    error_logs = getattr(db, "error_logs", None)
    if error_logs is None:
        if not callable(getattr(db, "session", None)):
            return
        try:
            from app.data_access.error_logs import ErrorLogRepository
            error_logs = ErrorLogRepository(db)
        except ImportError:
            return
    safe_error = _safe_error_text(error_text, error)
    context = {
        "domain": "user_import",
        "stage": stage,
        "task_key": task_key,
        "provider_key": provider_key,
        "user_dictionary_entry_id": user_dictionary_entry_id,
        "import_item_id": import_item_id,
        "import_job_id": import_job_id,
        "task_log_id": task_log_id,
        "telegram_user_id": telegram_user_id,
        "lookup_word": lookup_word,
        "attempt_count": attempt_count,
        "error_type": type(error).__name__ if error is not None else None,
        "last_attempted_at": current_time.isoformat() if current_time is not None else None,
        "error_text": safe_error,
        **(context_json or {}),
    }
    context = {key: value for key, value in context.items() if value is not None}
    try:
        error_logs.create(level, _build_error_log_text(context), context_json=context)
    except Exception:
        return


def _safe_error_text(error_text: str | None, error: Exception | None) -> str:
    if error_text:
        return sanitize_external_error_text(error_text)
    if error is not None:
        return format_external_error(error, fallback="User import pipeline failed")
    return sanitize_external_error_text(str(error_text or "")) or "User import pipeline failed"


def _build_error_log_text(context: dict[str, Any]) -> str:
    ordered_keys = (
        "domain",
        "stage",
        "task_key",
        "provider_key",
        "user_dictionary_entry_id",
        "import_item_id",
        "import_job_id",
        "task_log_id",
        "telegram_user_id",
        "source_type",
        "source_identifier",
        "lookup_word",
        "attempt_count",
        "error_type",
    )
    tokens = [f"{key}={context[key]}" for key in ordered_keys if key in context]
    return " ".join([*tokens, f"error={context.get('error_text') or ''}"]).strip()
