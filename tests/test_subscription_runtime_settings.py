from __future__ import annotations

import pytest

from app.subscriptions.runtime_settings import (
    SubscriptionSettingsValidationError,
    normalize_subscription_runtime_settings,
)


def test_subscription_runtime_settings_accept_defaults() -> None:
    assert normalize_subscription_runtime_settings({}, partial=True) == {
        "trial_duration_days": 7,
    }


def test_subscription_runtime_settings_reject_invalid_trial_duration() -> None:
    with pytest.raises(SubscriptionSettingsValidationError):
        normalize_subscription_runtime_settings({"trial_duration_days": 99}, partial=True)


def test_subscription_runtime_settings_reject_non_object_payload() -> None:
    with pytest.raises(SubscriptionSettingsValidationError):
        normalize_subscription_runtime_settings("trial_duration_days")
