from __future__ import annotations

from app.billing.providers.monobank.audit import MonobankAuditLogger
from app.billing.providers.monobank.client import MonobankClient
from app.billing.providers.monobank.provider import MonobankPaymentProvider
from app.config import Settings


def build_monobank_client(
    *,
    settings: Settings,
    provider_mode: str,
    audit_logger: MonobankAuditLogger,
) -> MonobankClient:
    return MonobankClient(
        settings=settings,
        provider_mode=provider_mode,
        audit_logger=audit_logger,
    )


def build_monobank_payment_provider(
    *,
    settings: Settings,
    provider_mode: str,
    audit_logger: MonobankAuditLogger,
) -> MonobankPaymentProvider:
    return MonobankPaymentProvider(
        build_monobank_client(
            settings=settings,
            provider_mode=provider_mode,
            audit_logger=audit_logger,
        )
    )
