from __future__ import annotations

from typing import Any

SUPPORT_SETTINGS_KEY = "project.support_settings"
DEFAULT_SUPPORT_URL = "https://send.monobank.ua/jar/7E7wGkzHJr"
DEFAULT_SUPPORT_SETTINGS = {
    "is_enabled": True,
    "support_url": DEFAULT_SUPPORT_URL,
}
SUPPORT_SETTINGS_FIELDS = set(DEFAULT_SUPPORT_SETTINGS)
SUPPORT_URL_MAX_LENGTH = 2048


class SupportSettingsValidationError(ValueError):
    pass


def read_support_settings(db: Any) -> dict[str, Any]:
    repository = getattr(db, "app_settings", None)
    stored = repository.get_value(SUPPORT_SETTINGS_KEY) if repository is not None else None
    if stored is None:
        return dict(DEFAULT_SUPPORT_SETTINGS)
    return normalize_support_settings(stored, partial=True, base=DEFAULT_SUPPORT_SETTINGS)


def normalize_support_settings(
    value: Any,
    *,
    partial: bool = False,
    base: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SupportSettingsValidationError("support_settings must be an object")
    unknown_fields = set(value) - SUPPORT_SETTINGS_FIELDS
    if unknown_fields:
        unknown = ", ".join(sorted(unknown_fields))
        raise SupportSettingsValidationError(f"Unsupported support_settings fields: {unknown}")

    normalized = dict(DEFAULT_SUPPORT_SETTINGS if base is None else base) if partial else {}
    if "is_enabled" in value:
        normalized["is_enabled"] = bool(value["is_enabled"])
    elif not partial:
        normalized["is_enabled"] = DEFAULT_SUPPORT_SETTINGS["is_enabled"]

    if "support_url" in value:
        normalized["support_url"] = _normalize_support_url(value["support_url"])
    elif not partial:
        normalized["support_url"] = DEFAULT_SUPPORT_SETTINGS["support_url"]

    if normalized.get("is_enabled") and not normalized.get("support_url"):
        raise SupportSettingsValidationError("support_url is required when support link is enabled")
    return normalized


def _normalize_support_url(value: Any) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return ""
    if len(candidate) > SUPPORT_URL_MAX_LENGTH:
        raise SupportSettingsValidationError("support_url must be at most 2048 chars")
    if not candidate.startswith("https://"):
        raise SupportSettingsValidationError("support_url must use https://")
    return candidate
