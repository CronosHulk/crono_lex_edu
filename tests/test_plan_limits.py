from __future__ import annotations

import pytest

from app.subscriptions.plan_limits import (
    DEFAULT_PLAN_LIMITS,
    PLAN_PREMIUM,
    PlanLimitSettingsValidationError,
    normalize_plan_limit_settings,
)


def test_plan_limits_accept_defaults() -> None:
    assert normalize_plan_limit_settings({}, partial=True) == DEFAULT_PLAN_LIMITS


def test_plan_limits_reject_unknown_plan() -> None:
    with pytest.raises(PlanLimitSettingsValidationError):
        normalize_plan_limit_settings({"unknown": {}}, partial=True)


def test_plan_limits_reject_unknown_level() -> None:
    with pytest.raises(PlanLimitSettingsValidationError):
        normalize_plan_limit_settings({PLAN_PREMIUM: {"level_titles": ["A1", "Z9"]}}, partial=True)


def test_plan_limits_reject_string_boolean() -> None:
    with pytest.raises(PlanLimitSettingsValidationError):
        normalize_plan_limit_settings({PLAN_PREMIUM: {"listening_training": "true"}}, partial=True)
