from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.billing.providers.instant.provider import InstantPaymentProvider
from app.billing.providers.registry import build_billing_payment_provider_factory
from app.billing.runtime_settings import BillingRuntimeSettingsValidationError
from app.billing.services.provider_runtime import (
    BillingPaymentProviderRuntime,
    monobank_webhook_provider_key,
    payment_provider_runtime_is_monobank_test,
    resolve_payment_provider_runtime,
    validate_payment_provider_credentials,
)


@pytest.mark.parametrize("provider", [None, ""])
def test_resolve_payment_provider_runtime_falls_back_to_instant(provider: str | None) -> None:
    runtime = resolve_payment_provider_runtime(
        {
            "provider": provider,
            "provider_mode": "production",
        }
    )

    assert runtime == BillingPaymentProviderRuntime(
        provider_key="instant",
        provider_mode="production",
    )


def test_resolve_payment_provider_runtime_returns_explicit_custom_provider() -> None:
    runtime = resolve_payment_provider_runtime(
        provider_key="custom_provider",
        provider_mode="sandbox",
    )

    assert runtime == BillingPaymentProviderRuntime(
        provider_key="custom_provider",
        provider_mode="sandbox",
    )


def test_validate_payment_provider_credentials_noops_for_custom_provider() -> None:
    settings = SimpleNamespace(monobank_token_test="", monobank_token="")
    runtime = BillingPaymentProviderRuntime(
        provider_key="custom_provider",
        provider_mode="production",
    )

    validate_payment_provider_credentials(settings, runtime)


def test_validate_payment_provider_credentials_preserves_missing_monobank_token_error() -> None:
    settings = SimpleNamespace(monobank_token_test="test-token", monobank_token="")
    runtime = BillingPaymentProviderRuntime(
        provider_key="monobank",
        provider_mode="production",
    )

    with pytest.raises(BillingRuntimeSettingsValidationError) as raised:
        validate_payment_provider_credentials(settings, runtime)

    assert str(raised.value) == "MONOBANK_TOKEN is not configured"


def test_payment_provider_runtime_is_monobank_test_for_monobank_test_mode() -> None:
    assert (
        payment_provider_runtime_is_monobank_test(
            BillingPaymentProviderRuntime(
                provider_key="monobank",
                provider_mode="test",
            )
        )
        is True
    )


def test_payment_provider_runtime_is_monobank_test_is_false_for_monobank_production() -> None:
    assert (
        payment_provider_runtime_is_monobank_test(
            BillingPaymentProviderRuntime(
                provider_key="monobank",
                provider_mode="production",
            )
        )
        is False
    )


def test_payment_provider_runtime_is_monobank_test_is_false_for_custom_provider_test_mode() -> None:
    assert (
        payment_provider_runtime_is_monobank_test(
            BillingPaymentProviderRuntime(
                provider_key="custompay",
                provider_mode="test",
            )
        )
        is False
    )


def test_monobank_webhook_provider_key_returns_monobank() -> None:
    assert monobank_webhook_provider_key() == "monobank"


def test_billing_provider_registry_factory_resolves_instant_provider() -> None:
    factory = build_billing_payment_provider_factory(
        settings=SimpleNamespace(),
        monobank_audit_logger=object(),
    )

    provider = factory(provider_key="instant", provider_mode="instant")

    assert isinstance(provider, InstantPaymentProvider)


def test_billing_provider_registry_factory_resolves_monobank_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_builder(*, settings, provider_mode: str, audit_logger):
        calls.append(
            {
                "settings": settings,
                "provider_mode": provider_mode,
                "audit_logger": audit_logger,
            }
        )
        return {"provider": "monobank", "provider_mode": provider_mode}

    monkeypatch.setattr("app.billing.providers.registry.build_monobank_payment_provider", fake_builder)
    settings = SimpleNamespace(monobank_token_test="token")
    audit_logger = object()
    factory = build_billing_payment_provider_factory(
        settings=settings,
        monobank_audit_logger=audit_logger,
    )

    provider = factory(provider_key="monobank", provider_mode="test")

    assert provider == {"provider": "monobank", "provider_mode": "test"}
    assert calls == [
        {
            "settings": settings,
            "provider_mode": "test",
            "audit_logger": audit_logger,
        }
    ]


def test_billing_provider_registry_factory_rejects_unknown_provider() -> None:
    factory = build_billing_payment_provider_factory(
        settings=SimpleNamespace(),
        monobank_audit_logger=object(),
    )

    with pytest.raises(RuntimeError, match="Unsupported billing provider"):
        factory(provider_key="futurepay", provider_mode="test")
