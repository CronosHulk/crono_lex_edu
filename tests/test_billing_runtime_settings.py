from __future__ import annotations

import pytest

from app.billing.runtime_settings import (
    BILLING_MONOBANK_MODE_SETTINGS_KEY,
    BILLING_RUNTIME_SETTINGS_KEY,
    MONOBANK_MODE_DISABLED,
    MONOBANK_MODE_PRODUCTION,
    MONOBANK_MODE_TEST,
    BillingRuntimeSettingsValidationError,
    normalize_billing_runtime_settings,
    read_billing_runtime_settings,
    validate_monobank_mode_token,
)
from app.domain.billing.constants import BILLING_PROVIDER_INSTANT, BILLING_PROVIDER_MONOBANK


class FakeAppSettings:
    def __init__(self, value=None, mode_value=None) -> None:
        self.value = value
        self.mode_value = mode_value

    def get_value(self, key: str):
        if key == BILLING_RUNTIME_SETTINGS_KEY:
            return self.value
        if key == BILLING_MONOBANK_MODE_SETTINGS_KEY:
            return self.mode_value
        raise AssertionError(f"Unexpected settings key: {key}")


class FakeDb:
    def __init__(self, value=None, mode_value=None) -> None:
        self.app_settings = FakeAppSettings(value, mode_value)


class FakeProviderSettings:
    monobank_token = ""
    monobank_token_test = ""


def test_billing_runtime_settings_defaults_are_safe() -> None:
    settings = read_billing_runtime_settings(FakeDb())

    assert settings["billing_provider"] == BILLING_PROVIDER_INSTANT
    assert settings["monobank_mode"] == MONOBANK_MODE_DISABLED
    assert settings["double_time_for_project_support_enabled"] is False
    assert settings["premium_plus_checkout_enabled"] is True
    assert settings["enabled_period_months"] == [1, 3, 6, 12]
    assert settings["plan_prices_uah"]["premium"]["1"] == 10
    assert settings["plan_prices_uah"]["premium_plus"]["1"] == 20
    assert settings["webhook_wait_seconds"] == 20
    assert settings["frontend_poll_interval_seconds"] == 10
    assert settings["reconciliation_interval_seconds"] == 3600
    assert settings["receipt_retry_interval_seconds"] == 2
    assert settings["receipt_retry_delay_seconds"] == 2
    assert settings["receipt_retry_max_attempts"] == 3
    assert settings["success_recheck_interval_days"] == 7
    assert settings["success_recheck_window_days"] == 7
    assert settings["subscription_expiration_hour"] == 0
    assert len(settings["offer_text"]) >= 20


def test_billing_runtime_settings_default_offer_text_is_provider_neutral() -> None:
    settings = read_billing_runtime_settings(FakeDb())
    offer_text = settings["offer_text"]

    assert "Monobank payment page" not in offer_text
    assert "Monobank" not in offer_text
    assert "payment provider checkout page" in offer_text
    assert "payment provider confirms successful payment" in offer_text


def test_billing_runtime_settings_reads_monobank_mode_from_separate_setting() -> None:
    settings = read_billing_runtime_settings(
        FakeDb(
            value={"monobank_mode": MONOBANK_MODE_DISABLED, "webhook_wait_seconds": 45},
            mode_value={"monobank_mode": MONOBANK_MODE_TEST},
        )
    )

    assert settings["monobank_mode"] == MONOBANK_MODE_TEST
    assert settings["webhook_wait_seconds"] == 45


def test_billing_runtime_settings_rejects_empty_separate_monobank_mode() -> None:
    with pytest.raises(BillingRuntimeSettingsValidationError) as error:
        read_billing_runtime_settings(FakeDb(mode_value={"monobank_mode": ""}))

    assert "monobank_mode" in str(error.value)


def test_billing_runtime_settings_merges_partial_values() -> None:
    settings = normalize_billing_runtime_settings(
        {
            "billing_provider": " monobank ",
            "monobank_mode": MONOBANK_MODE_TEST,
            "double_time_for_project_support_enabled": True,
            "premium_plus_checkout_enabled": False,
            "enabled_period_months": [12, 1, 1],
            "plan_prices_uah": {"premium": {"1": 11}},
            "frontend_poll_interval_seconds": 5,
        },
        partial=True,
    )

    assert settings["billing_provider"] == BILLING_PROVIDER_MONOBANK
    assert settings["monobank_mode"] == MONOBANK_MODE_TEST
    assert settings["double_time_for_project_support_enabled"] is True
    assert settings["premium_plus_checkout_enabled"] is False
    assert settings["enabled_period_months"] == [12, 1]
    assert settings["plan_prices_uah"]["premium"]["1"] == 11
    assert settings["plan_prices_uah"]["premium"]["3"] == 30
    assert settings["plan_prices_uah"]["premium_plus"]["1"] == 20
    assert settings["frontend_poll_interval_seconds"] == 5


def test_billing_runtime_settings_accepts_explicit_monobank_provider() -> None:
    settings = normalize_billing_runtime_settings(
        {
            "billing_provider": " monobank ",
            "monobank_mode": MONOBANK_MODE_TEST,
        },
        partial=True,
    )

    assert settings["billing_provider"] == BILLING_PROVIDER_MONOBANK
    assert settings["monobank_mode"] == MONOBANK_MODE_TEST


def test_billing_runtime_settings_accepts_production_mode_without_token_check_here() -> None:
    settings = normalize_billing_runtime_settings({"monobank_mode": MONOBANK_MODE_PRODUCTION}, partial=True)

    assert settings["monobank_mode"] == MONOBANK_MODE_PRODUCTION


@pytest.mark.parametrize("billing_provider", ["other", "tribute"])
def test_billing_runtime_settings_rejects_unknown_billing_provider(billing_provider: str) -> None:
    with pytest.raises(BillingRuntimeSettingsValidationError) as error:
        normalize_billing_runtime_settings({"billing_provider": billing_provider}, partial=True)

    assert "billing_provider" in str(error.value)


def test_billing_runtime_settings_rejects_unknown_mode() -> None:
    try:
        normalize_billing_runtime_settings({"monobank_mode": "live"}, partial=True)
    except BillingRuntimeSettingsValidationError as error:
        assert "monobank_mode" in str(error)
    else:  # pragma: no cover
        raise AssertionError("BillingRuntimeSettingsValidationError was expected")


def test_billing_runtime_settings_rejects_unknown_period() -> None:
    try:
        normalize_billing_runtime_settings({"enabled_period_months": [1, 2]}, partial=True)
    except BillingRuntimeSettingsValidationError as error:
        assert "enabled_period_months" in str(error)
    else:  # pragma: no cover
        raise AssertionError("BillingRuntimeSettingsValidationError was expected")


def test_billing_runtime_settings_rejects_unknown_price_plan() -> None:
    try:
        normalize_billing_runtime_settings({"plan_prices_uah": {"free": {"1": 1}}}, partial=True)
    except BillingRuntimeSettingsValidationError as error:
        assert "plan_prices_uah" in str(error)
    else:  # pragma: no cover
        raise AssertionError("BillingRuntimeSettingsValidationError was expected")


def test_billing_runtime_settings_rejects_short_offer_text() -> None:
    try:
        normalize_billing_runtime_settings({"offer_text": "too short"}, partial=True)
    except BillingRuntimeSettingsValidationError as error:
        assert "offer_text" in str(error)
    else:  # pragma: no cover
        raise AssertionError("BillingRuntimeSettingsValidationError was expected")


def test_billing_runtime_settings_rejects_fractional_integers() -> None:
    for payload, field_name in [
        ({"enabled_period_months": [1.5]}, "enabled_period_months"),
        ({"plan_prices_uah": {"premium": {"1": 10.9}}}, "plan_prices_uah.premium.1"),
        ({"webhook_wait_seconds": 20.7}, "webhook_wait_seconds"),
    ]:
        try:
            normalize_billing_runtime_settings(payload, partial=True)
        except BillingRuntimeSettingsValidationError as error:
            assert field_name in str(error)
        else:  # pragma: no cover
            raise AssertionError("BillingRuntimeSettingsValidationError was expected")


def test_billing_runtime_settings_rejects_non_boolean_double_time_flag() -> None:
    with pytest.raises(BillingRuntimeSettingsValidationError) as error:
        normalize_billing_runtime_settings(
            {"double_time_for_project_support_enabled": "true"},
            partial=True,
        )

    assert "double_time_for_project_support_enabled" in str(error.value)


def test_billing_runtime_settings_rejects_missing_monobank_token_without_http_error() -> None:
    with pytest.raises(BillingRuntimeSettingsValidationError) as error:
        validate_monobank_mode_token(FakeProviderSettings(), MONOBANK_MODE_PRODUCTION)

    assert str(error.value) == "MONOBANK_TOKEN is not configured"
