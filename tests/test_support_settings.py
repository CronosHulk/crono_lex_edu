from __future__ import annotations

import pytest

from app.support.runtime_settings import (
    SupportSettingsValidationError,
    normalize_support_settings,
)


def test_support_settings_accept_defaults() -> None:
    assert normalize_support_settings({}, partial=True) == {
        "is_enabled": True,
        "support_url": "https://send.monobank.ua/jar/7E7wGkzHJr",
    }


def test_support_settings_reject_invalid_url() -> None:
    with pytest.raises(SupportSettingsValidationError):
        normalize_support_settings({"support_url": "http://example.test/jar"}, partial=True)


def test_support_settings_requires_url_when_enabled() -> None:
    with pytest.raises(SupportSettingsValidationError):
        normalize_support_settings({"is_enabled": True, "support_url": ""})
