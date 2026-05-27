from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from ecdsa import NIST256p, SigningKey
from ecdsa.util import sigencode_der

from app.billing.providers.monobank.audit import MonobankAuditContext, mask_headers
from app.billing.providers.monobank.client import (
    MonobankAPIError,
    MonobankClient,
    MonobankConfigurationError,
    MonobankCreateInvoiceRequest,
    resolve_monobank_token,
)
from app.billing.providers.monobank.factory import build_monobank_client
from app.billing.providers.monobank.provider import MonobankPaymentProvider
from app.billing.providers.monobank.signature import verify_monobank_webhook_signature
from app.billing.services.provider_port import (
    BillingProviderAuditContext,
    BillingProviderInvoiceCreateRequest,
    BillingProviderInvoiceLine,
    BillingProviderPaymentStatus,
    BillingProviderReceiptFetchResult,
)
from app.config import Settings
from app.domain.billing.monobank_statuses import monobank_payment_status_from_payload


def build_settings(**overrides) -> Settings:
    values = {
        "bot_token": "token",
        "db_host": "localhost",
        "db_port": 5432,
        "db_name": "cronolex",
        "db_user": "user",
        "db_password": "password",
        "app_env": "test",
        "app_timezone": "Europe/Kyiv",
        "app_host": "127.0.0.1",
        "app_port": 8000,
        "monobank_token_test": "test-token",
        "monobank_token": "production-token",
    }
    values.update(overrides)
    return Settings(**values)


class FakeAuditLogger:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def create_monobank_audit_log(self, **kwargs):
        self.rows.append(kwargs)
        return {"id": len(self.rows), **kwargs}


class FakeHttpClient:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.requests: list[dict] = []

    def request(self, method, url, *, headers, json=None, params=None):
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "json": json,
                "params": params,
            }
        )
        return self.response


class FakeMonobankProviderClient:
    def __init__(
        self,
        *,
        receipt_payload: dict[str, Any] | None = None,
        fiscal_payload: dict[str, Any] | None = None,
    ) -> None:
        self.calls: list[dict[str, object]] = []
        self.receipt_payload = receipt_payload or {"file": "JVBERi0xLjQK"}
        self.fiscal_payload = fiscal_payload or {"checks": []}

    def create_invoice(self, request, *, audit_context):
        self.calls.append(
            {"method": "create_invoice", "request": request, "audit_context": audit_context}
        )
        return {"invoiceId": "p2_demo", "pageUrl": "https://pay.example/p2_demo"}

    def get_invoice_status(self, invoice_id: str, *, audit_context):
        self.calls.append(
            {"method": "get_invoice_status", "invoice_id": invoice_id, "audit_context": audit_context}
        )
        return {"invoiceId": invoice_id, "status": "success"}

    def get_receipt(self, invoice_id: str, *, audit_context):
        self.calls.append(
            {"method": "get_receipt", "invoice_id": invoice_id, "audit_context": audit_context}
        )
        return self.receipt_payload

    def get_fiscal_checks(self, invoice_id: str, *, audit_context):
        self.calls.append(
            {"method": "get_fiscal_checks", "invoice_id": invoice_id, "audit_context": audit_context}
        )
        return self.fiscal_payload

    def get_public_key(self, *, audit_context):
        self.calls.append({"method": "get_public_key", "audit_context": audit_context})
        return {"key": "public"}


def test_mask_headers_redacts_monobank_token() -> None:
    assert mask_headers({"X-Token": "secret", "Content-Type": "application/json"}) == {
        "X-Token": "[redacted]",
        "Content-Type": "application/json",
    }


def test_resolve_monobank_token_uses_provider_mode() -> None:
    settings = build_settings()

    assert resolve_monobank_token(settings, "test") == "test-token"
    assert resolve_monobank_token(settings, "production") == "production-token"


def test_resolve_monobank_token_rejects_missing_mode_token() -> None:
    settings = build_settings(monobank_token_test="")

    with pytest.raises(MonobankConfigurationError, match="test"):
        resolve_monobank_token(settings, "test")


def test_build_monobank_client_wires_settings_provider_mode_and_audit_logger() -> None:
    settings = build_settings()
    audit_logger = FakeAuditLogger()

    client = build_monobank_client(
        settings=settings,
        provider_mode="test",
        audit_logger=audit_logger,
    )

    assert isinstance(client, MonobankClient)
    assert client.settings is settings
    assert client.provider_mode == "test"
    assert client.audit_logger is audit_logger
    assert client.token == "test-token"


def test_monobank_payment_provider_adapts_generic_invoice_request_and_audit_context() -> None:
    client = FakeMonobankProviderClient()
    provider = MonobankPaymentProvider(client)

    result = provider.create_invoice(
        BillingProviderInvoiceCreateRequest(
            amount_minor=1234,
            currency=980,
            reference="clx-order-1",
            destination="CronoLex Premium",
            comment="User: 42",
            lines=(
                BillingProviderInvoiceLine(
                    name="CronoLex Premium",
                    quantity=1,
                    amount_minor=1234,
                    code="premium",
                    total_minor=1234,
                    icon_url="https://web.example/billing/premium-crown.svg",
                ),
            ),
            redirect_url="https://web.example/plans?payment_id=1",
            webhook_url="https://api.example/api/v1/billing/monobank/webhook",
            validity_seconds=3600,
        ),
        audit_context=BillingProviderAuditContext(
            source_place="checkout",
            actor_user_uuid="11111111-1111-4111-8111-111111111111",
            telegram_user_id=42,
            payment_id=1,
            order_reference="clx-order-1",
            request_ip="127.0.0.1",
        ),
    )
    provider.get_invoice_status(
        "p2_demo",
        audit_context=BillingProviderAuditContext(
            source_place="status",
            telegram_user_id=42,
            invoice_id="p2_demo",
        ),
    )

    assert result.provider_invoice_id == "p2_demo"
    assert result.checkout_url == "https://pay.example/p2_demo"
    invoice_request = client.calls[0]["request"]
    audit_context = client.calls[0]["audit_context"]
    status_audit_context = client.calls[1]["audit_context"]
    assert type(invoice_request) is MonobankCreateInvoiceRequest
    assert type(audit_context) is MonobankAuditContext
    assert type(status_audit_context) is MonobankAuditContext
    assert audit_context.source_place == "checkout"
    assert audit_context.actor_user_uuid == "11111111-1111-4111-8111-111111111111"
    assert audit_context.telegram_user_id == 42
    assert audit_context.payment_id == 1
    assert audit_context.order_reference == "clx-order-1"
    assert audit_context.request_ip == "127.0.0.1"
    assert invoice_request.to_payload() == {
        "amount": 1234,
        "ccy": 980,
        "merchantPaymInfo": {
            "reference": "clx-order-1",
            "destination": "CronoLex Premium",
            "comment": "User: 42",
            "basketOrder": [
                {
                    "name": "CronoLex Premium",
                    "qty": 1,
                    "sum": 1234,
                    "code": "premium",
                    "total": 1234,
                    "icon": "https://web.example/billing/premium-crown.svg",
                }
            ],
        },
        "redirectUrl": "https://web.example/plans?payment_id=1",
        "webHookUrl": "https://api.example/api/v1/billing/monobank/webhook",
        "validity": 3600,
        "paymentType": "debit",
    }
    assert client.calls[1]["method"] == "get_invoice_status"
    assert client.calls[1]["invoice_id"] == "p2_demo"
    assert status_audit_context.source_place == "status"
    assert status_audit_context.invoice_id == "p2_demo"


def test_monobank_payment_provider_fetches_normalized_receipt_artifacts() -> None:
    client = FakeMonobankProviderClient(
        receipt_payload={"file": "JVBERi0xLjQK", "source": "receipt-endpoint"},
        fiscal_payload={
            "checks": [
                {
                    "id": "check-1",
                    "status": "done",
                    "type": "sale",
                    "fiscalizationSource": "checkbox",
                    "taxUrl": "https://tax.example/check-1",
                    "file": "RklTQ0FMCg==",
                }
            ]
        },
    )
    provider = MonobankPaymentProvider(client)
    audit_context = BillingProviderAuditContext(
        source_place="billing_bot_receipt",
        actor_user_uuid="11111111-1111-4111-8111-111111111111",
        telegram_user_id=42,
        payment_id=7,
        order_reference="clx-order-7",
        invoice_id="p2_demo",
        request_ip="127.0.0.1",
    )

    receipt_result = provider.fetch_receipt("p2_demo", audit_context=audit_context)
    fiscal_result = provider.fetch_fiscal_checks("p2_demo", audit_context=audit_context)

    assert type(receipt_result) is BillingProviderReceiptFetchResult
    assert receipt_result.receipt_type == "receipt"
    assert receipt_result.provider_payload == {"file": "JVBERi0xLjQK", "source": "receipt-endpoint"}
    assert receipt_result.artifacts[0].receipt_type == "receipt"
    assert receipt_result.artifacts[0].status == "done"
    assert receipt_result.artifacts[0].file_base64 == "JVBERi0xLjQK"
    assert receipt_result.artifacts[0].payload == {
        "file": "JVBERi0xLjQK",
        "source": "receipt-endpoint",
    }
    assert type(fiscal_result) is BillingProviderReceiptFetchResult
    assert fiscal_result.receipt_type == "fiscal_check"
    assert fiscal_result.provider_payload == client.fiscal_payload
    assert fiscal_result.artifacts[0].receipt_type == "fiscal_check"
    assert fiscal_result.artifacts[0].status == "done"
    assert fiscal_result.artifacts[0].provider_check_id == "check-1"
    assert fiscal_result.artifacts[0].fiscalization_source == "checkbox"
    assert fiscal_result.artifacts[0].tax_url == "https://tax.example/check-1"
    assert fiscal_result.artifacts[0].file_base64 == "RklTQ0FMCg=="
    assert fiscal_result.artifacts[0].payload == client.fiscal_payload["checks"][0]
    assert [call["method"] for call in client.calls] == ["get_receipt", "get_fiscal_checks"]
    assert [call["invoice_id"] for call in client.calls] == ["p2_demo", "p2_demo"]
    for call in client.calls:
        mono_audit_context = call["audit_context"]
        assert type(mono_audit_context) is MonobankAuditContext
        assert mono_audit_context.source_place == "billing_bot_receipt"
        assert mono_audit_context.actor_user_uuid == "11111111-1111-4111-8111-111111111111"
        assert mono_audit_context.telegram_user_id == 42
        assert mono_audit_context.payment_id == 7
        assert mono_audit_context.order_reference == "clx-order-7"
        assert mono_audit_context.invoice_id == "p2_demo"
        assert mono_audit_context.request_ip == "127.0.0.1"


def test_monobank_status_maps_hold_to_processing() -> None:
    status = monobank_payment_status_from_payload({"status": "hold", "invoiceId": "p2_demo"})

    assert status.provider_status == "hold"
    assert status.internal_status == "processing"
    assert status.failure_code is None
    assert status.failure_reason is None


def test_monobank_status_trims_failure_fields() -> None:
    status = monobank_payment_status_from_payload(
        {
            "status": "failure",
            "errCode": f" {'E' * 140} ",
            "failureReason": f" {'R' * 1100} ",
        }
    )

    assert status.provider_status == "failure"
    assert status.internal_status == "failure"
    assert status.failure_code == "E" * 128
    assert status.failure_reason == "R" * 1024


def test_monobank_payment_provider_resolves_generic_payment_status() -> None:
    provider = MonobankPaymentProvider(FakeMonobankProviderClient())

    status = provider.resolve_payment_status(
        {
            "invoiceId": "p2_demo",
            "status": "failure",
            "errCode": " CARD_DECLINED ",
            "failureReason": " Insufficient funds ",
        }
    )

    assert status == BillingProviderPaymentStatus(
        provider_status="failure",
        internal_status="failure",
        failure_code="CARD_DECLINED",
        failure_reason="Insufficient funds",
    )


def test_create_invoice_posts_payload_and_writes_audit() -> None:
    response = httpx.Response(200, json={"invoiceId": "p2_demo", "pageUrl": "https://pay.example/p2_demo"})
    http_client = FakeHttpClient(response)
    audit_logger = FakeAuditLogger()
    current_time = datetime(2026, 5, 6, 10, 0, tzinfo=UTC)
    client = MonobankClient(
        settings=build_settings(),
        provider_mode="test",
        audit_logger=audit_logger,
        http_client=http_client,
        base_url="https://mono.example",
        clock=lambda: current_time,
    )

    payload = client.create_invoice(
        MonobankCreateInvoiceRequest(
            amount=1000,
            merchant_paym_info={"reference": "order-1", "destination": "CronoLex premium"},
            redirect_url="https://app.example/plans/result",
            webhook_url="https://api.example/api/v1/billing/monobank/webhook",
            validity=3600,
        ),
        audit_context=MonobankAuditContext(
            source_place="checkout",
            telegram_user_id=42,
            order_reference="order-1",
            request_ip="127.0.0.1",
        ),
    )

    assert payload["invoiceId"] == "p2_demo"
    assert http_client.requests[0]["method"] == "POST"
    assert http_client.requests[0]["url"] == "https://mono.example/api/merchant/invoice/create"
    assert http_client.requests[0]["json"]["amount"] == 1000
    assert http_client.requests[0]["headers"]["X-Token"] == "test-token"
    assert audit_logger.rows[0]["direction"] == "outgoing"
    assert audit_logger.rows[0]["request_headers_json"]["X-Token"] == "[redacted]"
    assert audit_logger.rows[0]["request_body_json"]["merchantPaymInfo"]["reference"] == "order-1"
    assert audit_logger.rows[0]["response_body_json"]["invoiceId"] == "p2_demo"
    assert audit_logger.rows[0]["invoice_id"] == "p2_demo"
    assert audit_logger.rows[0]["telegram_user_id"] == 42


def test_get_invoice_status_adds_query_and_audit_invoice_id() -> None:
    response = httpx.Response(200, json={"invoiceId": "p2_demo", "status": "success", "amount": 1000, "ccy": 980})
    http_client = FakeHttpClient(response)
    audit_logger = FakeAuditLogger()
    client = MonobankClient(
        settings=build_settings(),
        provider_mode="production",
        audit_logger=audit_logger,
        http_client=http_client,
        base_url="https://mono.example",
    )

    payload = client.get_invoice_status("p2_demo", audit_context=MonobankAuditContext(source_place="polling"))

    assert payload["status"] == "success"
    assert http_client.requests[0]["params"] == {"invoiceId": "p2_demo"}
    assert audit_logger.rows[0]["provider_mode"] == "production"
    assert audit_logger.rows[0]["invoice_id"] == "p2_demo"
    assert audit_logger.rows[0]["request_url"] == "https://mono.example/api/merchant/invoice/status?invoiceId=p2_demo"


def test_provider_error_includes_monobank_error_and_writes_audit() -> None:
    response = httpx.Response(400, json={"errCode": "BAD_REQUEST", "errText": "invalid invoice"})
    http_client = FakeHttpClient(response)
    audit_logger = FakeAuditLogger()
    client = MonobankClient(
        settings=build_settings(),
        provider_mode="test",
        audit_logger=audit_logger,
        http_client=http_client,
    )

    with pytest.raises(MonobankAPIError) as raised:
        client.get_invoice_status("bad", audit_context=MonobankAuditContext(source_place="reconciliation"))

    assert raised.value.status_code == 400
    assert raised.value.error_code == "BAD_REQUEST"
    assert "invalid invoice" in str(raised.value)
    assert audit_logger.rows[0]["response_status_code"] == 400
    assert audit_logger.rows[0]["response_body_json"]["errCode"] == "BAD_REQUEST"
    assert audit_logger.rows[0]["error_text"] == "invalid invoice"


def test_verify_monobank_webhook_signature_accepts_valid_der_signature() -> None:
    body = b'{"invoiceId":"p2_demo","status":"success"}'
    signing_key = SigningKey.generate(curve=NIST256p)
    signature = signing_key.sign_digest_deterministic(
        hashlib.sha256(body).digest(),
        sigencode=sigencode_der,
    )
    public_key_base64 = base64.b64encode(signing_key.verifying_key.to_pem()).decode()
    signature_base64 = base64.b64encode(signature).decode()

    assert verify_monobank_webhook_signature(
        public_key_base64=public_key_base64,
        signature_base64=signature_base64,
        raw_body=body,
    )
    assert not verify_monobank_webhook_signature(
        public_key_base64=public_key_base64,
        signature_base64=signature_base64,
        raw_body=b'{"invoiceId":"p2_demo","status":"failure"}',
    )
