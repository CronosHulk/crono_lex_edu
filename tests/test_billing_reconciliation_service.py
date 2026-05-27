from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.billing.services.monobank_receipt_artifacts import (
    monobank_fiscal_checks_fetch_result,
)
from app.billing.services.provider_port import BillingProviderPaymentStatus
from app.billing.services.reconciliation_service import (
    BILLING_SUBSCRIPTION_RECOVERY_TASK_TYPE,
    BillingReconciliationService,
)
from app.domain.billing.monobank_statuses import monobank_payment_status_from_payload

USER_UUID = "11111111-1111-4111-8111-111111111111"


class FakeTimeService:
    def __init__(self) -> None:
        self.current_time = datetime(2026, 5, 6, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current_time


class FakeTaskLogs:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []
        self.updated: list[tuple[int, dict[str, object]]] = []

    def create(self, **kwargs):
        self.created.append(kwargs)
        return {"id": 77, **kwargs}

    def update(self, task_log_id: int, **kwargs):
        self.updated.append((task_log_id, kwargs))
        return {"id": task_log_id, **kwargs}


class FakeBillingRepository:
    def __init__(self, payments: list[dict[str, object]]) -> None:
        self.payments = [dict(payment) for payment in payments]
        self.status_updates: list[dict[str, object]] = []
        self.events: list[dict[str, object]] = []
        self.subscription_purchases: list[dict[str, object]] = []
        self.success_rechecked: list[int] = []
        self.receipts: list[dict[str, object]] = []

    def list_non_terminal_payments(self, *, limit: int = 100):
        return [dict(payment) for payment in self.payments[:limit]]

    def update_payment_provider_status(self, payment_id: int, **kwargs):
        self.status_updates.append({"payment_id": payment_id, **kwargs})
        for index, payment in enumerate(self.payments):
            if payment["id"] == payment_id:
                self.payments[index] = {**payment, **kwargs, "id": payment_id}
                return dict(self.payments[index])
        return None

    def create_payment_event(self, **kwargs):
        self.events.append(kwargs)
        return {"id": len(self.events), **kwargs}

    def list_success_payments_missing_subscription_purchase_today(self, *, current_time: datetime, limit: int = 100):
        return self.list_success_payments_requiring_subscription_recovery_today(current_time=current_time, limit=limit)

    def list_success_payments_requiring_subscription_recovery_today(self, *, current_time: datetime, limit: int = 100):
        return [
            dict(payment)
            for payment in self.payments[:limit]
            if payment.get("status") == "success" and not any(row["payment_id"] == payment["id"] for row in self.subscription_purchases)
        ]

    def list_active_subscription_purchase_payments_requiring_projection(self, *, current_time: datetime, limit: int = 100):
        return []

    def apply_subscription_purchase_for_payment(self, payment: dict[str, object], *, current_time: datetime):
        row = {
            "id": len(self.subscription_purchases) + 1,
            "payment_id": payment["id"],
            "user_uuid": payment["user_uuid"],
            "product_key": payment["plan_key"],
            "period_months": payment["period_months"],
            "amount_minor": payment["amount_minor"],
            "currency": payment["currency"],
            "period_start": current_time,
            "period_end": current_time,
            "status": "active",
        }
        self.subscription_purchases.append(row)
        return {
            "purchase": dict(row),
            "subscription": {
                "user_uuid": payment["user_uuid"],
                "plan_key": payment["plan_key"],
                "start": row["period_start"],
                "end": row["period_end"],
            },
        }

    def reverse_subscription_purchase_projection_for_payment(self, payment_id: int, *, current_time: datetime):
        return None

    def list_success_payments_due_for_recheck(self, *, current_time: datetime, window_days: int, interval_days: int, limit: int = 100):
        return [dict(payment) for payment in self.payments[:limit] if payment.get("status") == "success"]

    def mark_payment_success_rechecked(self, payment_id: int, *, current_time: datetime):
        self.success_rechecked.append(payment_id)

    def create_monobank_audit_log(self, **kwargs):
        return {"id": 1, **kwargs}

    def list_payment_receipts(self, payment_id: int):
        return [dict(row) for row in self.receipts if row["payment_id"] == payment_id]

    def create_receipt(self, **kwargs):
        row = {"id": len(self.receipts) + 1, **kwargs}
        self.receipts.append(row)
        return dict(row)


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

    def apply_paid_subscription_projection_for_user(self, user_uuid: str, **kwargs):
        payload = {"user_uuid": user_uuid, **kwargs}
        self.activations.append(payload)
        return {
            "user_uuid": user_uuid,
            "plan_key": kwargs["plan_key"],
            "start": kwargs["period_start"],
            "end": kwargs["period_end"],
        }


class FakeRuntimeState:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, object]] = {}

    def get(self, key: str):
        value = self.rows.get(key)
        return {"key": key, "value_json": value} if value is not None else None

    def set(self, key: str, value_json: dict[str, object], current_time: datetime):
        self.rows[key] = value_json


class FakeDatabase:
    def __init__(self, payments: list[dict[str, object]]) -> None:
        self.settings = SimpleNamespace(monobank_token_test="test-token", monobank_token="production-token")
        self.billing = FakeBillingRepository(payments)
        self.subscriptions = FakeSubscriptions()
        self.task_logs = FakeTaskLogs()
        self.app_runtime_state = FakeRuntimeState()


class FakeMonobankClient:
    def __init__(self, payload_by_invoice: dict[str, dict[str, object]]) -> None:
        self.payload_by_invoice = payload_by_invoice
        self.calls: list[dict[str, object]] = []
        self.fiscal_calls: list[dict[str, object]] = []

    def get_invoice_status(self, invoice_id: str, *, audit_context):
        self.calls.append({"invoice_id": invoice_id, "audit_context": audit_context})
        payload = self.payload_by_invoice[invoice_id]
        if isinstance(payload, Exception):
            raise payload
        return dict(payload)

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


class FakeBillingProvider:
    def __init__(
        self,
        payload_by_invoice: dict[str, dict[str, object]],
        provider_status_by_invoice: dict[str, BillingProviderPaymentStatus],
    ) -> None:
        self.payload_by_invoice = payload_by_invoice
        self.provider_status_by_invoice = provider_status_by_invoice
        self.calls: list[dict[str, object]] = []
        self.resolve_calls: list[dict[str, object]] = []

    def get_invoice_status(self, invoice_id: str, *, audit_context):
        self.calls.append({"invoice_id": invoice_id, "audit_context": audit_context})
        return dict(self.payload_by_invoice[invoice_id])

    def resolve_payment_status(self, payload: dict[str, object]) -> BillingProviderPaymentStatus:
        self.resolve_calls.append(dict(payload))
        invoice_id = str(payload["invoiceId"])
        return self.provider_status_by_invoice[invoice_id]

    def get_fiscal_checks(self, invoice_id: str, *, audit_context):
        return {"checks": []}


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
        "failure_reason": None,
        "created": datetime(2026, 5, 6, 11, 0, tzinfo=UTC),
        "updated": datetime(2026, 5, 6, 11, 30, tzinfo=UTC),
    }
    value.update(overrides)
    return value


def test_reconciliation_polls_non_terminal_payments_and_logs_summary() -> None:
    db = FakeDatabase([make_payment()])
    monobank_client = FakeMonobankClient({"p2_demo": {"invoiceId": "p2_demo", "status": "success", "amount": 1000}})
    service = BillingReconciliationService(
        db,
        FakeTimeService(),
        billing_provider_factory=lambda provider_key, provider_mode: monobank_client,
    )

    summary = service.process_non_terminal_payments(limit=10)

    assert summary == {
        "checked_count": 1,
        "updated_count": 1,
        "terminal_count": 1,
        "error_count": 0,
        "task_log_id": 77,
    }
    assert db.task_logs.created[0]["task_type"] == "billing_payment_reconciliation"
    assert db.task_logs.created[0]["description"] == "Processing non-terminal billing payments."
    assert db.task_logs.updated[0][1]["status"] == "success"
    assert "Monobank" not in str(db.task_logs.updated[0][1]["description"])
    assert db.billing.status_updates[0]["status"] == "success"
    assert db.billing.events[0]["source"] == "billing_payment_reconciliation"
    assert db.billing.events[1]["event_type"] == "subscription_activated"
    assert db.billing.subscription_purchases[0]["product_key"] == "premium"
    assert db.billing.events[1]["payload_json"]["subscription"]["plan_key"] == "premium"
    assert monobank_client.calls[0]["audit_context"].source_place == "reconciliation_worker"


def test_reconciliation_uses_billing_provider_to_resolve_status() -> None:
    db = FakeDatabase([make_payment(provider="custom_provider")])
    db.settings.monobank_token_test = None
    db.settings.monobank_token = None
    provider = FakeBillingProvider(
        {"p2_demo": {"invoiceId": "p2_demo", "status": "not-a-monobank-status"}},
        {
            "p2_demo": BillingProviderPaymentStatus(
                provider_status="provider-processing",
                internal_status="processing",
            )
        },
    )
    factory_calls: list[dict[str, str]] = []

    def billing_provider_factory(provider_key: str, provider_mode: str) -> FakeBillingProvider:
        factory_calls.append(
            {
                "provider_key": provider_key,
                "provider_mode": provider_mode,
            }
        )
        return provider

    service = BillingReconciliationService(
        db,
        FakeTimeService(),
        billing_provider_factory=billing_provider_factory,
    )

    summary = service.process_non_terminal_payments(limit=10)

    assert summary["checked_count"] == 1
    assert summary["updated_count"] == 1
    assert summary["terminal_count"] == 0
    assert provider.calls[0]["audit_context"].source_place == "reconciliation_worker"
    assert provider.resolve_calls == [{"invoiceId": "p2_demo", "status": "not-a-monobank-status"}]
    assert factory_calls == [
        {"provider_key": "custom_provider", "provider_mode": "test"},
    ]
    assert db.billing.status_updates[0]["status"] == "processing"
    assert db.billing.events[0]["provider_status"] == "provider-processing"


def test_reconciliation_falls_back_to_monobank_runtime_when_provider_is_blank_or_missing() -> None:
    payment_missing_provider = make_payment(
        id=8,
        provider_mode="test",
        provider_invoice_id="p2_missing",
    )
    payment_missing_provider.pop("provider")
    db = FakeDatabase(
        [
            make_payment(
                id=7,
                provider="",
                provider_mode="production",
                provider_invoice_id="p2_blank",
            ),
            payment_missing_provider,
        ]
    )
    provider = FakeBillingProvider(
        {
            "p2_blank": {"invoiceId": "p2_blank", "status": "provider-processing"},
            "p2_missing": {"invoiceId": "p2_missing", "status": "provider-processing"},
        },
        {
            "p2_blank": BillingProviderPaymentStatus(
                provider_status="provider-processing",
                internal_status="processing",
            ),
            "p2_missing": BillingProviderPaymentStatus(
                provider_status="provider-processing",
                internal_status="processing",
            ),
        },
    )
    factory_calls: list[dict[str, str]] = []

    def billing_provider_factory(provider_key: str, provider_mode: str) -> FakeBillingProvider:
        factory_calls.append(
            {
                "provider_key": provider_key,
                "provider_mode": provider_mode,
            }
        )
        return provider

    service = BillingReconciliationService(
        db,
        FakeTimeService(),
        billing_provider_factory=billing_provider_factory,
    )

    summary = service.process_non_terminal_payments(limit=10)

    assert summary["checked_count"] == 2
    assert summary["updated_count"] == 2
    assert summary["terminal_count"] == 0
    assert summary["error_count"] == 0
    assert factory_calls == [
        {"provider_key": "instant", "provider_mode": "production"},
        {"provider_key": "instant", "provider_mode": "test"},
    ]
    assert provider.resolve_calls == [
        {"invoiceId": "p2_blank", "status": "provider-processing"},
        {"invoiceId": "p2_missing", "status": "provider-processing"},
    ]


def test_reconciliation_fetches_fiscal_check_after_production_success() -> None:
    db = FakeDatabase([make_payment(provider_mode="production")])
    monobank_client = FakeMonobankClient({"p2_demo": {"invoiceId": "p2_demo", "status": "success", "amount": 1000}})
    service = BillingReconciliationService(
        db,
        FakeTimeService(),
        billing_provider_factory=lambda provider_key, provider_mode: monobank_client,
    )

    service.process_non_terminal_payments(limit=10)

    assert monobank_client.fiscal_calls[0]["invoice_id"] == "p2_demo"
    assert monobank_client.fiscal_calls[0]["audit_context"].source_place == "reconciliation_worker_fiscal_check"
    assert db.billing.receipts[0]["receipt_type"] == "fiscal_check"


def test_reconciliation_records_per_payment_errors_and_continues() -> None:
    db = FakeDatabase(
        [
            make_payment(id=7, provider_invoice_id="p2_fail"),
            make_payment(id=8, provider_invoice_id="p2_ok"),
        ]
    )
    monobank_client = FakeMonobankClient(
        {
            "p2_fail": RuntimeError("mono unavailable"),
            "p2_ok": {"invoiceId": "p2_ok", "status": "processing"},
        }
    )
    service = BillingReconciliationService(
        db,
        FakeTimeService(),
        billing_provider_factory=lambda provider_key, provider_mode: monobank_client,
    )

    summary = service.process_non_terminal_payments(limit=10)

    assert summary["checked_count"] == 2
    assert summary["updated_count"] == 1
    assert summary["terminal_count"] == 0
    assert summary["error_count"] == 1
    assert summary["errors"] == [{"payment_id": 7, "error": "mono unavailable"}]
    assert db.billing.events[0]["event_type"] == "reconciliation_error"
    assert db.billing.events[0]["source"] == "billing_payment_reconciliation"
    assert db.billing.events[1]["provider_status"] == "processing"


def test_internal_recovery_creates_subscription_purchase_for_today_success_payment() -> None:
    db = FakeDatabase([make_payment(status="success", paid_at=datetime(2026, 5, 6, 11, 0, tzinfo=UTC))])
    service = BillingReconciliationService(db, FakeTimeService())

    summary = service.process_due_internal_recovery(limit=10)

    assert summary["recovered_count"] == 1
    assert db.task_logs.created[0]["task_type"] == BILLING_SUBSCRIPTION_RECOVERY_TASK_TYPE
    assert db.billing.subscription_purchases[0]["payment_id"] == 7
    assert db.billing.events[0]["event_type"] == "subscription_recovered"
    assert db.billing.events[0]["payload_json"]["subscription"]["plan_key"] == "premium"


def test_internal_recovery_queues_post_upgrade_rescan_for_paid_subscription() -> None:
    db = FakeDatabase([make_payment(status="success", paid_at=datetime(2026, 5, 6, 11, 0, tzinfo=UTC))])
    rescan_calls: list[dict[str, object]] = []
    service = BillingReconciliationService(
        db,
        FakeTimeService(),
        post_upgrade_rescan=lambda **kwargs: rescan_calls.append(dict(kwargs)) or {"status": "queued", "task_log_id": 10},
    )

    service.process_due_internal_recovery(limit=10)

    assert rescan_calls == [
        {
            "telegram_user_id": 42,
            "user_uuid": USER_UUID,
            "current_time": datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
        }
    ]
    assert db.billing.events[1]["event_type"] == "post_upgrade_google_doc_rescan_queued"
    assert db.billing.events[1]["source"] == "billing_subscription_recovery"


def test_success_recheck_runs_at_configured_hour_and_marks_checked_payment() -> None:
    time_service = FakeTimeService()
    time_service.current_time = datetime(2026, 5, 6, 6, 0, tzinfo=UTC)
    db = FakeDatabase([make_payment(status="success", paid_at=datetime(2026, 5, 5, 11, 0, tzinfo=UTC))])
    monobank_client = FakeMonobankClient({"p2_demo": {"invoiceId": "p2_demo", "status": "success", "amount": 1000}})
    service = BillingReconciliationService(
        db,
        time_service,
        billing_provider_factory=lambda provider_key, provider_mode: monobank_client,
    )

    summary = service.process_due_success_recheck(limit=10)

    assert summary["checked_count"] == 1
    assert db.task_logs.created[0]["task_type"] == "billing_payment_success_recheck"
    assert db.task_logs.created[0]["description"] == "Rechecking successful billing payments for late reverse statuses."
    assert "Monobank" not in str(db.task_logs.updated[0][1]["description"])
    assert db.billing.success_rechecked == [7]
    assert db.billing.events[0]["source"] == "billing_payment_success_recheck"
    assert db.app_runtime_state.rows["billing.payment_success_recheck"] == {
        "last_run_at": "2026-05-06T06:00:00+00:00"
    }
    assert "billing.monobank_success_recheck" not in db.app_runtime_state.rows
    assert monobank_client.calls[0]["audit_context"].source_place == "success_recheck_worker"


def test_success_recheck_respects_legacy_runtime_state_key_without_task_log() -> None:
    time_service = FakeTimeService()
    time_service.current_time = datetime(2026, 5, 6, 6, 0, tzinfo=UTC)
    db = FakeDatabase([make_payment(status="success", paid_at=datetime(2026, 5, 5, 11, 0, tzinfo=UTC))])
    db.app_runtime_state.rows["billing.monobank_success_recheck"] = {
        "last_run_at": datetime(2026, 5, 6, 5, 59, tzinfo=UTC).isoformat()
    }
    monobank_client = FakeMonobankClient({"p2_demo": {"invoiceId": "p2_demo", "status": "success", "amount": 1000}})
    service = BillingReconciliationService(
        db,
        time_service,
        billing_provider_factory=lambda provider_key, provider_mode: monobank_client,
    )

    summary = service.process_due_success_recheck(limit=10)

    assert summary == {"skipped": True, "reason": "not_due"}
    assert db.task_logs.created == []
    assert db.billing.success_rechecked == []
    assert monobank_client.calls == []
    assert "billing.payment_success_recheck" not in db.app_runtime_state.rows
