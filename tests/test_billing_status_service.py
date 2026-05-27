from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.billing.runtime_settings import (
    BILLING_RUNTIME_SETTINGS_KEY,
    DEFAULT_BILLING_RUNTIME_SETTINGS,
)
from app.billing.services.monobank_receipt_artifacts import (
    monobank_fiscal_checks_fetch_result,
)
from app.billing.services.provider_port import BillingProviderPaymentStatus
from app.billing.services.status_service import (
    BillingPaymentStatusConfigurationError,
    BillingPaymentStatusNotFoundError,
    BillingPaymentStatusService,
)
from app.domain.billing.monobank_statuses import monobank_payment_status_from_payload

USER_UUID = "11111111-1111-4111-8111-111111111111"
OTHER_USER_UUID = "22222222-2222-4222-8222-222222222222"


class FakeTimeService:
    def __init__(self) -> None:
        self.current_time = datetime(2026, 5, 6, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current_time


class FakeBillingRepository:
    def __init__(self, payment: dict[str, object]) -> None:
        self.payment = dict(payment)
        self.status_updates: list[dict[str, object]] = []
        self.events: list[dict[str, object]] = []
        self.applied_purchases: list[dict[str, object]] = []
        self.reversed_purchases: list[dict[str, object]] = []
        self.receipts: list[dict[str, object]] = []

    def get_payment_by_id(self, payment_id: int):
        if payment_id == self.payment["id"]:
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
        return {"id": 1, **kwargs}

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
        self.reversed_purchases.append({"payment_id": payment_id, "current_time": current_time})
        return {
            "purchase": {"payment_id": payment_id, "status": "reversed"},
            "subscription": {
                "user_uuid": USER_UUID,
                "plan_key": "free",
                "start": current_time,
                "end": None,
            },
        }


class FakeMissingPurchaseBillingRepository(FakeBillingRepository):
    def reverse_subscription_purchase_projection_for_payment(self, payment_id: int, *, current_time: datetime):
        self.reversed_purchases.append({"payment_id": payment_id, "current_time": current_time})
        return None


class FakeBrokenStatusApplyBillingRepository(FakeBillingRepository):
    def update_payment_provider_status(self, payment_id: int, **kwargs):
        raise RuntimeError("local billing write failed")


class FakeProfiles:
    def get_profile(self, telegram_user_id: int):
        if telegram_user_id != 42:
            return None
        return {"telegram_user_id": 42, "user_uuid": USER_UUID}


class FakeSubscriptions:
    def __init__(self) -> None:
        self.activations: list[dict[str, object]] = []
        self.revocations: list[dict[str, object]] = []
        self.rows: dict[str, dict[str, object]] = {}

    def get_by_user_uuid(self, user_uuid: str):
        return self.rows.get(user_uuid)

    def activate_paid_plan_for_user(self, user_uuid: str, **kwargs):
        payload = {"user_uuid": user_uuid, **kwargs}
        self.activations.append(payload)
        return {
            "user_uuid": user_uuid,
            "plan_key": kwargs["plan_key"],
            "start": kwargs["current_time"],
            "end": kwargs["current_time"],
        }

    def revoke_paid_plan_for_user(self, user_uuid: str, **kwargs):
        payload = {"user_uuid": user_uuid, **kwargs}
        self.revocations.append(payload)
        return {
            "user_uuid": user_uuid,
            "plan_key": "free",
            "start": kwargs["current_time"],
            "end": None,
        }


class FakeAppSettings:
    def __init__(self, value: dict[str, object]) -> None:
        self.value = value

    def get_value(self, key: str):
        if key == BILLING_RUNTIME_SETTINGS_KEY:
            return self.value
        return None


class FakeDatabase:
    def __init__(self, payment: dict[str, object], billing_settings: dict[str, object] | None = None) -> None:
        self.settings = SimpleNamespace(monobank_token_test="test-token", monobank_token="production-token")
        self.billing = FakeBillingRepository(payment)
        self.subscriptions = FakeSubscriptions()
        self.user_profiles = FakeProfiles()
        self.app_settings = FakeAppSettings(billing_settings or default_billing_settings())


class FakeMissingPurchaseDatabase(FakeDatabase):
    def __init__(self, payment: dict[str, object], billing_settings: dict[str, object] | None = None) -> None:
        super().__init__(payment, billing_settings)
        self.billing = FakeMissingPurchaseBillingRepository(payment)


class FakeBrokenStatusApplyDatabase(FakeDatabase):
    def __init__(self, payment: dict[str, object], billing_settings: dict[str, object] | None = None) -> None:
        super().__init__(payment, billing_settings)
        self.billing = FakeBrokenStatusApplyBillingRepository(payment)


class FakeMonobankClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[dict[str, object]] = []
        self.fiscal_calls: list[dict[str, object]] = []

    def get_invoice_status(self, invoice_id: str, *, audit_context):
        self.calls.append({"invoice_id": invoice_id, "audit_context": audit_context})
        return dict(self.payload)

    def get_fiscal_checks(self, invoice_id: str, *, audit_context):
        self.fiscal_calls.append({"invoice_id": invoice_id, "audit_context": audit_context})
        return {
            "checks": [
                {
                    "id": "check-1",
                    "status": "done",
                    "taxUrl": "https://cabinet.tax.gov.ua/check/1",
                }
            ]
        }

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


class FailingMonobankClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def get_invoice_status(self, invoice_id: str, *, audit_context):
        self.calls.append({"invoice_id": invoice_id, "audit_context": audit_context})
        raise RuntimeError("mono temporary unavailable")

    def resolve_payment_status(self, payload: dict[str, object]) -> BillingProviderPaymentStatus:
        status = monobank_payment_status_from_payload(payload)
        return BillingProviderPaymentStatus(
            provider_status=status.provider_status,
            internal_status=status.internal_status,
            failure_code=status.failure_code,
            failure_reason=status.failure_reason,
        )


class FakeBillingProvider:
    def __init__(
        self,
        payload: dict[str, object],
        provider_status: BillingProviderPaymentStatus,
    ) -> None:
        self.payload = payload
        self.provider_status = provider_status
        self.calls: list[dict[str, object]] = []
        self.resolve_calls: list[dict[str, object]] = []

    def get_invoice_status(self, invoice_id: str, *, audit_context):
        self.calls.append({"invoice_id": invoice_id, "audit_context": audit_context})
        return dict(self.payload)

    def resolve_payment_status(self, payload: dict[str, object]) -> BillingProviderPaymentStatus:
        self.resolve_calls.append(dict(payload))
        return self.provider_status

    def get_fiscal_checks(self, invoice_id: str, *, audit_context):
        return {"checks": []}


def default_billing_settings(**overrides) -> dict[str, object]:
    value = {
        **DEFAULT_BILLING_RUNTIME_SETTINGS,
        "monobank_mode": "test",
        "offer_text": "CronoLex paid subscription offer text for tests.",
    }
    value.update(overrides)
    return value


def make_payment(**overrides) -> dict[str, object]:
    value = {
        "id": 7,
        "user_uuid": USER_UUID,
        "telegram_user_id": 42,
        "plan_key": "premium",
        "period_months": 1,
        "amount_minor": 1000,
        "currency": 980,
        "status": "invoice_created",
        "provider": "monobank",
        "provider_mode": "test",
        "provider_invoice_id": "p2_demo",
        "provider_reference": "clx-order-7",
        "return_url": "https://web.example/plans",
        "source_path": "/learning",
        "failure_reason": None,
        "created": datetime(2026, 5, 6, 11, 59, 30, tzinfo=UTC),
        "paid_at": None,
    }
    value.update(overrides)
    return value


def test_client_status_polls_after_webhook_wait_and_applies_success() -> None:
    db = FakeDatabase(make_payment())
    monobank_client = FakeMonobankClient({"invoiceId": "p2_demo", "status": "success", "amount": 1000, "ccy": 980})
    service = BillingPaymentStatusService(
        db,
        FakeTimeService(),
        billing_provider_factory=lambda provider_key, provider_mode: monobank_client,
    )

    payload = service.get_client_payment_status(
        {"telegram_user_id": 42},
        payment_id=7,
        request_ip="127.0.0.1",
    )

    assert payload["payment"]["status"] == "success"
    assert "provider_invoice_id" not in payload["payment"]
    assert "provider_reference" not in payload["payment"]
    assert "provider_mode" not in payload["payment"]
    assert "checkout_url" not in payload["payment"]
    assert "failure_reason" not in payload["status"]
    assert payload["status"]["is_success"] is True
    assert payload["polling"]["attempted"] is True
    assert db.billing.status_updates[0]["status"] == "success"
    assert db.billing.events[0]["source"] == "client_status_polling"
    assert db.billing.applied_purchases[0]["payment"]["id"] == 7
    assert db.subscriptions.activations == []
    assert monobank_client.calls[0]["invoice_id"] == "p2_demo"


def test_client_status_uses_billing_provider_to_resolve_status() -> None:
    db = FakeDatabase(make_payment(provider="custom_provider"))
    db.settings.monobank_token_test = ""
    db.settings.monobank_token = ""
    provider = FakeBillingProvider(
        {"invoiceId": "p2_demo", "status": "not-a-monobank-status"},
        BillingProviderPaymentStatus(
            provider_status="provider-processing",
            internal_status="processing",
        ),
    )
    provider_factory_calls: list[dict[str, str]] = []

    def provider_factory(provider_key: str, provider_mode: str) -> FakeBillingProvider:
        provider_factory_calls.append(
            {"provider_key": provider_key, "provider_mode": provider_mode}
        )
        return provider

    service = BillingPaymentStatusService(
        db,
        FakeTimeService(),
        billing_provider_factory=provider_factory,
    )

    payload = service.get_client_payment_status(
        {"telegram_user_id": 42},
        payment_id=7,
        request_ip="127.0.0.1",
    )

    assert payload["payment"]["status"] == "processing"
    assert provider_factory_calls == [
        {"provider_key": "custom_provider", "provider_mode": "test"}
    ]
    assert provider.calls[0]["invoice_id"] == "p2_demo"
    assert provider.resolve_calls == [{"invoiceId": "p2_demo", "status": "not-a-monobank-status"}]
    assert db.billing.status_updates[0]["status"] == "processing"
    assert db.billing.events[0]["provider_status"] == "provider-processing"


def test_client_status_queues_post_upgrade_rescan_when_payment_unlocks_ai_import() -> None:
    db = FakeDatabase(make_payment())
    rescan_calls: list[dict[str, object]] = []
    monobank_client = FakeMonobankClient({"invoiceId": "p2_demo", "status": "success", "amount": 1000, "ccy": 980})
    service = BillingPaymentStatusService(
        db,
        FakeTimeService(),
        billing_provider_factory=lambda provider_key, provider_mode: monobank_client,
        post_upgrade_rescan=lambda **kwargs: rescan_calls.append(dict(kwargs)) or {"status": "queued", "task_log_id": 10},
    )

    service.get_client_payment_status(
        {"telegram_user_id": 42},
        payment_id=7,
        request_ip="127.0.0.1",
    )

    assert rescan_calls == [
        {
            "telegram_user_id": 42,
            "user_uuid": USER_UUID,
            "current_time": datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
        }
    ]
    assert db.billing.events[2]["event_type"] == "post_upgrade_google_doc_rescan_queued"
    assert db.billing.events[2]["payload_json"] == {"status": "queued", "task_log_id": 10}


def test_client_status_queues_rescan_for_successful_paid_activation_even_when_plan_was_already_paid() -> None:
    db = FakeDatabase(make_payment())
    db.subscriptions.rows[USER_UUID] = {
        "user_uuid": USER_UUID,
        "plan_key": "premium",
        "start": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        "end": datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
    }
    rescan_calls: list[dict[str, object]] = []
    monobank_client = FakeMonobankClient({"invoiceId": "p2_demo", "status": "success", "amount": 1000, "ccy": 980})
    service = BillingPaymentStatusService(
        db,
        FakeTimeService(),
        billing_provider_factory=lambda provider_key, provider_mode: monobank_client,
        post_upgrade_rescan=lambda **kwargs: rescan_calls.append(dict(kwargs)) or {"status": "queued", "task_log_id": 10},
    )

    service.get_client_payment_status(
        {"telegram_user_id": 42},
        payment_id=7,
        request_ip="127.0.0.1",
    )

    assert rescan_calls[0]["telegram_user_id"] == 42
    assert db.billing.events[2]["event_type"] == "post_upgrade_google_doc_rescan_queued"


def test_client_status_logs_rescan_queue_failure_without_breaking_payment_success() -> None:
    db = FakeDatabase(make_payment())
    monobank_client = FakeMonobankClient({"invoiceId": "p2_demo", "status": "success", "amount": 1000, "ccy": 980})

    def fail_rescan(**kwargs: object) -> dict[str, object]:
        raise RuntimeError("queue unavailable")

    service = BillingPaymentStatusService(
        db,
        FakeTimeService(),
        billing_provider_factory=lambda provider_key, provider_mode: monobank_client,
        post_upgrade_rescan=fail_rescan,
    )

    payload = service.get_client_payment_status(
        {"telegram_user_id": 42},
        payment_id=7,
        request_ip="127.0.0.1",
    )

    assert payload["payment"]["status"] == "success"
    assert db.billing.events[2]["event_type"] == "post_upgrade_google_doc_rescan_queue_failed"
    assert db.billing.events[2]["payload_json"] == {
        "error_type": "RuntimeError",
        "error_text": "queue unavailable",
    }


def test_client_status_fetches_fiscal_check_after_production_success() -> None:
    db = FakeDatabase(make_payment(provider_mode="production"))
    monobank_client = FakeMonobankClient({"invoiceId": "p2_demo", "status": "success", "amount": 1000, "ccy": 980})
    service = BillingPaymentStatusService(
        db,
        FakeTimeService(),
        billing_provider_factory=lambda provider_key, provider_mode: monobank_client,
    )

    service.get_client_payment_status(
        {"telegram_user_id": 42},
        payment_id=7,
        request_ip="127.0.0.1",
    )

    assert monobank_client.fiscal_calls[0]["invoice_id"] == "p2_demo"
    assert monobank_client.fiscal_calls[0]["audit_context"].source_place == "client_status_fiscal_check"
    assert db.billing.receipts[0]["receipt_type"] == "fiscal_check"


def test_client_status_preserves_fractional_hryvnia_order_amount() -> None:
    db = FakeDatabase(make_payment(amount_minor=1055))
    service = BillingPaymentStatusService(db, FakeTimeService())

    payload = service.get_client_payment_status(
        {"telegram_user_id": 42},
        payment_id=7,
        request_ip=None,
    )

    assert payload["order"]["amount_uah"] == 10.55


def test_client_status_waits_for_webhook_before_polling() -> None:
    db = FakeDatabase(make_payment(created=datetime(2026, 5, 6, 11, 59, 50, tzinfo=UTC)))
    monobank_client = FakeMonobankClient({"invoiceId": "p2_demo", "status": "success"})
    service = BillingPaymentStatusService(
        db,
        FakeTimeService(),
        billing_provider_factory=lambda provider_key, provider_mode: monobank_client,
    )

    payload = service.get_client_payment_status(
        {"telegram_user_id": 42},
        payment_id=7,
        request_ip=None,
    )

    assert payload["payment"]["status"] == "invoice_created"
    assert payload["polling"]["attempted"] is False
    assert monobank_client.calls == []


def test_client_status_keeps_waiting_when_fallback_polling_fails() -> None:
    db = FakeDatabase(make_payment())
    monobank_client = FailingMonobankClient()
    service = BillingPaymentStatusService(
        db,
        FakeTimeService(),
        billing_provider_factory=lambda provider_key, provider_mode: monobank_client,
    )

    payload = service.get_client_payment_status(
        {"telegram_user_id": 42},
        payment_id=7,
        request_ip="127.0.0.1",
    )

    assert payload["payment"]["status"] == "invoice_created"
    assert payload["status"]["is_terminal"] is False
    assert payload["status"]["message"] == "Waiting for payment confirmation"
    assert payload["polling"]["attempted"] is True
    assert payload["polling"]["error"] == {
        "code": "provider_status_temporarily_unavailable",
        "message": "Payment status is temporarily unavailable. CronoLex will keep checking it in the background.",
    }
    assert db.billing.status_updates == []
    assert db.billing.events[0]["event_type"] == "client_status_polling_error"
    assert db.billing.events[0]["payload_json"] == {
        "client_error_code": "provider_status_temporarily_unavailable",
        "error_type": "RuntimeError",
        "error_message": "mono temporary unavailable",
    }
    assert monobank_client.calls[0]["invoice_id"] == "p2_demo"


def test_client_status_does_not_hide_local_status_application_errors() -> None:
    db = FakeBrokenStatusApplyDatabase(make_payment())
    monobank_client = FakeMonobankClient({"invoiceId": "p2_demo", "status": "success"})
    service = BillingPaymentStatusService(
        db,
        FakeTimeService(),
        billing_provider_factory=lambda provider_key, provider_mode: monobank_client,
    )

    with pytest.raises(RuntimeError, match="local billing write failed"):
        service.get_client_payment_status(
            {"telegram_user_id": 42},
            payment_id=7,
            request_ip="127.0.0.1",
        )

    assert db.billing.events == []
    assert monobank_client.calls[0]["invoice_id"] == "p2_demo"


def test_client_status_marks_long_processing_message() -> None:
    db = FakeDatabase(make_payment(created=datetime(2026, 5, 6, 11, 58, 1, tzinfo=UTC)), default_billing_settings(webhook_wait_seconds=120))
    service = BillingPaymentStatusService(db, FakeTimeService())

    payload = service.get_client_payment_status(
        {"telegram_user_id": 42},
        payment_id=7,
        request_ip=None,
    )

    assert payload["polling"]["attempted"] is False
    assert payload["status"]["is_long_processing"] is True
    assert payload["status"]["should_stop_polling"] is True
    assert "Telegram" in payload["status"]["message"]


def test_client_status_uses_timeout_message_when_poll_timeout_is_before_long_processing() -> None:
    db = FakeDatabase(
        make_payment(created=datetime(2026, 5, 6, 11, 59, 40, tzinfo=UTC)),
        default_billing_settings(webhook_wait_seconds=120, frontend_poll_timeout_seconds=10, long_processing_seconds=60),
    )
    service = BillingPaymentStatusService(db, FakeTimeService())

    payload = service.get_client_payment_status(
        {"telegram_user_id": 42},
        payment_id=7,
        request_ip=None,
    )

    assert payload["status"]["is_long_processing"] is False
    assert payload["status"]["should_stop_polling"] is True
    assert "Telegram" in payload["status"]["message"]


def test_apply_provider_reversed_after_success_revokes_subscription_directly() -> None:
    from app.billing.services.payment_status import apply_provider_status_payload

    db = FakeDatabase(make_payment(status="success", paid_at=datetime(2026, 5, 6, 11, 0, tzinfo=UTC)))
    payment = db.billing.get_payment_by_id(7)

    updated = apply_provider_status_payload(
        db,
        FakeTimeService(),
        payment=payment,
        provider_status=BillingProviderPaymentStatus(
            provider_status="provider-reversed",
            internal_status="reversed",
        ),
        payload={"invoice_id": "p2_demo", "status": "provider-reversed"},
        source="test_provider",
    )

    assert updated["status"] == "reversed"
    assert db.billing.reversed_purchases == [{"payment_id": 7, "current_time": datetime(2026, 5, 6, 12, 0, tzinfo=UTC)}]
    assert db.subscriptions.revocations == []
    assert db.billing.events[1]["event_type"] == "subscription_revoked"
    assert db.billing.events[1]["provider_status"] == "provider-reversed"


def test_apply_provider_status_uses_provider_fields_instead_of_payload_keys() -> None:
    from app.billing.services.payment_status import apply_provider_status_payload

    db = FakeDatabase(make_payment())
    payment = db.billing.get_payment_by_id(7)

    updated = apply_provider_status_payload(
        db,
        FakeTimeService(),
        payment=payment,
        provider_status=BillingProviderPaymentStatus(
            provider_status="provider-declined",
            internal_status="failure",
            failure_code="provider-code",
            failure_reason="provider reason",
        ),
        payload={
            "invoiceId": "p2_demo",
            "status": "success",
            "errCode": "payload-code",
            "failureReason": "payload reason",
        },
        source="test_provider",
    )

    assert updated["status"] == "failure"
    assert db.billing.status_updates[0]["status"] == "failure"
    assert db.billing.status_updates[0]["failure_code"] == "provider-code"
    assert db.billing.status_updates[0]["failure_reason"] == "provider reason"
    assert db.billing.events[0]["provider_status"] == "provider-declined"


def test_apply_provider_success_activates_subscription_and_queues_rescan() -> None:
    from app.billing.services.payment_status import apply_provider_status_payload

    db = FakeDatabase(make_payment())
    payment = db.billing.get_payment_by_id(7)
    rescan_calls: list[dict[str, object]] = []

    updated = apply_provider_status_payload(
        db,
        FakeTimeService(),
        payment=payment,
        provider_status=BillingProviderPaymentStatus(
            provider_status="provider-paid",
            internal_status="success",
        ),
        payload={"invoiceId": "p2_demo", "status": "not-a-monobank-status"},
        source="test_provider",
        post_upgrade_rescan=lambda **kwargs: rescan_calls.append(dict(kwargs))
        or {"status": "queued", "task_log_id": 10},
    )

    assert updated["status"] == "success"
    assert db.billing.applied_purchases[0]["payment"]["id"] == 7
    assert db.billing.events[0]["event_type"] == "terminal_status"
    assert db.billing.events[0]["provider_status"] == "provider-paid"
    assert db.billing.events[1]["event_type"] == "subscription_activated"
    assert db.billing.events[2]["event_type"] == "post_upgrade_google_doc_rescan_queued"
    assert db.billing.events[2]["provider_status"] == "provider-paid"
    assert rescan_calls == [
        {
            "telegram_user_id": 42,
            "user_uuid": USER_UUID,
            "current_time": datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
        }
    ]


def test_apply_provider_reversed_after_success_revokes_subscription() -> None:
    from app.billing.services.payment_status import apply_provider_status_payload

    db = FakeDatabase(
        make_payment(status="success", paid_at=datetime(2026, 5, 6, 11, 0, tzinfo=UTC))
    )
    payment = db.billing.get_payment_by_id(7)

    updated = apply_provider_status_payload(
        db,
        FakeTimeService(),
        payment=payment,
        provider_status=BillingProviderPaymentStatus(
            provider_status="provider-reversed",
            internal_status="reversed",
        ),
        payload={"invoiceId": "p2_demo", "status": "success"},
        source="test_provider",
    )

    assert updated["status"] == "reversed"
    assert db.billing.reversed_purchases == [
        {"payment_id": 7, "current_time": datetime(2026, 5, 6, 12, 0, tzinfo=UTC)}
    ]
    assert db.billing.events[1]["event_type"] == "subscription_revoked"
    assert db.billing.events[1]["provider_status"] == "provider-reversed"


def test_apply_provider_reversed_after_success_uses_atomic_purchase_projection_when_available() -> None:
    from app.billing.services.payment_status import apply_provider_status_payload

    db = FakeDatabase(make_payment(status="success", paid_at=datetime(2026, 5, 6, 11, 0, tzinfo=UTC)))
    payment = db.billing.get_payment_by_id(7)

    updated = apply_provider_status_payload(
        db,
        FakeTimeService(),
        payment=payment,
        provider_status=BillingProviderPaymentStatus(
            provider_status="provider-reversed",
            internal_status="reversed",
        ),
        payload={"invoice_id": "p2_demo", "status": "provider-reversed"},
        source="test_provider",
    )

    assert updated["status"] == "reversed"
    assert db.billing.reversed_purchases == [{"payment_id": 7, "current_time": datetime(2026, 5, 6, 12, 0, tzinfo=UTC)}]
    assert db.subscriptions.revocations == []
    assert db.billing.events[1]["event_type"] == "subscription_revoked"
    assert db.billing.events[1]["provider_status"] == "provider-reversed"


def test_apply_provider_stale_processing_after_success_does_not_regress_payment() -> None:
    from app.billing.services.payment_status import apply_provider_status_payload

    db = FakeDatabase(make_payment(status="success", paid_at=datetime(2026, 5, 6, 11, 0, tzinfo=UTC)))
    payment = db.billing.get_payment_by_id(7)

    updated = apply_provider_status_payload(
        db,
        FakeTimeService(),
        payment=payment,
        provider_status=BillingProviderPaymentStatus(
            provider_status="provider-processing",
            internal_status="processing",
        ),
        payload={"invoice_id": "p2_demo", "status": "provider-processing"},
        source="test_provider",
    )

    assert updated["status"] == "success"
    assert db.billing.status_updates == []
    assert db.billing.events[0]["event_type"] == "status_update_ignored"
    assert db.billing.events[0]["provider_status"] == "provider-processing"
    assert db.billing.applied_purchases == []
    assert db.billing.reversed_purchases == []


@pytest.mark.parametrize("previous_status", ["failure", "reversed", "expired"])
def test_apply_provider_success_after_failed_terminal_status_does_not_resurrect_payment(previous_status: str) -> None:
    from app.billing.services.payment_status import apply_provider_status_payload

    db = FakeDatabase(make_payment(status=previous_status, paid_at=datetime(2026, 5, 6, 11, 0, tzinfo=UTC)))
    payment = db.billing.get_payment_by_id(7)

    updated = apply_provider_status_payload(
        db,
        FakeTimeService(),
        payment=payment,
        provider_status=BillingProviderPaymentStatus(
            provider_status="provider-paid",
            internal_status="success",
        ),
        payload={"invoice_id": "p2_demo", "status": "provider-paid"},
        source="test_provider",
    )

    assert updated["status"] == previous_status
    assert db.billing.status_updates == []
    assert db.billing.events[0]["event_type"] == "status_update_ignored"
    assert db.billing.events[0]["provider_status"] == "provider-paid"
    assert db.billing.applied_purchases == []
    assert db.billing.reversed_purchases == []


def test_missing_purchase_revocation_logs_incoming_provider_status() -> None:
    from app.billing.services.payment_status import apply_provider_status_payload

    db = FakeMissingPurchaseDatabase(make_payment(status="success", paid_at=datetime(2026, 5, 6, 11, 0, tzinfo=UTC)))
    payment = db.billing.get_payment_by_id(7)

    updated = apply_provider_status_payload(
        db,
        FakeTimeService(),
        payment=payment,
        provider_status=BillingProviderPaymentStatus(
            provider_status="provider-reversed",
            internal_status="reversed",
        ),
        payload={"invoice_id": "p2_demo", "status": "provider-reversed"},
        source="test_provider",
    )

    assert updated["status"] == "reversed"
    assert db.billing.events[1]["event_type"] == "subscription_revocation_skipped"
    assert db.billing.events[1]["provider_status"] == "provider-reversed"


def test_client_status_rejects_other_user_payment() -> None:
    db = FakeDatabase(make_payment(user_uuid=OTHER_USER_UUID))
    service = BillingPaymentStatusService(db, FakeTimeService())

    with pytest.raises(BillingPaymentStatusNotFoundError) as raised:
        service.get_client_payment_status(
            {"telegram_user_id": 42, "user_uuid": USER_UUID},
            payment_id=7,
            request_ip=None,
        )

    assert raised.value.detail == "Billing payment not found"
    assert not hasattr(raised.value, "status_code")


def test_client_status_raises_non_http_not_found_for_missing_payment() -> None:
    db = FakeDatabase(make_payment())
    service = BillingPaymentStatusService(db, FakeTimeService())

    with pytest.raises(BillingPaymentStatusNotFoundError) as raised:
        service.get_client_payment_status(
            {"telegram_user_id": 42, "user_uuid": USER_UUID},
            payment_id=999,
            request_ip=None,
        )

    assert raised.value.detail == "Billing payment not found"
    assert not hasattr(raised.value, "status_code")


def test_client_status_raises_non_http_not_found_for_missing_profile() -> None:
    db = FakeDatabase(make_payment())
    service = BillingPaymentStatusService(db, FakeTimeService())

    with pytest.raises(BillingPaymentStatusNotFoundError) as raised:
        service.get_client_payment_status(
            {"telegram_user_id": 99},
            payment_id=7,
            request_ip=None,
        )

    assert raised.value.detail == "User profile not found"
    assert not hasattr(raised.value, "status_code")


def test_client_status_raises_non_http_configuration_error_for_invalid_settings() -> None:
    db = FakeDatabase(make_payment(), default_billing_settings(webhook_wait_seconds="slow"))
    service = BillingPaymentStatusService(db, FakeTimeService())

    with pytest.raises(BillingPaymentStatusConfigurationError) as raised:
        service.get_client_payment_status(
            {"telegram_user_id": 42},
            payment_id=7,
            request_ip=None,
        )

    assert "webhook_wait_seconds" in raised.value.detail
    assert not hasattr(raised.value, "status_code")


def test_client_status_records_polling_error_for_missing_monobank_production_token() -> None:
    db = FakeDatabase(make_payment(provider_mode="production"))
    db.settings.monobank_token = ""
    monobank_client = FakeMonobankClient({"invoiceId": "p2_demo", "status": "success"})
    factory_calls: list[dict[str, str]] = []

    def billing_provider_factory(provider_key: str, provider_mode: str) -> FakeMonobankClient:
        factory_calls.append({"provider_key": provider_key, "provider_mode": provider_mode})
        return monobank_client

    service = BillingPaymentStatusService(
        db,
        FakeTimeService(),
        billing_provider_factory=billing_provider_factory,
    )

    payload = service.get_client_payment_status(
        {"telegram_user_id": 42},
        payment_id=7,
        request_ip=None,
    )

    assert payload["payment"]["status"] == "invoice_created"
    assert payload["polling"]["attempted"] is True
    assert payload["polling"]["error"]["code"] == "provider_status_temporarily_unavailable"
    assert db.billing.events[0]["event_type"] == "client_status_polling_error"
    assert db.billing.events[0]["payload_json"]["error_type"] == (
        "BillingPaymentStatusConfigurationError"
    )
    assert db.billing.events[0]["payload_json"]["error_message"] == (
        "MONOBANK_TOKEN is not configured"
    )
    assert factory_calls == []
    assert monobank_client.calls == []


def test_client_status_does_not_poll_terminal_payment() -> None:
    db = FakeDatabase(make_payment(status="failure", failure_reason="declined", created=datetime(2026, 5, 6, 11, 0, tzinfo=UTC)))
    monobank_client = FakeMonobankClient({"invoiceId": "p2_demo", "status": "success"})
    service = BillingPaymentStatusService(
        db,
        FakeTimeService(),
        billing_provider_factory=lambda provider_key, provider_mode: monobank_client,
    )

    payload = service.get_client_payment_status(
        {"telegram_user_id": 42},
        payment_id=7,
        request_ip=None,
    )

    assert payload["status"]["is_failure"] is True
    assert payload["status"]["message"] == "declined"
    assert payload["status"]["failure_message"] == "declined"
    assert "failure_reason" not in payload["status"]
    assert payload["polling"]["attempted"] is False
    assert monobank_client.calls == []
