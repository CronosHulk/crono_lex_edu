from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

BILLING_PROVIDER_AUDIT_SECRET_HEADER_NAMES = {"authorization", "x-token", "x-api-key", "api-key"}


@dataclass(frozen=True)
class BillingProviderAuditContext:
    source_place: str
    actor_user_uuid: str | UUID | None = None
    telegram_user_id: int | None = None
    payment_id: int | None = None
    order_reference: str | None = None
    invoice_id: str | None = None
    request_ip: str | None = None


def mask_billing_provider_audit_headers(headers: dict[str, Any]) -> dict[str, Any]:
    masked: dict[str, Any] = {}
    for key, value in headers.items():
        masked[key] = (
            "[redacted]" if key.lower() in BILLING_PROVIDER_AUDIT_SECRET_HEADER_NAMES else value
        )
    return masked


def billing_provider_audit_duration_ms(started: datetime, finished: datetime) -> int:
    return max(int((finished - started).total_seconds() * 1000), 0)


@dataclass(frozen=True)
class BillingProviderInvoiceLine:
    name: str
    quantity: int
    amount_minor: int
    code: str
    total_minor: int
    icon_url: str | None = None


@dataclass(frozen=True)
class BillingProviderInvoiceCreateRequest:
    amount_minor: int
    currency: int
    reference: str
    destination: str
    comment: str | None
    lines: tuple[BillingProviderInvoiceLine, ...]
    redirect_url: str
    webhook_url: str
    validity_seconds: int
    payment_type: str = "debit"


@dataclass(frozen=True)
class BillingProviderInvoiceCreateResult:
    provider_invoice_id: str
    checkout_url: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class BillingProviderAPIErrorDetails:
    status_code: int | None
    error_code: str | None


@dataclass(frozen=True)
class BillingProviderPaymentStatus:
    provider_status: str
    internal_status: str
    failure_code: str | None = None
    failure_reason: str | None = None


@dataclass(frozen=True)
class BillingProviderWebhookPayload:
    invoice_id: str
    provider_status: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class BillingProviderReceiptArtifact:
    receipt_type: str
    status: str
    provider_check_id: str | None = None
    fiscalization_source: str | None = None
    tax_url: str | None = None
    file_base64: str | None = None
    payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class BillingProviderReceiptFetchResult:
    receipt_type: str
    artifacts: tuple[BillingProviderReceiptArtifact, ...] = ()
    unavailable_reason: str | None = None
    provider_payload: dict[str, Any] | None = None


def billing_provider_api_error_details(
    error: BaseException,
) -> BillingProviderAPIErrorDetails | None:
    missing = object()
    status_code = getattr(error, "status_code", missing)
    error_code = getattr(error, "error_code", missing)
    if status_code is missing and error_code is missing:
        return None
    return BillingProviderAPIErrorDetails(
        status_code=status_code if isinstance(status_code, int) else None,
        error_code=str(error_code)
        if error_code is not missing and error_code is not None
        else None,
    )


class BillingInvoiceStatusProviderPort(Protocol):
    provider_key: str

    def create_invoice(
        self,
        request: BillingProviderInvoiceCreateRequest,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> BillingProviderInvoiceCreateResult: ...

    def get_invoice_status(
        self,
        invoice_id: str,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> dict[str, Any]: ...

    def resolve_payment_status(
        self, payload: dict[str, Any]
    ) -> BillingProviderPaymentStatus: ...


class BillingReceiptFiscalProviderPort(Protocol):
    def fetch_receipt(
        self,
        invoice_id: str,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> BillingProviderReceiptFetchResult: ...

    def fetch_fiscal_checks(
        self,
        invoice_id: str,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> BillingProviderReceiptFetchResult: ...


class BillingWebhookPublicKeyProviderPort(Protocol):
    def get_public_key(self, *, audit_context: BillingProviderAuditContext) -> dict[str, Any]: ...


class BillingPaymentProviderPort(
    BillingInvoiceStatusProviderPort,
    BillingReceiptFiscalProviderPort,
    BillingWebhookPublicKeyProviderPort,
    Protocol,
):
    def get_receipt(
        self,
        invoice_id: str,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> dict[str, Any]: ...

    def fetch_receipt(
        self,
        invoice_id: str,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> BillingProviderReceiptFetchResult: ...

    def get_fiscal_checks(
        self,
        invoice_id: str,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> dict[str, Any]: ...


BillingInvoiceStatusProviderFactory = Callable[..., BillingInvoiceStatusProviderPort]
BillingReceiptFiscalProviderFactory = Callable[..., BillingReceiptFiscalProviderPort]
BillingWebhookPublicKeyProviderFactory = Callable[..., BillingWebhookPublicKeyProviderPort]
BillingPaymentProviderFactory = Callable[..., BillingPaymentProviderPort]


class BillingWebhookSignatureVerifier(Protocol):
    def __call__(
        self,
        *,
        public_key_base64: str,
        signature_base64: str,
        raw_body: bytes,
    ) -> bool: ...


def require_billing_payment_provider_factory(
    billing_provider_factory: BillingPaymentProviderFactory | None,
) -> BillingPaymentProviderFactory:
    if billing_provider_factory is None:
        raise RuntimeError("Billing payment provider factory is not configured")
    return billing_provider_factory


def require_billing_invoice_status_provider_factory(
    billing_provider_factory: BillingInvoiceStatusProviderFactory | None,
) -> BillingInvoiceStatusProviderFactory:
    if billing_provider_factory is None:
        raise RuntimeError("Billing invoice status provider factory is not configured")
    return billing_provider_factory


def require_billing_receipt_fiscal_provider_factory(
    billing_provider_factory: BillingReceiptFiscalProviderFactory | None,
) -> BillingReceiptFiscalProviderFactory:
    if billing_provider_factory is None:
        raise RuntimeError("Billing receipt fiscal provider factory is not configured")
    return billing_provider_factory


def require_billing_webhook_public_key_provider_factory(
    billing_provider_factory: BillingWebhookPublicKeyProviderFactory | None,
) -> BillingWebhookPublicKeyProviderFactory:
    if billing_provider_factory is None:
        raise RuntimeError("Billing webhook public key provider factory is not configured")
    return billing_provider_factory


def require_billing_webhook_signature_verifier(
    billing_signature_verifier: BillingWebhookSignatureVerifier | None,
) -> BillingWebhookSignatureVerifier:
    if billing_signature_verifier is None:
        raise RuntimeError("Billing webhook signature verifier is not configured")
    return billing_signature_verifier
