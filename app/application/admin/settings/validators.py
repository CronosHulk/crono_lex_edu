from __future__ import annotations

import re
from typing import Any

from app.application.admin.settings.errors import AdminSettingsValidationError
from app.billing.runtime_settings import (
    BillingRuntimeSettingsValidationError,
    normalize_billing_runtime_settings,
)
from app.domain.provider_pricing import list_provider_model_options
from app.domain.provider_settings import get_provider_task, normalize_provider_key
from app.marketing.runtime_settings import (
    AnalyticsSettingsValidationError,
    normalize_analytics_settings,
)
from app.subscriptions.plan_limits import (
    PlanLimitSettingsValidationError,
    normalize_plan_limit_settings,
)
from app.subscriptions.runtime_settings import (
    SubscriptionSettingsValidationError,
    normalize_subscription_runtime_settings,
)
from app.support.runtime_settings import SupportSettingsValidationError, normalize_support_settings
from app.user_import.runtime_settings import (
    UserImportRuntimeSettingsValidationError,
    normalize_user_import_runtime_settings,
)

SUPPORTED_INTERFACE_LOCALES = {"uk", "ru", "pl"}
APP_VERSION_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._+-]{0,31}$")


def normalize_settings_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    if "interface_locale" in payload and payload["interface_locale"] is not None:
        normalized["interface_locale"] = _ensure_allowed_value(
            str(payload["interface_locale"]).strip(),
            SUPPORTED_INTERFACE_LOCALES,
            "interface_locale",
        )
    if "app_version" in payload and payload["app_version"] is not None:
        version = str(payload["app_version"]).strip()
        if not APP_VERSION_RE.fullmatch(version):
            raise AdminSettingsValidationError(
                "app_version must be 1-32 chars and use only letters, digits, dot, underscore, plus or hyphen"
            )
        normalized["app_version"] = version
    if "billing_settings" in payload and payload["billing_settings"] is not None:
        if (
            isinstance(payload["billing_settings"], dict)
            and (
                "billing_provider" in payload["billing_settings"]
                or "monobank_mode" in payload["billing_settings"]
            )
        ):
            raise AdminSettingsValidationError(
                "Use OTP-protected billing provider settings endpoint"
            )
        try:
            normalized["billing_settings"] = normalize_billing_runtime_settings(
                payload["billing_settings"],
                partial=True,
            )
        except BillingRuntimeSettingsValidationError as error:
            raise AdminSettingsValidationError(str(error)) from error
    if "import_settings" in payload and payload["import_settings"] is not None:
        try:
            normalized["import_settings"] = normalize_user_import_runtime_settings(
                payload["import_settings"],
                partial=True,
            )
        except UserImportRuntimeSettingsValidationError as error:
            raise AdminSettingsValidationError(str(error)) from error
    if "subscription_settings" in payload and payload["subscription_settings"] is not None:
        try:
            normalized["subscription_settings"] = normalize_subscription_runtime_settings(
                payload["subscription_settings"],
                partial=True,
            )
        except SubscriptionSettingsValidationError as error:
            raise AdminSettingsValidationError(str(error)) from error
    if "plan_limits" in payload and payload["plan_limits"] is not None:
        try:
            normalized["plan_limits"] = normalize_plan_limit_settings(
                payload["plan_limits"],
                partial=True,
            )
        except PlanLimitSettingsValidationError as error:
            raise AdminSettingsValidationError(str(error)) from error
    if "support_settings" in payload and payload["support_settings"] is not None:
        try:
            normalized["support_settings"] = normalize_support_settings(
                payload["support_settings"],
                partial=True,
                base={},
            )
        except SupportSettingsValidationError as error:
            raise AdminSettingsValidationError(str(error)) from error
    if "analytics_settings" in payload and payload["analytics_settings"] is not None:
        try:
            normalized["analytics_settings"] = normalize_analytics_settings(
                payload["analytics_settings"],
                partial=True,
            )
        except AnalyticsSettingsValidationError as error:
            raise AdminSettingsValidationError(str(error)) from error
    return normalized


PROVIDER_CONFIG_FIELDS_BY_PROVIDER = {
    "openai": {"model", "api_url"},
    "google_tts": {"language_code", "voice_name"},
    "local_sentence_transformers": {"model", "device"},
    "disabled": set(),
}
PROVIDER_CONFIG_VALUE_MAX_LENGTH = 512


def normalize_provider_settings_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise AdminSettingsValidationError("tasks must be a non-empty list")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_item in raw_tasks:
        if not isinstance(raw_item, dict):
            raise AdminSettingsValidationError("tasks items must be objects")
        task_key = str(raw_item.get("task_key") or "").strip()
        if task_key in seen:
            raise AdminSettingsValidationError(f"Duplicate provider task: {task_key}")
        seen.add(task_key)
        try:
            task = get_provider_task(task_key)
        except ValueError as error:
            raise AdminSettingsValidationError(str(error)) from error
        provider_key = _ensure_allowed_value(
            normalize_provider_key(raw_item.get("provider_key")),
            set(task.allowed_provider_keys),
            "provider_key",
        )
        config = _normalize_provider_config(provider_key, raw_item.get("config") or {})
        normalized.append(
            {
                "task_key": task_key,
                "provider_key": provider_key,
                "is_enabled": bool(raw_item.get("is_enabled", True)) and provider_key != "disabled",
                "config_json": config,
            }
        )
    return normalized


def _normalize_provider_config(provider_key: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AdminSettingsValidationError("config must be an object")
    allowed_fields = PROVIDER_CONFIG_FIELDS_BY_PROVIDER.get(provider_key)
    if allowed_fields is None:
        raise AdminSettingsValidationError(f"Unsupported provider_key: {provider_key}")
    unknown_fields = set(value) - allowed_fields
    if unknown_fields:
        unknown_list = ", ".join(sorted(unknown_fields))
        raise AdminSettingsValidationError(f"Unsupported config fields for {provider_key}: {unknown_list}")
    normalized: dict[str, Any] = {}
    for key, raw in value.items():
        if raw is None:
            continue
        if isinstance(raw, bool):
            normalized[key] = raw
            continue
        candidate = str(raw).strip()
        if len(candidate) > PROVIDER_CONFIG_VALUE_MAX_LENGTH:
            raise AdminSettingsValidationError(f"{key} must be at most 512 chars")
        if key == "api_url" and candidate and not candidate.startswith("https://"):
            raise AdminSettingsValidationError("api_url must use https://")
        if provider_key == "openai" and key == "model":
            candidate = _ensure_allowed_value(candidate, set(list_provider_model_options("openai")), "model")
        normalized[key] = candidate
    return normalized


def _ensure_allowed_value(value: Any, allowed_values: set[str], field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise AdminSettingsValidationError(f"{field_name} is required")
    if len(text) > 100:
        raise AdminSettingsValidationError(f"{field_name} must be at most 100 characters")
    allowed = {str(item) for item in allowed_values}
    if text not in allowed:
        expected = ", ".join(sorted(allowed))
        raise AdminSettingsValidationError(f"{field_name} must be one of: {expected}")
    return text
