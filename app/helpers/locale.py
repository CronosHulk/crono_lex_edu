from __future__ import annotations

from typing import Any

SUPPORTED_INTERFACE_LOCALES = {"uk", "ru", "pl"}
DEFAULT_INTERFACE_LOCALE = "uk"


def normalize_interface_locale(language_code: str | None) -> str:
    if not language_code:
        return DEFAULT_INTERFACE_LOCALE
    candidate = str(language_code).strip().lower().split("-", 1)[0]
    if candidate in SUPPORTED_INTERFACE_LOCALES:
        return candidate
    return DEFAULT_INTERFACE_LOCALE


def resolve_user_locale(user: Any) -> str:
    interface_locale = _read_value(user, "interface_locale")
    if interface_locale:
        normalized = str(interface_locale).strip().lower()
        if normalized in SUPPORTED_INTERFACE_LOCALES:
            return normalized
    return normalize_interface_locale(_read_value(user, "language_code"))


def _read_value(source: Any, key: str) -> str | None:
    if source is None:
        return None
    if isinstance(source, dict):
        value = source.get(key)
    else:
        value = getattr(source, key, None)
    return str(value) if value is not None else None
