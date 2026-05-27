from __future__ import annotations

from typing import Literal

from app.domain.provider_settings import EXERCISE_TEXT_GENERATION_TASK_KEY

TaskLogScope = Literal["all", "billing", "operations"]

TASK_LOG_STATUS_OPTIONS: tuple[str, ...] = ("queued", "processing", "success", "error", "fatal")
TASK_LOG_STATUSES = set(TASK_LOG_STATUS_OPTIONS)

TASK_LOG_SCOPE_OPTIONS: tuple[TaskLogScope, ...] = ("all", "billing", "operations")
TASK_LOG_SCOPES = set(TASK_LOG_SCOPE_OPTIONS)

BILLING_TASK_LOG_PREFIXES: tuple[str, ...] = ("billing_", "subscription_")

TASK_LOG_TYPE_OPTIONS: tuple[str, ...] = (
    "billing_payment_reconciliation",
    "billing_payment_success_recheck",
    "billing_receipt_retry",
    "billing_subscription_purchase_recovery",
    "bound_google_doc_sync",
    EXERCISE_TEXT_GENERATION_TASK_KEY,
    "exercise_texts.quiz_generation",
    "exercise_texts.tts_generation",
    "exercise_texts.translations_generation",
    "post_upgrade_google_doc_rescan",
    "subscription_daily_maintenance",
    "subscription_trial_expiration",
    "user_import_audio_build",
    "user_import_embedding_build",
    "user_vocabulary_import_job_process",
)

LEGACY_TASK_LOG_TYPE_OPTIONS: tuple[str, ...] = (
    "billing_monobank_receipt_retry",
    "billing_monobank_reconciliation",
    "billing_monobank_success_recheck",
)
TASK_LOG_TYPES = set((*TASK_LOG_TYPE_OPTIONS, *LEGACY_TASK_LOG_TYPE_OPTIONS))


def is_billing_task_type(task_type: str) -> bool:
    return str(task_type).startswith(BILLING_TASK_LOG_PREFIXES)


def task_log_type_options_for_scope(scope: str) -> tuple[str, ...]:
    validate_task_log_scope(scope)
    if scope == "all":
        return TASK_LOG_TYPE_OPTIONS
    if scope == "billing":
        return tuple(value for value in TASK_LOG_TYPE_OPTIONS if is_billing_task_type(value))
    return tuple(value for value in TASK_LOG_TYPE_OPTIONS if not is_billing_task_type(value))


def task_log_filter_values_for_scope(scope: str) -> tuple[str, ...]:
    validate_task_log_scope(scope)
    values = (*TASK_LOG_TYPE_OPTIONS, *LEGACY_TASK_LOG_TYPE_OPTIONS)
    if scope == "all":
        return values
    if scope == "billing":
        return tuple(value for value in values if is_billing_task_type(value))
    return tuple(value for value in values if not is_billing_task_type(value))


def validate_task_status(status: str) -> None:
    if status not in TASK_LOG_STATUSES:
        raise ValueError(f"Unsupported task status: {status}")


def validate_task_log_scope(scope: str) -> None:
    if scope not in TASK_LOG_SCOPES:
        raise ValueError(f"Unsupported task log scope: {scope}")
