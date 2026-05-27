from __future__ import annotations

from typing import Any


def build_user_import_task_error_context(
    *,
    task_log_id: int,
    telegram_user_id: int | None,
    source_type: str | None,
    source_identifier: str | None,
    import_job_id: int | None = None,
    import_item_id: int | None = None,
    lookup_word: str | None = None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "task_log_id": task_log_id,
        "telegram_user_id": telegram_user_id,
        "source_type": source_type,
        "source_identifier": source_identifier,
    }
    if import_job_id is not None:
        context["import_job_id"] = import_job_id
    if import_item_id is not None:
        context["import_item_id"] = import_item_id
    if lookup_word is not None:
        context["lookup_word"] = lookup_word
    return context
