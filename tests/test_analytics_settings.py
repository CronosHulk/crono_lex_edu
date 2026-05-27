from __future__ import annotations

import pytest

from app.marketing.runtime_settings import (
    AnalyticsSettingsValidationError,
    normalize_analytics_settings,
)


def test_analytics_settings_accept_empty_defaults() -> None:
    assert normalize_analytics_settings({}, partial=True) == {
        "google_analytics_id": "",
        "google_ads_id": "",
    }


def test_analytics_settings_normalize_google_ids() -> None:
    assert normalize_analytics_settings(
        {
            "google_analytics_id": " g-abcdef12 ",
            "google_ads_id": " aw-123456789 ",
        },
        partial=True,
    ) == {
        "google_analytics_id": "G-ABCDEF12",
        "google_ads_id": "AW-123456789",
    }


def test_analytics_settings_reject_invalid_ids() -> None:
    with pytest.raises(AnalyticsSettingsValidationError):
        normalize_analytics_settings({"google_analytics_id": "UA-123"})
    with pytest.raises(AnalyticsSettingsValidationError):
        normalize_analytics_settings({"google_ads_id": "G-ABCDEF12"})
