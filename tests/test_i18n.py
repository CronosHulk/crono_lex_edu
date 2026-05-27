from __future__ import annotations

import json
from pathlib import Path

from app.i18n import PROJECT_MESSAGES_PATH, detect_locale, translate


def test_detect_locale_returns_uk_for_supported_language() -> None:
    assert detect_locale("uk-UA") == "uk"


def test_detect_locale_falls_back_to_uk() -> None:
    assert detect_locale("en-US") == "uk"


def test_translate_formats_template() -> None:
    assert "Марко" in translate("uk", "start_title", mention="Марко")


def test_project_i18n_source_contains_backend_and_frontend_scopes() -> None:
    messages = json.loads(Path(PROJECT_MESSAGES_PATH).read_text(encoding="utf-8"))

    assert sorted(messages) == ["admin", "backend", "client"]
    assert "settingsTitle" in messages["client"]["uk"]
    assert "settings_title" in messages["backend"]["uk"]
    assert "settings" in messages["admin"]["uk"]


def test_backend_docker_image_includes_project_i18n_source() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "frontend_shared/src/i18n/messages.json" in dockerfile
