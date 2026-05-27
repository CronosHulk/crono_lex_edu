from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.billing.runtime_settings import MONOBANK_MODE_TEST, validate_monobank_mode_token
from app.domain.billing.constants import BILLING_PROVIDER_INSTANT, BILLING_PROVIDER_MONOBANK


@dataclass(frozen=True)
class BillingPaymentProviderRuntime:
    provider_key: str
    provider_mode: str


def resolve_payment_provider_runtime(
    payment: Mapping[str, Any] | None = None,
    *,
    provider_key: str | None = None,
    provider_mode: str | None = None,
) -> BillingPaymentProviderRuntime:
    if provider_key is None and payment is not None:
        provider_key = str(payment.get("provider") or BILLING_PROVIDER_INSTANT)
    if provider_mode is None and payment is not None:
        provider_mode = str(payment["provider_mode"])
    if provider_mode is None:
        raise ValueError("provider_mode is required")
    return BillingPaymentProviderRuntime(
        provider_key=str(provider_key or BILLING_PROVIDER_INSTANT),
        provider_mode=provider_mode,
    )


def validate_payment_provider_credentials(
    provider_settings: Any,
    runtime: BillingPaymentProviderRuntime,
) -> None:
    if runtime.provider_key != BILLING_PROVIDER_MONOBANK:
        return
    validate_monobank_mode_token(provider_settings, runtime.provider_mode)


def payment_provider_runtime_is_monobank_test(runtime: BillingPaymentProviderRuntime) -> bool:
    return (
        runtime.provider_key == BILLING_PROVIDER_MONOBANK
        and runtime.provider_mode == MONOBANK_MODE_TEST
    )


def monobank_webhook_provider_key() -> str:
    return BILLING_PROVIDER_MONOBANK
