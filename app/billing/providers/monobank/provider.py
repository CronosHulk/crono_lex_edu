from __future__ import annotations

from typing import Any, Protocol

from app.billing.providers.monobank.audit import MonobankAuditContext
from app.billing.providers.monobank.client import MonobankCreateInvoiceRequest
from app.billing.services.monobank_receipt_artifacts import (
    monobank_fiscal_checks_fetch_result,
    monobank_receipt_fetch_result,
)
from app.billing.services.provider_port import (
    BillingProviderAuditContext,
    BillingProviderInvoiceCreateRequest,
    BillingProviderInvoiceCreateResult,
    BillingProviderPaymentStatus,
    BillingProviderReceiptFetchResult,
)
from app.domain.billing.constants import BILLING_PROVIDER_MONOBANK
from app.domain.billing.monobank_statuses import monobank_payment_status_from_payload


class MonobankClientPort(Protocol):
    def create_invoice(
        self,
        request: MonobankCreateInvoiceRequest,
        *,
        audit_context: MonobankAuditContext,
    ) -> dict[str, Any]: ...

    def get_invoice_status(
        self,
        invoice_id: str,
        *,
        audit_context: MonobankAuditContext,
    ) -> dict[str, Any]: ...

    def get_receipt(
        self,
        invoice_id: str,
        *,
        audit_context: MonobankAuditContext,
    ) -> dict[str, Any]: ...

    def get_fiscal_checks(
        self,
        invoice_id: str,
        *,
        audit_context: MonobankAuditContext,
    ) -> dict[str, Any]: ...

    def get_public_key(self, *, audit_context: MonobankAuditContext) -> dict[str, Any]: ...


class MonobankPaymentProvider:
    provider_key = BILLING_PROVIDER_MONOBANK

    def __init__(self, client: MonobankClientPort) -> None:
        self.client = client

    def create_invoice(
        self,
        request: BillingProviderInvoiceCreateRequest,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> BillingProviderInvoiceCreateResult:
        payload = self.client.create_invoice(
            _to_monobank_invoice_request(request),
            audit_context=_to_monobank_audit_context(audit_context),
        )
        return BillingProviderInvoiceCreateResult(
            provider_invoice_id=str(payload["invoiceId"]),
            checkout_url=str(payload["pageUrl"]),
            payload=payload,
        )

    def get_invoice_status(
        self,
        invoice_id: str,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> dict[str, Any]:
        return self.client.get_invoice_status(
            invoice_id,
            audit_context=_to_monobank_audit_context(audit_context),
        )

    def get_receipt(
        self,
        invoice_id: str,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> dict[str, Any]:
        return self.client.get_receipt(
            invoice_id,
            audit_context=_to_monobank_audit_context(audit_context),
        )

    def fetch_receipt(
        self,
        invoice_id: str,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> BillingProviderReceiptFetchResult:
        return monobank_receipt_fetch_result(
            self.get_receipt(invoice_id, audit_context=audit_context)
        )

    def get_fiscal_checks(
        self,
        invoice_id: str,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> dict[str, Any]:
        return self.client.get_fiscal_checks(
            invoice_id,
            audit_context=_to_monobank_audit_context(audit_context),
        )

    def fetch_fiscal_checks(
        self,
        invoice_id: str,
        *,
        audit_context: BillingProviderAuditContext,
    ) -> BillingProviderReceiptFetchResult:
        return monobank_fiscal_checks_fetch_result(
            self.get_fiscal_checks(invoice_id, audit_context=audit_context)
        )

    def get_public_key(self, *, audit_context: BillingProviderAuditContext) -> dict[str, Any]:
        return self.client.get_public_key(audit_context=_to_monobank_audit_context(audit_context))

    def resolve_payment_status(
        self, payload: dict[str, Any]
    ) -> BillingProviderPaymentStatus:
        status = monobank_payment_status_from_payload(payload)
        return BillingProviderPaymentStatus(
            provider_status=status.provider_status,
            internal_status=status.internal_status,
            failure_code=status.failure_code,
            failure_reason=status.failure_reason,
        )


def _to_monobank_invoice_request(
    request: BillingProviderInvoiceCreateRequest,
) -> MonobankCreateInvoiceRequest:
    basket_order = []
    for line in request.lines:
        item: dict[str, Any] = {
            "name": line.name,
            "qty": line.quantity,
            "sum": line.amount_minor,
            "code": line.code,
            "total": line.total_minor,
        }
        if line.icon_url:
            item["icon"] = line.icon_url
        basket_order.append(item)
    return MonobankCreateInvoiceRequest(
        amount=request.amount_minor,
        ccy=request.currency,
        merchant_paym_info={
            "reference": request.reference,
            "destination": request.destination,
            "comment": request.comment,
            "basketOrder": basket_order,
        },
        redirect_url=request.redirect_url,
        webhook_url=request.webhook_url,
        validity=request.validity_seconds,
        payment_type=request.payment_type,
    )


def _to_monobank_audit_context(context: BillingProviderAuditContext) -> MonobankAuditContext:
    return MonobankAuditContext(
        source_place=context.source_place,
        actor_user_uuid=context.actor_user_uuid,
        telegram_user_id=context.telegram_user_id,
        payment_id=context.payment_id,
        order_reference=context.order_reference,
        invoice_id=context.invoice_id,
        request_ip=context.request_ip,
    )
