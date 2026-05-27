from __future__ import annotations

from uuid import uuid4

from app.billing.services.provider_port import (
    BillingPaymentProviderPort,
    BillingProviderAuditContext,
    BillingProviderInvoiceCreateRequest,
    BillingProviderInvoiceCreateResult,
    BillingProviderPaymentStatus,
    BillingProviderReceiptFetchResult,
)
from app.domain.billing.constants import BILLING_PROVIDER_INSTANT


class InstantPaymentProvider(BillingPaymentProviderPort):
    provider_key = BILLING_PROVIDER_INSTANT

    def create_invoice(
        self,
        request: BillingProviderInvoiceCreateRequest,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> BillingProviderInvoiceCreateResult:
        provider_invoice_id = f"instant-{uuid4().hex}"
        return BillingProviderInvoiceCreateResult(
            provider_invoice_id=provider_invoice_id,
            checkout_url=request.redirect_url,
            payload={
                "provider": BILLING_PROVIDER_INSTANT,
                "provider_invoice_id": provider_invoice_id,
                "status": "success",
            },
        )

    def get_invoice_status(
        self,
        invoice_id: str,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> dict:
        return {
            "provider": BILLING_PROVIDER_INSTANT,
            "invoice_id": invoice_id,
            "status": "success",
        }

    def resolve_payment_status(
        self, payload: dict
    ) -> BillingProviderPaymentStatus:
        return BillingProviderPaymentStatus(
            provider_status="success",
            internal_status="success",
            failure_code=None,
            failure_reason=None,
        )

    def get_receipt(
        self,
        invoice_id: str,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> dict:
        return {"provider": BILLING_PROVIDER_INSTANT, "invoice_id": invoice_id}

    def fetch_receipt(
        self,
        invoice_id: str,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> BillingProviderReceiptFetchResult:
        return BillingProviderReceiptFetchResult(
            receipt_type="receipt",
            unavailable_reason="instant_receipt_unavailable",
            provider_payload={"provider": BILLING_PROVIDER_INSTANT, "invoice_id": invoice_id},
        )

    def get_fiscal_checks(
        self,
        invoice_id: str,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> dict:
        return {"provider": BILLING_PROVIDER_INSTANT, "invoice_id": invoice_id}

    def fetch_fiscal_checks(
        self,
        invoice_id: str,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> BillingProviderReceiptFetchResult:
        return BillingProviderReceiptFetchResult(
            receipt_type="fiscal_check",
            unavailable_reason="instant_fiscal_checks_unavailable",
            provider_payload={"provider": BILLING_PROVIDER_INSTANT, "invoice_id": invoice_id},
        )

    def get_public_key(self, *, audit_context: BillingProviderAuditContext) -> dict:
        return {}
