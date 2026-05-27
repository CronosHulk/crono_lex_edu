from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.billing.services.checkout_provider_config as provider_config_module
from app.billing.runtime_settings import BillingRuntimeSettingsValidationError
from app.billing.services.checkout_provider_config import (
    MONOBANK_SUPPORTED_PERIOD_MONTHS,
    BillingCheckoutProviderConfig,
    build_checkout_plan_icon_url,
    build_checkout_subscription_description,
    build_checkout_webhook_url,
    resolve_checkout_provider_config,
    supported_checkout_period_months,
    validate_checkout_provider_credentials,
)


def provider_settings(**overrides: str) -> SimpleNamespace:
    values = {
        "monobank_token_test": "test-token",
        "monobank_token": "production-token",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def runtime_settings(**overrides: str) -> dict[str, str]:
    values = {
        "billing_provider": "monobank",
        "monobank_mode": "test",
    }
    values.update(overrides)
    return values


def test_resolve_checkout_provider_config_returns_monobank_metadata() -> None:
    config = resolve_checkout_provider_config(runtime_settings(), provider_settings())

    assert config == BillingCheckoutProviderConfig(
        provider_key="monobank",
        provider_mode="test",
        webhook_path="/api/v1/billing/monobank/webhook",
        invoice_unavailable_detail="Monobank checkout is temporarily unavailable",
        plan_icon_paths={
            "premium": "/billing/premium-crown.svg",
            "premium_plus": "/billing/premium-plus-crown.svg",
        },
        supported_period_months=(1, 3, 6, 12),
    )


def test_resolve_checkout_provider_config_returns_instant_metadata_without_token_requirements() -> None:
    config = resolve_checkout_provider_config(
        runtime_settings(billing_provider="instant", monobank_mode="disabled"),
        provider_settings(monobank_token_test="", monobank_token=""),
    )

    assert config == BillingCheckoutProviderConfig(
        provider_key="instant",
        provider_mode="instant",
        webhook_path="/api/v1/billing/instant/webhook",
        invoice_unavailable_detail="Instant checkout is temporarily unavailable",
        plan_icon_paths={
            "premium": "/billing/premium-crown.svg",
            "premium_plus": "/billing/premium-plus-crown.svg",
        },
        supported_period_months=(1, 3, 6, 12),
    )


@pytest.mark.parametrize(
    ("monobank_mode", "expected_detail"),
    [
        ("disabled", "Monobank checkout is disabled"),
        ("live", "Unsupported Monobank mode"),
    ],
)
def test_resolve_checkout_provider_config_preserves_monobank_mode_errors(
    monobank_mode: str,
    expected_detail: str,
) -> None:
    with pytest.raises(BillingRuntimeSettingsValidationError) as error:
        resolve_checkout_provider_config(
            runtime_settings(monobank_mode=monobank_mode),
            provider_settings(),
        )

    assert str(error.value) == expected_detail


@pytest.mark.parametrize(
    ("monobank_mode", "token_override", "expected_detail"),
    [
        ("test", {"monobank_token_test": ""}, "MONOBANK_TOKEN_TEST is not configured"),
        ("production", {"monobank_token": ""}, "MONOBANK_TOKEN is not configured"),
    ],
)
def test_resolve_checkout_provider_config_preserves_monobank_token_errors(
    monobank_mode: str,
    token_override: dict[str, str],
    expected_detail: str,
) -> None:
    with pytest.raises(BillingRuntimeSettingsValidationError) as error:
        resolve_checkout_provider_config(
            runtime_settings(monobank_mode=monobank_mode),
            provider_settings(**token_override),
        )

    assert str(error.value) == expected_detail


def test_resolve_checkout_provider_config_keeps_tribute_disabled() -> None:
    with pytest.raises(BillingRuntimeSettingsValidationError) as error:
        resolve_checkout_provider_config(
            runtime_settings(billing_provider="tribute"),
            provider_settings(),
        )

    assert str(error.value) == "Unsupported billing provider"


def test_monobank_disabled_does_not_break_instant_provider_resolution() -> None:
    config = resolve_checkout_provider_config(
        runtime_settings(billing_provider="instant", monobank_mode="disabled"),
        provider_settings(monobank_token_test="", monobank_token=""),
    )

    assert config.provider_key == "instant"
    assert config.provider_mode == "instant"


def test_resolve_checkout_provider_config_rejects_allowed_provider_without_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        provider_config_module,
        "BILLING_PAYMENT_PROVIDERS",
        {"monobank", "futurepay"},
    )

    with pytest.raises(BillingRuntimeSettingsValidationError) as error:
        resolve_checkout_provider_config(
            runtime_settings(billing_provider="futurepay"),
            provider_settings(),
        )

    assert str(error.value) == "Unsupported billing provider"


def test_resolve_checkout_provider_config_uses_registered_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = runtime_settings(billing_provider="fakepay")
    external_provider_settings = provider_settings()
    calls: list[tuple[dict[str, str], object, bool]] = []
    fake_config = BillingCheckoutProviderConfig(
        provider_key="fakepay",
        provider_mode="sandbox",
        webhook_path="/fakepay/webhook",
        invoice_unavailable_detail="FakePay checkout is temporarily unavailable",
        plan_icon_paths={"premium": "/billing/fakepay-premium.svg"},
        supported_period_months=(1, 3),
    )

    def fake_resolver(
        runtime_settings_arg: dict[str, str],
        provider_settings_arg: object,
        *,
        validate_credentials: bool,
    ) -> BillingCheckoutProviderConfig:
        calls.append((runtime_settings_arg, provider_settings_arg, validate_credentials))
        return fake_config

    monkeypatch.setattr(
        provider_config_module,
        "BILLING_PAYMENT_PROVIDERS",
        {"monobank", "fakepay"},
    )
    monkeypatch.setattr(
        provider_config_module,
        "CHECKOUT_PROVIDER_CONFIG_RESOLVERS",
        {
            **provider_config_module.CHECKOUT_PROVIDER_CONFIG_RESOLVERS,
            "fakepay": fake_resolver,
        },
    )

    config = resolve_checkout_provider_config(
        settings,
        external_provider_settings,
        validate_credentials=False,
    )

    assert config == fake_config
    assert calls == [(settings, external_provider_settings, False)]


def test_validate_checkout_provider_credentials_rejects_provider_without_validator() -> None:
    config = BillingCheckoutProviderConfig(
        provider_key="fakepay",
        provider_mode="sandbox",
        webhook_path="/fakepay/webhook",
        invoice_unavailable_detail="FakePay checkout is temporarily unavailable",
        plan_icon_paths={},
        supported_period_months=(1,),
    )

    with pytest.raises(BillingRuntimeSettingsValidationError) as error:
        validate_checkout_provider_credentials(config, provider_settings())

    assert str(error.value) == "Unsupported billing provider"


def test_validate_checkout_provider_credentials_uses_registered_validator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = BillingCheckoutProviderConfig(
        provider_key="fakepay",
        provider_mode="sandbox",
        webhook_path="/fakepay/webhook",
        invoice_unavailable_detail="FakePay checkout is temporarily unavailable",
        plan_icon_paths={},
        supported_period_months=(1,),
    )
    external_provider_settings = provider_settings()
    calls: list[tuple[BillingCheckoutProviderConfig, object]] = []

    def fake_validator(
        config_arg: BillingCheckoutProviderConfig,
        provider_settings_arg: object,
    ) -> None:
        calls.append((config_arg, provider_settings_arg))

    monkeypatch.setattr(
        provider_config_module,
        "CHECKOUT_PROVIDER_CREDENTIAL_VALIDATORS",
        {
            **provider_config_module.CHECKOUT_PROVIDER_CREDENTIAL_VALIDATORS,
            "fakepay": fake_validator,
        },
    )

    validate_checkout_provider_credentials(config, external_provider_settings)

    assert calls == [(config, external_provider_settings)]


def test_build_checkout_webhook_url_uses_provider_webhook_path() -> None:
    config = resolve_checkout_provider_config(runtime_settings(), provider_settings())

    assert (
        build_checkout_webhook_url(config, "https://api.example/")
        == "https://api.example/api/v1/billing/monobank/webhook"
    )


@pytest.mark.parametrize(
    ("plan_key", "expected_url"),
    [
        ("premium", "https://web.example/billing/premium-crown.svg"),
        ("premium_plus", "https://web.example/billing/premium-plus-crown.svg"),
    ],
)
def test_build_checkout_plan_icon_url_uses_provider_icon_paths(
    plan_key: str,
    expected_url: str,
) -> None:
    config = resolve_checkout_provider_config(runtime_settings(), provider_settings())

    assert build_checkout_plan_icon_url(config, "https://web.example/", plan_key) == expected_url


@pytest.mark.parametrize(
    ("plan_key", "period_months", "quote", "expected_description"),
    [
        (
            "premium",
            1,
            None,
            "Підписка CronoLex Premium на 1 міс.",
        ),
        (
            "premium_plus",
            3,
            {"kind": "renewal"},
            "Продовження підписки CronoLex Premium+ на 3 міс.",
        ),
        (
            "premium_plus",
            1,
            {"kind": "upgrade", "base_plan_key": "premium"},
            "Доплата за покращення CronoLex Premium до Premium+",
        ),
    ],
)
def test_build_checkout_subscription_description_preserves_provider_ukrainian_text(
    plan_key: str,
    period_months: int,
    quote: dict[str, str] | None,
    expected_description: str,
) -> None:
    config = resolve_checkout_provider_config(runtime_settings(), provider_settings())

    assert (
        build_checkout_subscription_description(
            config,
            plan_key,
            period_months,
            quote=quote,
        )
        == expected_description
    )


def test_build_checkout_subscription_description_uses_supplied_provider_config() -> None:
    config = BillingCheckoutProviderConfig(
        provider_key="fakepay",
        provider_mode="test",
        webhook_path="/fakepay/webhook",
        invoice_unavailable_detail="FakePay checkout is temporarily unavailable",
        plan_icon_paths={},
        supported_period_months=(1,),
    )

    assert build_checkout_subscription_description(config, "premium", 1) == "Підписка CronoLex Premium на 1 міс."


def test_supported_checkout_period_months_preserves_runtime_order_and_filters_provider_periods() -> None:
    config = BillingCheckoutProviderConfig(
        provider_key="fakepay",
        provider_mode="test",
        webhook_path="/fakepay/webhook",
        invoice_unavailable_detail="FakePay checkout is temporarily unavailable",
        plan_icon_paths={},
        supported_period_months=(12, 1, 3),
    )

    assert supported_checkout_period_months(config, [6, 3, 1, 12]) == [3, 1, 12]


def test_resolved_monobank_checkout_provider_config_supports_known_periods() -> None:
    config = resolve_checkout_provider_config(runtime_settings(), provider_settings())

    assert config.supported_period_months == MONOBANK_SUPPORTED_PERIOD_MONTHS
    assert config.supported_period_months == (1, 3, 6, 12)
