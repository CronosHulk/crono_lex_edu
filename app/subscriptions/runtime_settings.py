from __future__ import annotations

from typing import Any

SUBSCRIPTION_RUNTIME_SETTINGS_KEY = "subscriptions.runtime_settings"
DEFAULT_SUBSCRIPTION_RUNTIME_SETTINGS = {
    "trial_duration_days": 7,
}
TRIAL_DURATION_DAY_OPTIONS = {0, 1, 3, 7, 14, 30}


class SubscriptionSettingsValidationError(ValueError):
    pass


def read_subscription_runtime_settings(db: Any) -> dict[str, Any]:
    repository = getattr(db, "app_settings", None)
    stored = repository.get_value(SUBSCRIPTION_RUNTIME_SETTINGS_KEY) if repository is not None else None
    return normalize_subscription_runtime_settings(stored or {}, partial=True)


def normalize_subscription_runtime_settings(value: Any, *, partial: bool = False) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SubscriptionSettingsValidationError("subscription_settings must be an object")
    allowed_fields = set(DEFAULT_SUBSCRIPTION_RUNTIME_SETTINGS)
    unknown_fields = set(value) - allowed_fields
    if unknown_fields:
        unknown_list = ", ".join(sorted(unknown_fields))
        raise SubscriptionSettingsValidationError(f"Unsupported subscription_settings fields: {unknown_list}")
    base = dict(DEFAULT_SUBSCRIPTION_RUNTIME_SETTINGS) if partial else {}
    for key, raw in value.items():
        if key == "trial_duration_days":
            base[key] = _normalize_trial_duration_days(raw)
    return base


def _normalize_trial_duration_days(raw: Any) -> int:
    value = _normalize_non_negative_int(raw, "trial_duration_days")
    if value not in TRIAL_DURATION_DAY_OPTIONS:
        expected = ", ".join(sorted(str(option) for option in TRIAL_DURATION_DAY_OPTIONS))
        raise SubscriptionSettingsValidationError(f"trial_duration_days must be one of: {expected}")
    return value


def _normalize_non_negative_int(raw: Any, field_name: str) -> int:
    if isinstance(raw, bool):
        raise SubscriptionSettingsValidationError(f"{field_name} must be an integer")
    try:
        value = int(raw)
    except (TypeError, ValueError) as error:
        raise SubscriptionSettingsValidationError(f"{field_name} must be an integer") from error
    if value < 0:
        raise SubscriptionSettingsValidationError(f"{field_name} must be at least 0")
    return value
