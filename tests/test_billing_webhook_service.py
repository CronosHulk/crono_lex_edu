from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from ecdsa import NIST256p, SigningKey
from ecdsa.util import sigencode_der

from app.billing.providers.monobank.signature import verify_monobank_webhook_signature
from app.billing.providers.monobank.webhook_adapter import (
    BillingWebhookPayloadError,
    MonobankWebhookAdapter,
)
from app.billing.providers.monobank.webhook_payload import (
    parse_monobank_webhook_payload as parse_provider_monobank_webhook_payload,
)
from app.billing.services.monobank_receipt_artifacts import monobank_fiscal_checks_fetch_result
from app.billing.services.provider_port import (
    BillingProviderPaymentStatus,
    BillingProviderWebhookPayload,
)
from app.billing.services.webhook_service import (
    BillingWebhookService,
    MonobankWebhookError,
)
from app.domain.billing.monobank_statuses import monobank_payment_status_from_payload

USER_UUID = "00000000-0000-4000-8000-000000000042"
WEBHOOK_ADAPTER = MonobankWebhookAdapter()


class FakeTimeService:
    def __init__(self) -> None:
        self.current_time = datetime(2026, 5, 6, 10, 0, tzinfo=UTC)

    def now(self):
        return self.current_time


class FakeBillingRepository:
    def __init__(self) -> None:
        self.payment = {
            "id": 7,
            "user_uuid": USER_UUID,
            "telegram_user_id": 42,
            "provider_mode": "test",
            "provider_reference": "clx-order-7",
            "provider_invoice_id": "p2_demo",
            "plan_key": "premium",
            "period_months": 1,
            "status": "invoice_created",
        }
        self.audit_rows: list[dict] = []
        self.status_updates: list[dict] = []
        self.events: list[dict] = []
        self.applied_purchases: list[dict] = []
        self.receipts: list[dict] = []

    def get_payment_by_provider_invoice_id(self, provider_invoice_id: str):
        if provider_invoice_id == self.payment["provider_invoice_id"]:
            return dict(self.payment)
        return None

    def update_payment_provider_status(self, payment_id: int, **kwargs):
        self.status_updates.append({"payment_id": payment_id, **kwargs})
        self.payment = {**self.payment, **kwargs, "id": payment_id}
        return dict(self.payment)

    def create_payment_event(self, **kwargs):
        self.events.append(kwargs)
        return {"id": len(self.events), **kwargs}

    def create_monobank_audit_log(self, **kwargs):
        self.audit_rows.append(kwargs)
        return {"id": len(self.audit_rows), **kwargs}

    def list_payment_receipts(self, payment_id: int):
        return [dict(row) for row in self.receipts if row["payment_id"] == payment_id]

    def create_receipt(self, **kwargs):
        row = {"id": len(self.receipts) + 1, **kwargs}
        self.receipts.append(row)
        return dict(row)

    def apply_subscription_purchase_for_payment(self, payment: dict[str, object], *, current_time: datetime):
        self.applied_purchases.append({"payment": payment, "current_time": current_time})
        return {
            "purchase": {"payment_id": payment["id"]},
            "subscription": {
                "user_uuid": payment["user_uuid"],
                "plan_key": payment["plan_key"],
                "start": current_time,
                "end": current_time,
            },
        }

    def reverse_subscription_purchase_projection_for_payment(self, payment_id: int, *, current_time: datetime):
        return None


class FakeAppSettingsRepository:
    def get_value(self, key: str):
        if key == "billing.runtime_settings":
            return {"offer_text": "CronoLex paid subscription offer text for tests."}
        if key == "billing.monobank_mode":
            return {"monobank_mode": "test"}
        return None


class FakeSubscriptions:
    def __init__(self) -> None:
        self.activations: list[dict[str, object]] = []

    def activate_paid_plan_for_user(self, user_uuid: str, **kwargs):
        payload = {"user_uuid": user_uuid, **kwargs}
        self.activations.append(payload)
        return {
            "user_uuid": user_uuid,
            "plan_key": kwargs["plan_key"],
            "start": kwargs["current_time"],
            "end": kwargs["current_time"],
        }


class FakeDatabase:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(monobank_token_test="test-token", monobank_token="production-token")
        self.billing = FakeBillingRepository()
        self.subscriptions = FakeSubscriptions()
        self.app_settings = FakeAppSettingsRepository()


class FakeMonobankClient:
    def __init__(self, *, provider_mode: str, public_key: str, status_error: Exception | None = None) -> None:
        self.provider_mode = provider_mode
        self.public_key = public_key
        self.status_error = status_error

    def get_public_key(self, *, audit_context):
        return {"key": self.public_key}

    def get_invoice_status(self, invoice_id: str, *, audit_context):
        if self.status_error is not None:
            raise self.status_error
        return {"invoiceId": invoice_id, "status": "success", "amount": 1000, "ccy": 980}

    def get_fiscal_checks(self, invoice_id: str, *, audit_context):
        return {"checks": []}

    def resolve_payment_status(self, payload: dict[str, object]) -> BillingProviderPaymentStatus:
        status = monobank_payment_status_from_payload(payload)
        return BillingProviderPaymentStatus(
            provider_status=status.provider_status,
            internal_status=status.internal_status,
            failure_code=status.failure_code,
            failure_reason=status.failure_reason,
        )

    def fetch_fiscal_checks(self, invoice_id: str, *, audit_context):
        return monobank_fiscal_checks_fetch_result(
            self.get_fiscal_checks(invoice_id, audit_context=audit_context)
        )


class FakeBillingProvider:
    def __init__(
        self,
        *,
        public_key: str,
        payload: dict[str, object],
        provider_status: BillingProviderPaymentStatus,
    ) -> None:
        self.public_key = public_key
        self.payload = payload
        self.provider_status = provider_status
        self.public_key_calls: list[dict[str, object]] = []
        self.status_calls: list[dict[str, object]] = []
        self.resolve_calls: list[dict[str, object]] = []

    def get_public_key(self, *, audit_context):
        self.public_key_calls.append({"audit_context": audit_context})
        return {"key": self.public_key}

    def get_invoice_status(self, invoice_id: str, *, audit_context):
        self.status_calls.append({"invoice_id": invoice_id, "audit_context": audit_context})
        return dict(self.payload)

    def resolve_payment_status(self, payload: dict[str, object]) -> BillingProviderPaymentStatus:
        self.resolve_calls.append(dict(payload))
        return self.provider_status

    def get_fiscal_checks(self, invoice_id: str, *, audit_context):
        return {"checks": []}


class FakeMonobankWebhookAdapter:
    def __init__(self, *, webhook_payload: BillingProviderWebhookPayload, signature_valid: bool = True) -> None:
        self.webhook_payload = webhook_payload
        self.signature_valid = signature_valid
        self.parse_calls: list[bytes] = []
        self.verify_calls: list[dict[str, object]] = []

    def parse_webhook_payload(self, raw_body: bytes) -> BillingProviderWebhookPayload:
        self.parse_calls.append(raw_body)
        return self.webhook_payload

    def verify_signature(self, *, provider_mode: str, signature_base64: str, raw_body: bytes) -> bool:
        self.verify_calls.append(
            {
                "provider_mode": provider_mode,
                "signature_base64": signature_base64,
                "raw_body": raw_body,
            }
        )
        return self.signature_valid


def build_signature(raw_body: bytes, signing_key: SigningKey) -> str:
    signature = signing_key.sign_digest_deterministic(hashlib.sha256(raw_body).digest(), sigencode=sigencode_der)
    return base64.b64encode(signature).decode()


def build_service(
    db: FakeDatabase,
    public_key: str,
    *,
    status_error: Exception | None = None,
    billing_provider_factory=None,
    monobank_signature_verifier=verify_monobank_webhook_signature,
    monobank_webhook_adapter=None,
) -> BillingWebhookService:
    BillingWebhookService._public_key_cache = {}
    provider_factory = billing_provider_factory or (
        lambda provider_key, provider_mode: FakeMonobankClient(
            provider_mode=provider_mode,
            public_key=public_key,
            status_error=status_error,
        )
    )
    webhook_adapter = monobank_webhook_adapter or MonobankWebhookAdapter(
        billing_webhook_public_key_provider_factory=provider_factory,
        monobank_signature_verifier=monobank_signature_verifier,
    )
    return BillingWebhookService(
        db,
        FakeTimeService(),
        billing_provider_factory=provider_factory,
        monobank_signature_verifier=monobank_signature_verifier,
        monobank_webhook_adapter=webhook_adapter,
    )


def test_monobank_webhook_adapter_reuses_passed_empty_public_key_cache_and_populates_it() -> None:
    public_key_cache: dict[str, str] = {}
    provider_factory_calls: list[tuple[str, str]] = []
    verifier_calls: list[dict[str, object]] = []

    class _FakePublicKeyProvider:
        def get_public_key(self, *, audit_context):
            return {"key": "cached-test-key"}

    def billing_public_key_provider_factory(provider_key: str, provider_mode: str):
        provider_factory_calls.append((provider_key, provider_mode))
        return _FakePublicKeyProvider()

    def signature_verifier(*, public_key_base64: str, signature_base64: str, raw_body: bytes) -> bool:
        verifier_calls.append(
            {
                "public_key_base64": public_key_base64,
                "signature_base64": signature_base64,
                "raw_body": raw_body,
            }
        )
        return True

    adapter = MonobankWebhookAdapter(
        billing_webhook_public_key_provider_factory=billing_public_key_provider_factory,
        monobank_signature_verifier=signature_verifier,
        public_key_cache=public_key_cache,
    )
    assert adapter._public_key_cache is public_key_cache

    assert adapter.verify_signature(
        provider_mode="test",
        signature_base64="signature-value",
        raw_body=b'{"invoiceId":"p2_demo","status":"processing"}',
    )
    assert adapter.verify_signature(
        provider_mode="test",
        signature_base64="signature-value-2",
        raw_body=b'{"invoiceId":"p2_demo","status":"success"}',
    )

    assert adapter._public_key_cache is public_key_cache
    assert public_key_cache == {"test": "cached-test-key"}
    assert provider_factory_calls == [("monobank", "test")]
    assert verifier_calls[0]["public_key_base64"] == "cached-test-key"
    assert verifier_calls[1]["public_key_base64"] == "cached-test-key"


def test_parse_monobank_webhook_payload_returns_provider_payload() -> None:
    raw_body = b'{"invoiceId":" p2_demo ","status":"success","amount":1000,"ccy":980}'

    payload = WEBHOOK_ADAPTER.parse_webhook_payload(raw_body)

    assert payload == BillingProviderWebhookPayload(
        invoice_id="p2_demo",
        provider_status="success",
        payload={"invoiceId": " p2_demo ", "status": "success", "amount": 1000, "ccy": 980},
    )


@pytest.mark.parametrize("raw_body", [b"not-json", b'["not", "object"]'])
def test_parse_monobank_webhook_payload_rejects_invalid_json_or_non_object(
    raw_body: bytes,
) -> None:
    with pytest.raises(BillingWebhookPayloadError) as raised:
        WEBHOOK_ADAPTER.parse_webhook_payload(raw_body)

    assert raised.value.status_code == 400
    assert raised.value.error_code == "invalid_json"


@pytest.mark.parametrize(
    ("raw_body", "error_code"),
    [
        (b'{"status":"success"}', "missing_invoice_id"),
        (b'{"invoiceId":"' + (b"a" * 129) + b'","status":"success"}', "invalid_invoice_id"),
        (b'{"invoiceId":"p2_demo","status":"settled"}', "invalid_status"),
    ],
)
def test_parse_monobank_webhook_payload_rejects_invalid_invoice_or_status(
    raw_body: bytes,
    error_code: str,
) -> None:
    with pytest.raises(BillingWebhookPayloadError) as raised:
        WEBHOOK_ADAPTER.parse_webhook_payload(raw_body)

    assert raised.value.status_code == 400
    assert raised.value.error_code == error_code


def test_provider_payload_parser_raises_payload_error_for_invalid_status() -> None:
    with pytest.raises(BillingWebhookPayloadError) as raised:
        parse_provider_monobank_webhook_payload(b'{"invoiceId":"p2_demo","status":"settled"}')

    assert raised.value.status_code == 400
    assert raised.value.error_code == "invalid_status"


def test_monobank_webhook_verifies_signature_updates_payment_and_writes_audit() -> None:
    db = FakeDatabase()
    signing_key = SigningKey.generate(curve=NIST256p)
    public_key = base64.b64encode(signing_key.verifying_key.to_pem()).decode()
    raw_body = b'{"invoiceId":"p2_demo","status":"success","amount":1000,"ccy":980}'
    service = build_service(db, public_key)
    signature = build_signature(raw_body, signing_key)

    result = service.handle_monobank_webhook(
        raw_body=raw_body,
        headers={
            "X-Sign": signature,
            "X-Token": "secret-token",
            "x-api-key": "secret-api-key",
            "Authorization": "Bearer secret-token",
            "X-Request-ID": "request-42",
        },
        request_url="https://api.example/api/v1/billing/monobank/webhook",
        request_ip="127.0.0.1",
    )

    assert result == {"ok": True, "payment_id": 7, "status": "success"}
    assert db.billing.status_updates[0]["status"] == "success"
    assert db.billing.status_updates[0]["paid_at"] == datetime(2026, 5, 6, 10, 0, tzinfo=UTC)
    assert db.billing.events[0]["event_type"] == "terminal_status"
    assert db.billing.events[0]["source"] == "monobank_webhook"
    assert db.billing.events[1]["event_type"] == "subscription_activated"
    assert db.billing.applied_purchases[0]["payment"]["period_months"] == 1
    audit = db.billing.audit_rows[0]
    assert audit["direction"] == "incoming"
    assert audit["provider_mode"] == "test"
    assert audit["payment_id"] == 7
    assert audit["signature_valid"] is True
    assert audit["response_status_code"] == 200
    assert audit["request_body_json"]["invoiceId"] == "p2_demo"
    assert audit["request_headers_json"]["X-Token"] == "[redacted]"
    assert audit["request_headers_json"]["x-api-key"] == "[redacted]"
    assert audit["request_headers_json"]["Authorization"] == "[redacted]"
    assert audit["request_headers_json"]["X-Request-ID"] == "request-42"
    assert isinstance(audit["duration_ms"], int)
    assert audit["duration_ms"] == 0


def test_monobank_webhook_uses_billing_provider_to_resolve_verified_status() -> None:
    db = FakeDatabase()
    signing_key = SigningKey.generate(curve=NIST256p)
    public_key = base64.b64encode(signing_key.verifying_key.to_pem()).decode()
    raw_body = b'{"invoiceId":"p2_demo","status":"success","amount":1000,"ccy":980}'
    provider = FakeBillingProvider(
        public_key=public_key,
        payload={"invoiceId": "p2_demo", "status": "success", "amount": 1000, "ccy": 980},
        provider_status=BillingProviderPaymentStatus(
            provider_status="provider-declined",
            internal_status="failure",
            failure_code="provider-code",
            failure_reason="provider reason",
        ),
    )
    service = build_service(
        db,
        public_key,
        billing_provider_factory=lambda provider_key, provider_mode: provider,
    )

    result = service.handle_monobank_webhook(
        raw_body=raw_body,
        headers={"X-Sign": build_signature(raw_body, signing_key)},
        request_url="https://api.example/api/v1/billing/monobank/webhook",
        request_ip="127.0.0.1",
    )

    assert result == {"ok": True, "payment_id": 7, "status": "provider-declined"}
    assert provider.status_calls[0]["invoice_id"] == "p2_demo"
    assert provider.resolve_calls == [
        {"invoiceId": "p2_demo", "status": "success", "amount": 1000, "ccy": 980}
    ]
    assert db.billing.status_updates[0]["status"] == "failure"
    assert db.billing.status_updates[0]["failure_code"] == "provider-code"
    assert db.billing.status_updates[0]["failure_reason"] == "provider reason"
    assert db.billing.events[0]["provider_status"] == "provider-declined"


def test_monobank_webhook_uses_monobank_signature_provider_and_custom_status_provider() -> None:
    db = FakeDatabase()
    db.settings.monobank_token_test = ""
    db.settings.monobank_token = ""
    db.billing.payment["provider"] = "custompay"
    db.billing.payment["provider_mode"] = "test"
    signing_key = SigningKey.generate(curve=NIST256p)
    public_key = base64.b64encode(signing_key.verifying_key.to_pem()).decode()
    raw_body = b'{"invoiceId":"p2_demo","status":"success","amount":1000,"ccy":980}'
    factory_calls: list[tuple[str, str]] = []
    monobank_provider = FakeBillingProvider(
        public_key=public_key,
        payload={"invoiceId": "p2_demo", "status": "success", "amount": 1000, "ccy": 980},
        provider_status=BillingProviderPaymentStatus(
            provider_status="success",
            internal_status="success",
            failure_code=None,
            failure_reason=None,
        ),
    )
    custompay_provider = FakeBillingProvider(
        public_key="unused",
        payload={
            "invoiceId": "p2_demo",
            "status": "failure",
            "failureReason": "declined",
            "amount": 1000,
            "ccy": 980,
        },
        provider_status=BillingProviderPaymentStatus(
            provider_status="provider-declined",
            internal_status="failure",
            failure_code="provider-code",
            failure_reason="provider reason",
        ),
    )

    def billing_provider_factory(provider_key: str, provider_mode: str) -> FakeBillingProvider:
        factory_calls.append((provider_key, provider_mode))
        if provider_key == "monobank":
            return monobank_provider
        if provider_key == "custompay":
            return custompay_provider
        raise AssertionError(f"unexpected provider key: {provider_key}")

    service = build_service(
        db,
        public_key,
        billing_provider_factory=billing_provider_factory,
    )

    result = service.handle_monobank_webhook(
        raw_body=raw_body,
        headers={"X-Sign": build_signature(raw_body, signing_key)},
        request_url="https://api.example/api/v1/billing/monobank/webhook",
        request_ip="127.0.0.1",
    )

    assert result == {"ok": True, "payment_id": 7, "status": "provider-declined"}
    assert factory_calls == [
        ("monobank", "test"),
        ("custompay", "test"),
    ]
    assert len(monobank_provider.public_key_calls) == 1
    assert monobank_provider.status_calls == []
    assert custompay_provider.status_calls[0]["invoice_id"] == "p2_demo"
    assert custompay_provider.resolve_calls == [
        {
            "invoiceId": "p2_demo",
            "status": "failure",
            "failureReason": "declined",
            "amount": 1000,
            "ccy": 980,
        }
    ]
    assert db.billing.status_updates[0]["status"] == "failure"
    assert db.billing.status_updates[0]["failure_code"] == "provider-code"
    assert db.billing.status_updates[0]["failure_reason"] == "provider reason"
    assert db.billing.events[0]["provider_status"] == "provider-declined"


def test_monobank_webhook_delegates_payload_and_signature_flow_to_adapter() -> None:
    db = FakeDatabase()
    db.billing.payment["provider"] = "custompay"
    db.billing.payment["provider_mode"] = "test"
    raw_body = b'{"invoiceId":"p2_demo","status":"success","amount":1000,"ccy":980}'
    provider = FakeBillingProvider(
        public_key="unused",
        payload={"invoiceId": "p2_demo", "status": "success", "amount": 1000, "ccy": 980},
        provider_status=BillingProviderPaymentStatus(
            provider_status="success",
            internal_status="success",
            failure_code=None,
            failure_reason=None,
        ),
    )
    adapter = FakeMonobankWebhookAdapter(
        webhook_payload=BillingProviderWebhookPayload(
            invoice_id="p2_demo",
            provider_status="processing",
            payload={"invoiceId": "p2_demo", "status": "processing"},
        )
    )
    factory_calls: list[tuple[str, str]] = []

    def billing_provider_factory(provider_key: str, provider_mode: str) -> FakeBillingProvider:
        factory_calls.append((provider_key, provider_mode))
        return provider

    service = build_service(
        db,
        "unused",
        billing_provider_factory=billing_provider_factory,
        monobank_webhook_adapter=adapter,
    )

    result = service.handle_monobank_webhook(
        raw_body=raw_body,
        headers={"X-Sign": "adapter-signature"},
        request_url="https://api.example/api/v1/billing/monobank/webhook",
        request_ip="127.0.0.1",
    )

    assert result == {"ok": True, "payment_id": 7, "status": "success"}
    assert adapter.parse_calls == [raw_body]
    assert adapter.verify_calls == [
        {
            "provider_mode": "test",
            "signature_base64": "adapter-signature",
            "raw_body": raw_body,
        }
    ]
    assert factory_calls == [
        ("custompay", "test"),
        ("custompay", "test"),
    ]


@pytest.mark.parametrize("provider_case", ["missing_provider", "blank_provider"])
def test_monobank_webhook_uses_instant_runtime_fallback_for_blank_payment_provider(
    provider_case: str,
) -> None:
    db = FakeDatabase()
    if provider_case == "missing_provider":
        db.billing.payment.pop("provider", None)
    else:
        db.billing.payment["provider"] = ""
    db.billing.payment["provider_mode"] = "test"
    signing_key = SigningKey.generate(curve=NIST256p)
    public_key = base64.b64encode(signing_key.verifying_key.to_pem()).decode()
    raw_body = b'{"invoiceId":"p2_demo","status":"success","amount":1000,"ccy":980}'
    factory_calls: list[tuple[str, str]] = []
    signature_provider = FakeBillingProvider(
        public_key=public_key,
        payload={"invoiceId": "p2_demo", "status": "success", "amount": 1000, "ccy": 980},
        provider_status=BillingProviderPaymentStatus(
            provider_status="success",
            internal_status="success",
            failure_code=None,
            failure_reason=None,
        ),
    )
    verified_status_provider = FakeBillingProvider(
        public_key="unused",
        payload={"invoiceId": "p2_demo", "status": "failure", "failureReason": "declined"},
        provider_status=BillingProviderPaymentStatus(
            provider_status="provider-declined",
            internal_status="failure",
            failure_code="provider-code",
            failure_reason="provider reason",
        ),
    )

    def billing_provider_factory(provider_key: str, provider_mode: str) -> FakeBillingProvider:
        factory_calls.append((provider_key, provider_mode))
        if len(factory_calls) == 1:
            return signature_provider
        return verified_status_provider

    service = build_service(
        db,
        public_key,
        billing_provider_factory=billing_provider_factory,
    )

    result = service.handle_monobank_webhook(
        raw_body=raw_body,
        headers={"X-Sign": build_signature(raw_body, signing_key)},
        request_url="https://api.example/api/v1/billing/monobank/webhook",
        request_ip="127.0.0.1",
    )

    assert result == {"ok": True, "payment_id": 7, "status": "provider-declined"}
    assert factory_calls == [
        ("monobank", "test"),
        ("instant", "test"),
    ]
    assert len(signature_provider.public_key_calls) == 1
    assert signature_provider.status_calls == []
    assert verified_status_provider.status_calls[0]["invoice_id"] == "p2_demo"
    assert db.billing.status_updates[0]["status"] == "failure"


def test_monobank_webhook_does_not_apply_status_when_status_verification_fails() -> None:
    db = FakeDatabase()
    signing_key = SigningKey.generate(curve=NIST256p)
    public_key = base64.b64encode(signing_key.verifying_key.to_pem()).decode()
    raw_body = b'{"invoiceId":"p2_demo","status":"success","amount":1000,"ccy":980}'
    service = build_service(db, public_key, status_error=RuntimeError("mono unavailable"))

    with pytest.raises(MonobankWebhookError) as raised:
        service.handle_monobank_webhook(
            raw_body=raw_body,
            headers={"X-Sign": build_signature(raw_body, signing_key)},
            request_url="https://api.example/api/v1/billing/monobank/webhook",
            request_ip="127.0.0.1",
        )

    assert raised.value.status_code == 502
    assert db.billing.status_updates == []
    assert db.billing.applied_purchases == []
    assert db.billing.events[0]["event_type"] == "webhook_status_verification_error"
    audit = db.billing.audit_rows[0]
    assert audit["signature_valid"] is True
    assert audit["processing_result"] == "status_verification_failed"
    assert audit["response_status_code"] == 502


def test_monobank_webhook_rejects_invalid_signature_and_still_writes_audit() -> None:
    db = FakeDatabase()
    signing_key = SigningKey.generate(curve=NIST256p)
    other_key = SigningKey.generate(curve=NIST256p)
    public_key = base64.b64encode(signing_key.verifying_key.to_pem()).decode()
    raw_body = b'{"invoiceId":"p2_demo","status":"failure","failureReason":"declined"}'
    service = build_service(db, public_key)

    with pytest.raises(MonobankWebhookError) as raised:
        service.handle_monobank_webhook(
            raw_body=raw_body,
            headers={"X-Sign": build_signature(raw_body, other_key)},
            request_url="https://api.example/api/v1/billing/monobank/webhook",
            request_ip="127.0.0.1",
        )

    assert raised.value.status_code == 400
    assert db.billing.status_updates == []
    audit = db.billing.audit_rows[0]
    assert audit["signature_valid"] is False
    assert audit["processing_result"] == "invalid_signature"
    assert audit["response_status_code"] == 400


def test_monobank_webhook_refreshes_public_key_cache_when_signature_fails_first_check() -> None:
    db = FakeDatabase()
    stale_signing_key = SigningKey.generate(curve=NIST256p)
    signing_key = SigningKey.generate(curve=NIST256p)
    stale_public_key = base64.b64encode(stale_signing_key.verifying_key.to_pem()).decode()
    public_key = base64.b64encode(signing_key.verifying_key.to_pem()).decode()
    raw_body = b'{"invoiceId":"p2_demo","status":"success","amount":1000,"ccy":980}'
    service = build_service(db, public_key)
    BillingWebhookService._public_key_cache["test"] = stale_public_key

    result = service.handle_monobank_webhook(
        raw_body=raw_body,
        headers={"X-Sign": build_signature(raw_body, signing_key)},
        request_url="https://api.example/api/v1/billing/monobank/webhook",
        request_ip="127.0.0.1",
    )

    assert result == {"ok": True, "payment_id": 7, "status": "success"}
    assert db.billing.audit_rows[0]["signature_valid"] is True


def test_monobank_webhook_rejects_unknown_invoice_with_unknown_mode_audit() -> None:
    db = FakeDatabase()
    signing_key = SigningKey.generate(curve=NIST256p)
    public_key = base64.b64encode(signing_key.verifying_key.to_pem()).decode()
    raw_body = b'{"invoiceId":"p2_unknown","status":"processing"}'
    service = build_service(db, public_key)

    with pytest.raises(MonobankWebhookError) as raised:
        service.handle_monobank_webhook(
            raw_body=raw_body,
            headers={"X-Sign": build_signature(raw_body, signing_key)},
            request_url="https://api.example/api/v1/billing/monobank/webhook",
            request_ip="127.0.0.1",
        )

    assert raised.value.status_code == 404
    audit = db.billing.audit_rows[0]
    assert audit["provider_mode"] == "test"
    assert audit["payment_id"] is None
    assert audit["processing_result"] == "payment_not_found"


def test_monobank_webhook_rejects_invalid_body_before_signature_lookup() -> None:
    db = FakeDatabase()
    service = build_service(db, "unused")

    with pytest.raises(MonobankWebhookError) as raised:
        service.handle_monobank_webhook(
            raw_body=b"not-json",
            headers={},
            request_url="https://api.example/api/v1/billing/monobank/webhook",
            request_ip="127.0.0.1",
        )

    assert raised.value.status_code == 400
    assert raised.value.error_code == "invalid_json"
    assert raised.value.message == "Webhook body must be a JSON object"
    audit = db.billing.audit_rows[0]
    assert audit["provider_mode"] == "unknown"
    assert audit["processing_result"] == "invalid_json"
    assert audit["response_status_code"] == 400
    assert audit["request_raw_body"] == "not-json"
