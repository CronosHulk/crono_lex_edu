from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from app.billing.providers.instant.provider import InstantPaymentProvider
from app.billing.providers.monobank.factory import build_monobank_payment_provider
from app.billing.services.provider_port import BillingPaymentProviderFactory
from app.domain.billing.constants import (
    BILLING_PROVIDER_INSTANT,
    BILLING_PROVIDER_MONOBANK,
)

MonobankAuditLogger = Any

BillingProviderBuilder = Callable[[str], Any]


def build_billing_payment_provider_factory(
    *,
    settings: Any,
    monobank_audit_logger: Any,
) -> BillingPaymentProviderFactory:
    def build_billing_payment_provider(
        *,
        provider_key: str,
        provider_mode: str,
    ) -> Any:
        builders: Mapping[str, BillingProviderBuilder] = {
            BILLING_PROVIDER_MONOBANK: lambda: _build_monobank_payment_provider(
                settings=settings,
                provider_mode=provider_mode,
                monobank_audit_logger=monobank_audit_logger,
            ),
            BILLING_PROVIDER_INSTANT: lambda: InstantPaymentProvider(),
        }
        if provider_key not in builders:
            raise RuntimeError(f"Unsupported billing provider: {provider_key}")
        return builders[provider_key]()

    return build_billing_payment_provider


def _build_monobank_payment_provider(
    *,
    settings: Any,
    provider_mode: str,
    monobank_audit_logger: MonobankAuditLogger,
):
    if monobank_audit_logger is None:
        raise RuntimeError("Monobank audit logger is required")
    return build_monobank_payment_provider(
        settings=settings,
        provider_mode=provider_mode,
        audit_logger=monobank_audit_logger,
    )
