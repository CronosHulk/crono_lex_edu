from __future__ import annotations

import re
from typing import Any

ANALYTICS_SETTINGS_KEY = "marketing.analytics_settings"

DEFAULT_ANALYTICS_SETTINGS = {
    "google_analytics_id": "",
    "google_ads_id": "",
}

GOOGLE_ANALYTICS_ID_RE = re.compile(r"^G-[A-Z0-9]{4,32}$")
GOOGLE_ADS_ID_RE = re.compile(r"^AW-[0-9]{4,32}$")


class AnalyticsSettingsValidationError(ValueError):
    pass


def read_analytics_settings(db: Any) -> dict[str, str]:
    repository = getattr(db, "app_settings", None)
    stored = repository.get_value(ANALYTICS_SETTINGS_KEY) if repository is not None else None
    return normalize_analytics_settings(stored or {}, partial=True)


def normalize_analytics_settings(value: Any, *, partial: bool = False) -> dict[str, str]:
    if not isinstance(value, dict):
        raise AnalyticsSettingsValidationError("analytics_settings must be an object")
    allowed_fields = set(DEFAULT_ANALYTICS_SETTINGS)
    unknown_fields = set(value) - allowed_fields
    if unknown_fields:
        unknown_list = ", ".join(sorted(unknown_fields))
        raise AnalyticsSettingsValidationError(f"Unsupported analytics_settings fields: {unknown_list}")

    normalized = dict(DEFAULT_ANALYTICS_SETTINGS) if partial else {}
    if "google_analytics_id" in value:
        normalized["google_analytics_id"] = _normalize_optional_tracking_id(
            value["google_analytics_id"],
            field_name="google_analytics_id",
            pattern=GOOGLE_ANALYTICS_ID_RE,
            expected_format="G-XXXXXXXX",
        )
    if "google_ads_id" in value:
        normalized["google_ads_id"] = _normalize_optional_tracking_id(
            value["google_ads_id"],
            field_name="google_ads_id",
            pattern=GOOGLE_ADS_ID_RE,
            expected_format="AW-123456789",
        )
    return normalized


def _normalize_optional_tracking_id(value: Any, *, field_name: str, pattern: re.Pattern[str], expected_format: str) -> str:
    if value is None:
        return ""
    candidate = str(value).strip().upper()
    if not candidate:
        return ""
    if not pattern.fullmatch(candidate):
        raise AnalyticsSettingsValidationError(f"{field_name} must be empty or use format {expected_format}")
    return candidate
