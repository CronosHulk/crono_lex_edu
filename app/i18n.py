from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_LOCALE = "uk"
PROJECT_MESSAGES_PATH = Path(__file__).resolve().parents[1] / "frontend_shared" / "src" / "i18n" / "messages.json"


def _load_backend_messages() -> dict[str, dict[str, str]]:
    with PROJECT_MESSAGES_PATH.open(encoding="utf-8") as file:
        messages = json.load(file)
    backend_messages = messages.get("backend", {})
    if not isinstance(backend_messages, dict):
        raise RuntimeError("Project i18n source must contain a backend message scope.")
    return backend_messages


MESSAGES: dict[str, dict[str, str]] = _load_backend_messages()
SUPPORTED_LOCALES = set(MESSAGES)


def detect_locale(language_code: str | None) -> str:
    if not language_code:
        return DEFAULT_LOCALE

    candidate = language_code.lower().split("-", 1)[0]
    if candidate in SUPPORTED_LOCALES:
        return candidate
    return DEFAULT_LOCALE


def translate(locale: str, key: str, **kwargs: Any) -> str:
    message_locale = locale if locale in MESSAGES else DEFAULT_LOCALE
    template = MESSAGES[message_locale].get(key, MESSAGES[DEFAULT_LOCALE][key])
    return template.format(**kwargs)
