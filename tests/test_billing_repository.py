from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import UUID

from app.billing.helpers.client_payments import build_public_payment_failure_message
from app.data_access.billing import (
    BillingRepository,
    billing_receipt_has_deliverable_artifact,
    jsonb_safe_value,
    normalize_receipt_ids,
    sanitize_client_payment,
    sanitize_client_receipt,
)
from app.models import UserSubscription
from app.models.billing import BillingPayment, BillingReceipt, BillingSubscriptionPurchase

USER_UUID = UUID("00000000-0000-0000-0000-000000000042")


class FakeSession:
    def __init__(self, *, row_by_key=None) -> None:
        self.added = []
        self.row_by_key = row_by_key or {}

    def add(self, row) -> None:
        self.added.append(row)

    def get(self, model, key):
        return self.row_by_key.get((model, key))

    def flush(self) -> None:
        return None


class FakeSubscriptionPurchaseSession(FakeSession):
    def __init__(self) -> None:
        super().__init__()
        self.scalar_calls = 0

    def scalar(self, _statement):
        self.scalar_calls += 1
        if self.scalar_calls == 1:
            return None
        if self.scalar_calls == 2:
            return None
        if self.scalar_calls == 3:
            return next((row for row in self.added if isinstance(row, BillingSubscriptionPurchase)), None)
        raise AssertionError(f"Unexpected scalar call: {self.scalar_calls}")

    def add(self, row) -> None:
        if isinstance(row, BillingSubscriptionPurchase):
            row.id = len([item for item in self.added if isinstance(item, BillingSubscriptionPurchase)]) + 1
        self.added.append(row)
        if isinstance(row, UserSubscription):
            self.row_by_key[(UserSubscription, row.user_uuid)] = row


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def test_create_monobank_audit_log_persists_full_payload() -> None:
    session = FakeSession()
    repository = BillingRepository(FakeSessionManager(session))
    current_time = datetime(2026, 5, 6, 10, 0, tzinfo=UTC)

    payload = repository.create_monobank_audit_log(
        direction="incoming",
        provider_mode="test",
        source_place="webhook",
        actor_user_uuid=USER_UUID,
        telegram_user_id=42,
        payment_id=7,
        order_reference="order-7",
        invoice_id="p2_demo",
        request_method="POST",
        request_url="/api/v1/billing/monobank/webhook",
        request_ip="127.0.0.1",
        request_headers_json={"X-Sign": "signature"},
        request_body_json={"status": "success"},
        response_status_code=200,
        response_body_json={"ok": True},
        signature_valid=True,
        processing_result="accepted",
        started=current_time,
        finished=current_time,
        duration_ms=0,
    )

    assert len(session.added) == 1
    assert session.added[0].invoice_id == "p2_demo"
    assert session.added[0].actor_user_uuid == USER_UUID
    assert session.added[0].request_body_json == {"status": "success"}
    assert payload["signature_valid"] is True
    assert payload["processing_result"] == "accepted"


def test_create_payment_event_normalizes_datetime_payload_for_jsonb() -> None:
    session = FakeSession()
    repository = BillingRepository(FakeSessionManager(session))
    current_time = datetime(2026, 5, 6, 10, 0, tzinfo=UTC)

    payload = repository.create_payment_event(
        payment_id=7,
        event_type="subscription_activated",
        source="test",
        provider_status="success",
        payload_json={
            "subscription": {
                "user_uuid": USER_UUID,
                "start": current_time,
                "end": current_time,
            }
        },
        current_time=current_time,
    )

    assert len(session.added) == 1
    assert session.added[0].payload_json == {
        "subscription": {
            "user_uuid": str(USER_UUID),
            "start": "2026-05-06T10:00:00+00:00",
            "end": "2026-05-06T10:00:00+00:00",
        }
    }
    assert payload["payload_json"] == session.added[0].payload_json


def test_jsonb_safe_value_normalizes_nested_dates_and_tuples() -> None:
    current_time = datetime(2026, 5, 6, 10, 0, tzinfo=UTC)

    assert jsonb_safe_value({"items": (USER_UUID, current_time)}) == {
        "items": [str(USER_UUID), "2026-05-06T10:00:00+00:00"]
    }


def test_billing_receipt_deliverable_artifact_requires_valid_base64_or_tax_url() -> None:
    invalid_file = BillingReceipt(
        payment_id=7,
        receipt_type="receipt",
        status="done",
        file_base64="not-base64",
        payload_json={},
    )
    valid_file = BillingReceipt(
        payment_id=7,
        receipt_type="receipt",
        status="done",
        file_base64="JVBERi0xLjQK",
        payload_json={},
    )
    tax_url = BillingReceipt(
        payment_id=7,
        receipt_type="fiscal_check",
        status="done",
        tax_url="https://cabinet.tax.gov.ua/check/1",
        file_base64="not-base64",
        payload_json={},
    )

    assert not billing_receipt_has_deliverable_artifact(invalid_file)
    assert billing_receipt_has_deliverable_artifact(valid_file)
    assert billing_receipt_has_deliverable_artifact(tax_url)


def test_sanitize_client_receipt_exposes_only_deliverable_artifacts() -> None:
    timestamp = datetime(2026, 5, 6, 10, 0, tzinfo=UTC)

    invalid_file = sanitize_client_receipt(
        {
            "id": 1,
            "receipt_type": "receipt",
            "status": "done",
            "provider_check_id": None,
            "fiscalization_source": None,
            "tax_url": None,
            "file_base64": "not-base64",
            "created": timestamp,
            "updated": timestamp,
        }
    )
    unavailable_tax_url = sanitize_client_receipt(
        {
            "id": 2,
            "receipt_type": "fiscal_check",
            "status": "unavailable",
            "provider_check_id": None,
            "fiscalization_source": None,
            "tax_url": "https://cabinet.tax.gov.ua/check/2",
            "file_base64": None,
            "created": timestamp,
            "updated": timestamp,
        }
    )
    valid_file = sanitize_client_receipt(
        {
            "id": 3,
            "receipt_type": "receipt",
            "status": "done",
            "provider_check_id": None,
            "fiscalization_source": None,
            "tax_url": None,
            "file_base64": "JVBERi0xLjQK",
            "created": timestamp,
            "updated": timestamp,
        }
    )
    pending_checkbox_check = sanitize_client_receipt(
        {
            "id": 4,
            "receipt_type": "fiscal_check",
            "status": "new",
            "provider_check_id": "55a1d9f7-7475-4088-86d2-2132c2261e71",
            "fiscalization_source": "checkbox",
            "tax_url": None,
            "file_base64": None,
            "created": timestamp,
            "updated": timestamp,
        }
    )
    done_checkbox_check_with_tax_cabinet_url = sanitize_client_receipt(
        {
            "id": 6,
            "receipt_type": "fiscal_check",
            "status": "done",
            "provider_check_id": "55a1d9f7-7475-4088-86d2-2132c2261e71",
            "fiscalization_source": "checkbox",
            "tax_url": "https://cabinet.tax.gov.ua/cashregs/check?id=long",
            "file_base64": None,
            "created": timestamp,
            "updated": timestamp,
        }
    )
    pending_checkbox_without_provider_id = sanitize_client_receipt(
        {
            "id": 5,
            "receipt_type": "fiscal_check",
            "status": "new",
            "provider_check_id": None,
            "fiscalization_source": "checkbox",
            "tax_url": None,
            "file_base64": None,
            "created": timestamp,
            "updated": timestamp,
        }
    )

    assert invalid_file["has_file"] is False
    assert invalid_file["tax_url"] is None
    assert "provider_check_id" not in invalid_file
    assert "fiscalization_source" not in invalid_file
    assert unavailable_tax_url["tax_url"] is None
    assert valid_file["has_file"] is True
    assert pending_checkbox_check["tax_url"] == (
        "https://check.checkbox.ua/55a1d9f7-7475-4088-86d2-2132c2261e71"
    )
    assert done_checkbox_check_with_tax_cabinet_url["tax_url"] == (
        "https://check.checkbox.ua/55a1d9f7-7475-4088-86d2-2132c2261e71"
    )
    assert pending_checkbox_without_provider_id["tax_url"] is None
    assert "provider_check_id" not in pending_checkbox_check
    assert "fiscalization_source" not in pending_checkbox_check


def test_normalize_receipt_ids_ignores_malformed_values() -> None:
    assert normalize_receipt_ids([2, "1", "bad", None, 2, -1, 0]) == [1, 2]
    assert normalize_receipt_ids({"not": "a list"}) == []


def test_build_public_payment_failure_message_hides_raw_internals() -> None:
    assert build_public_payment_failure_message("success", "declined") is None
    assert build_public_payment_failure_message("failure", "declined by bank") == "declined by bank"
    assert build_public_payment_failure_message("expired", "raw provider text") == "Payment expired"
    assert build_public_payment_failure_message("reversed", "raw provider text") == "Payment was reversed"


def test_sanitize_client_payment_omits_provider_fields_and_raw_failure_reason() -> None:
    timestamp = datetime(2026, 5, 6, 10, 0, tzinfo=UTC)
    payment = BillingPayment(
        id=7,
        user_uuid=USER_UUID,
        telegram_user_id=42,
        plan_key="premium",
        period_months=1,
        amount_minor=1000,
        currency=980,
        status="failure",
        provider_reference="clx-secret-reference",
        provider_invoice_id="invoice-secret",
        provider_mode="test",
        checkout_url="https://pay.example/secret",
        failure_reason="declined",
        provider_status_json={"raw": True},
        created=timestamp,
        updated=timestamp,
    )

    payload = sanitize_client_payment(payment, receipts=[])

    assert payload["amount_uah"] == 10
    assert payload["failure_message"] == "declined"
    assert "failure_reason" not in payload
    assert "provider_reference" not in payload
    assert "provider_invoice_id" not in payload
    assert "provider_mode" not in payload
    assert "checkout_url" not in payload
    assert "provider_status_json" not in payload

    payment.amount_minor = 1055
    payload = sanitize_client_payment(payment, receipts=[])

    assert payload["amount_uah"] == 10.55


def test_sanitize_client_payment_exposes_promotion_label_and_granted_period() -> None:
    timestamp = datetime(2026, 5, 6, 10, 0, tzinfo=UTC)
    payment = BillingPayment(
        id=7,
        user_uuid=USER_UUID,
        telegram_user_id=42,
        plan_key="premium",
        period_months=3,
        amount_minor=3000,
        currency=980,
        status="success",
        provider_reference="clx-secret-reference",
        provider_invoice_id="invoice-secret",
        provider_mode="test",
        failure_reason=None,
        provider_status_json={
            "checkout_quote": {
                "period_months": 3,
                "granted_period_months": 6,
                "promotion": {"label": "Двойное время за поддержку проекта"},
            }
        },
        created=timestamp,
        updated=timestamp,
    )

    payload = sanitize_client_payment(payment, receipts=[])

    assert payload["period_months"] == 3
    assert payload["granted_period_months"] == 6
    assert payload["promotion_label"] == "Двойное время за поддержку проекта"


def test_apply_subscription_purchase_uses_checkout_granted_period_months() -> None:
    session = FakeSubscriptionPurchaseSession()
    repository = BillingRepository(FakeSessionManager(session))
    current_time = datetime(2026, 5, 6, 10, 0, tzinfo=UTC)

    payload = repository.apply_subscription_purchase_for_payment(
        {
            "id": 7,
            "user_uuid": str(USER_UUID),
            "telegram_user_id": 42,
            "plan_key": "premium",
            "period_months": 3,
            "amount_minor": 3000,
            "currency": 980,
            "provider_reference": "clx-order-7",
            "provider_invoice_id": "p2_demo",
            "provider_status_json": {
                "checkout_quote": {
                    "kind": "subscription",
                    "period_months": 3,
                    "granted_period_months": 6,
                    "promotion": {"label": "Двойное время за поддержку проекта"},
                }
            },
            "paid_at": current_time,
        },
        current_time=current_time,
    )

    purchase = payload["purchase"]
    assert purchase["period_months"] == 3
    assert purchase["period_start"] == current_time
    assert purchase["period_end"].month == 11
    assert purchase["metadata_json"]["granted_period_months"] == 6
    assert payload["subscription"]["end"] == purchase["period_end"]


def test_mark_receipt_delivery_sent_rejects_invalid_artifact() -> None:
    receipt = BillingReceipt(
        id=3,
        payment_id=7,
        receipt_type="receipt",
        status="done",
        file_base64="not-base64",
        payload_json={},
        bot_delivery_status="claimed",
    )
    repository = BillingRepository(FakeSessionManager(FakeSession(row_by_key={(BillingReceipt, 3): receipt})))

    repository.mark_receipt_delivery_sent(3, current_time=datetime(2026, 5, 6, 10, 0, tzinfo=UTC))

    assert receipt.status == "unavailable"
    assert receipt.bot_delivery_status is None
    assert receipt.bot_delivery_error == "Receipt artifact is not deliverable"
