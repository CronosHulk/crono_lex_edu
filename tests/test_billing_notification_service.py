from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.billing.services.monobank_receipt_artifacts import (
    monobank_fiscal_checks_fetch_result,
    monobank_receipt_fetch_result,
)
from app.billing.services.notification_service import (
    BillingBotNotificationService,
    build_payment_notification_screen,
    build_receipt_delivery_screen,
)
from app.billing.services.provider_port import (
    BillingProviderReceiptArtifact,
    BillingProviderReceiptFetchResult,
)
from app.billing.services.receipt_retrieval_service import BillingReceiptRetrievalService
from app.billing.services.receipt_storage_port import BillingReceiptArtifactRef

USER_UUID = "11111111-1111-4111-8111-111111111111"


class FakeTimeService:
    def now(self) -> datetime:
        return datetime(2026, 5, 6, 12, 0, tzinfo=UTC)


class FakeBillingReceiptStorageProvider:
    def __init__(self) -> None:
        self.writes: list[dict[str, object]] = []

    def write_receipt_file(self, *, receipt_id: int, payload: bytes) -> BillingReceiptArtifactRef:
        self.writes.append({"receipt_id": receipt_id, "payload": payload})
        filename = f"billing_receipt_{receipt_id}.pdf"
        return BillingReceiptArtifactRef(
            path=f"memory://billing-receipts/{filename}",
            filename=filename,
        )


class FailingBillingReceiptStorageProvider:
    def write_receipt_file(self, *, receipt_id: int, payload: bytes) -> BillingReceiptArtifactRef:
        raise RuntimeError("receipt storage unavailable")


def build_billing_bot_notification_service(
    db: FakeDatabase,
    time_service: FakeTimeService | None = None,
    *,
    billing_receipt_storage_provider: FakeBillingReceiptStorageProvider | FailingBillingReceiptStorageProvider | None = None,
    **kwargs: object,
) -> BillingBotNotificationService:
    billing_provider_factory = kwargs.pop("billing_provider_factory", None)
    if billing_provider_factory is not None:
        kwargs["billing_receipt_fiscal_provider_factory"] = billing_provider_factory
    return BillingBotNotificationService(
        db,
        time_service or FakeTimeService(),
        billing_receipt_storage_provider=(
            billing_receipt_storage_provider or FakeBillingReceiptStorageProvider()
        ),
        **kwargs,
    )


class FakeBillingRepository:
    def __init__(self, payment: dict[str, object]) -> None:
        self.payment = dict(payment)
        self.notifications = [
            {
                "id": 5,
                "payment_id": payment["id"],
                "notification_type": "terminal_status",
                "status_snapshot": payment["status"],
                "receipt_ids": [],
            }
        ]
        self.receipts: list[dict[str, object]] = []
        self.sent: list[int] = []
        self.skipped: list[dict[str, object]] = []
        self.failed: list[dict[str, object]] = []
        self.audit_rows: list[dict[str, object]] = []
        self.receipt_delivery_sent: list[int] = []
        self.receipt_delivery_failed: list[dict[str, object]] = []
        self.receipt_admin_alerted: list[int] = []
        self.success_receipt_retry_payments: list[dict[str, object]] = []

    def claim_due_bot_notifications(self, *, current_time: datetime, limit: int = 50):
        return list(self.notifications)

    def get_payment_by_id(self, payment_id: int):
        if payment_id == self.payment["id"]:
            return dict(self.payment)
        return None

    def list_payment_receipts(self, payment_id: int):
        return [dict(row) for row in self.receipts if row["payment_id"] == payment_id]

    def create_receipt(self, **kwargs):
        row = {"id": len(self.receipts) + 1, **kwargs}
        self.receipts.append(row)
        return dict(row)

    def list_success_payments_requiring_receipt_retry(
        self,
        *,
        current_time: datetime,
        limit: int = 100,
        max_attempts: int | None = None,
    ):
        return [dict(row) for row in self.success_receipt_retry_payments[:limit]]

    def claim_due_receipt_delivery_notifications(
        self,
        *,
        current_time: datetime,
        limit: int = 50,
        claim_timeout_minutes: int = 10,
        exclude_receipt_ids: set[int] | None = None,
    ):
        excluded_ids = exclude_receipt_ids or set()
        rows = [
            row
            for row in self.receipts
            if row.get("status") == "done"
            and row.get("file_base64")
            and row.get("bot_delivery_status") in {None, "queued", "failed"}
            and int(row["id"]) not in excluded_ids
        ][:limit]
        for row in rows:
            row["bot_delivery_status"] = "claimed"
        return [dict(row) for row in rows]

    def set_bot_notification_receipt_ids(self, notification_id: int, receipt_ids: list[int], *, current_time: datetime):
        for row in self.notifications:
            if row["id"] == notification_id:
                row["receipt_ids"] = sorted(set(receipt_ids))
                return

    def mark_receipt_delivery_sent(self, receipt_id: int, *, current_time: datetime):
        self.receipt_delivery_sent.append(receipt_id)

    def mark_receipt_delivery_failed(self, receipt_id: int, *, error_text: str, current_time: datetime):
        self.receipt_delivery_failed.append({"id": receipt_id, "error_text": error_text})

    def claim_receipts_requiring_admin_alert(
        self,
        *,
        current_time: datetime,
        max_retry_count: int,
        limit: int = 50,
        claim_timeout_minutes: int = 10,
    ):
        rows = [
            row
            for row in self.receipts
            if row.get("receipt_type") in {"receipt", "fiscal_check"}
            and row.get("status") in {"failed", "unavailable"}
            and row.get("retry_count", 0) >= max_retry_count
            and row.get("admin_alerted_at") is None
            and row.get("admin_alert_status") in {None, "queued", "failed"}
        ][:limit]
        for row in rows:
            row["admin_alert_status"] = "claimed"
        return [dict(row) for row in rows]

    def mark_receipt_admin_alerted(self, receipt_id: int, *, current_time: datetime):
        self.receipt_admin_alerted.append(receipt_id)

    def mark_receipt_admin_alert_sent(self, receipt_id: int, *, current_time: datetime):
        self.receipt_admin_alerted.append(receipt_id)

    def mark_receipt_admin_alert_failed(self, receipt_id: int, *, error_text: str, current_time: datetime):
        self.failed.append({"id": receipt_id, "error_text": error_text, "type": "admin_alert"})

    def get_bot_notification_by_id(self, notification_id: int):
        for row in self.notifications:
            if row["id"] == notification_id:
                return dict(row)
        return None

    def mark_receipt_deliveries_sent_by_ids(self, receipt_ids: list[int], *, current_time: datetime):
        receipt_id_set = set(receipt_ids)
        for row in self.receipts:
            if int(row["id"]) in receipt_id_set and row.get("status") == "done" and (row.get("tax_url") or row.get("file_base64")):
                row["bot_delivery_status"] = "sent"

    def mark_bot_notification_sent(self, notification_id: int, *, current_time: datetime):
        self.sent.append(notification_id)

    def mark_bot_notification_skipped(self, notification_id: int, *, error_text: str, current_time: datetime):
        self.skipped.append({"id": notification_id, "error_text": error_text})

    def mark_bot_notification_failed(self, notification_id: int, *, error_text: str, current_time: datetime):
        self.failed.append({"id": notification_id, "error_text": error_text})

    def create_monobank_audit_log(self, **kwargs):
        self.audit_rows.append(kwargs)
        return {"id": len(self.audit_rows), **kwargs}

    def create_payment_event(self, **kwargs):
        return {"id": 1, **kwargs}


class FakeProfiles:
    def __init__(self, chat_id: int | None = 1001) -> None:
        self.chat_id = chat_id

    def get_profile(self, telegram_user_id: int):
        return {"telegram_user_id": telegram_user_id, "chat_id": self.chat_id}

    def list_super_admin_profiles(self):
        return [{"telegram_user_id": 9001, "chat_id": 9002}]


class FakeTaskLogs:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []
        self.updated: list[tuple[int, dict[str, object]]] = []

    def create(self, **kwargs):
        self.created.append(kwargs)
        return {"id": 55, **kwargs}

    def update(self, task_log_id: int, **kwargs):
        self.updated.append((task_log_id, kwargs))


class FakeAppSettings:
    def __init__(self) -> None:
        self.value: dict[str, object] = {}

    def get_value(self, key: str):
        if key == "billing.runtime_settings":
            return self.value
        return None


class FakeRuntimeState:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, object]] = {}

    def get(self, key: str):
        value = self.rows.get(key)
        return {"key": key, "value_json": value} if value is not None else None

    def set(self, key: str, value_json: dict[str, object], current_time: datetime):
        self.rows[key] = value_json


class FakeDatabase:
    def __init__(self, payment: dict[str, object], *, chat_id: int | None = 1001) -> None:
        self.settings = SimpleNamespace(monobank_token_test="test-token", monobank_token="production-token")
        self.billing = FakeBillingRepository(payment)
        self.user_profiles = FakeProfiles(chat_id)
        self.task_logs = FakeTaskLogs()
        self.app_settings = FakeAppSettings()
        self.app_runtime_state = FakeRuntimeState()


class FakeMonobankClient:
    def __init__(self, *, receipt_error: Exception | None = None, fiscal_error: Exception | None = None) -> None:
        self.receipt_calls: list[str] = []
        self.fiscal_calls: list[str] = []
        self.receipt_error = receipt_error
        self.fiscal_error = fiscal_error

    def get_receipt(self, invoice_id: str, *, audit_context):
        self.receipt_calls.append(invoice_id)
        if self.receipt_error is not None:
            raise self.receipt_error
        return {"file": "JVBERi0xLjQK"}

    def get_fiscal_checks(self, invoice_id: str, *, audit_context):
        self.fiscal_calls.append(invoice_id)
        if self.fiscal_error is not None:
            raise self.fiscal_error
        return {
            "checks": [
                {
                    "id": "check-1",
                    "status": "done",
                    "type": "sale",
                    "fiscalizationSource": "monopay",
                    "taxUrl": "https://cabinet.tax.gov.ua/check/1",
                    "file": "JVBERi0xLjQK",
                }
            ]
        }

    def fetch_receipt(self, invoice_id: str, *, audit_context):
        return monobank_receipt_fetch_result(
            self.get_receipt(invoice_id, audit_context=audit_context)
        )

    def fetch_fiscal_checks(self, invoice_id: str, *, audit_context):
        return monobank_fiscal_checks_fetch_result(
            self.get_fiscal_checks(invoice_id, audit_context=audit_context)
        )


class FakeProviderAPIError(Exception):
    def __init__(self, message: str, *, status_code: int, error_code: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class FakeCustomBillingProvider:
    provider_key = "custompay"

    def __init__(self, fiscal_result: BillingProviderReceiptFetchResult) -> None:
        self.fiscal_result = fiscal_result
        self.fiscal_calls: list[dict[str, object]] = []

    def fetch_fiscal_checks(self, invoice_id: str, *, audit_context):
        self.fiscal_calls.append({"invoice_id": invoice_id, "audit_context": audit_context})
        return self.fiscal_result


def make_payment(**overrides) -> dict[str, object]:
    value = {
        "id": 7,
        "user_uuid": USER_UUID,
        "telegram_user_id": 42,
        "plan_key": "premium",
        "period_months": 3,
        "amount_minor": 3000,
        "status": "success",
        "provider_mode": "production",
        "provider_invoice_id": "p2_demo",
        "provider_reference": "clx-order-7",
        "failure_reason": None,
    }
    value.update(overrides)
    return value


def monobank_provider_factory(monobank_client: FakeMonobankClient):
    def factory(provider_key: str, provider_mode: str):
        _ = (provider_key, provider_mode)
        return monobank_client

    return factory


def test_dispatch_success_notification_uses_saved_fiscal_check_and_returns_delivery_ack_metadata() -> None:
    db = FakeDatabase(make_payment())
    db.billing.receipts.append(
        {
            "id": 1,
            "payment_id": 7,
            "receipt_type": "fiscal_check",
            "status": "done",
            "tax_url": "https://cabinet.tax.gov.ua/check/1",
            "file_base64": "JVBERi0xLjQK",
            "bot_delivery_status": "queued",
            "payload_json": {},
        }
    )
    monobank_client = FakeMonobankClient()
    storage_provider = FakeBillingReceiptStorageProvider()
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_receipt_storage_provider=storage_provider,
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    notifications = service.dispatch_due_billing_notifications()

    assert len(notifications) == 2
    assert notifications[0].telegram_user_id == 42
    assert notifications[0].chat_id == 1001
    assert "Оплата успішна" in notifications[0].screen.text
    assert "особистому кабінеті" in notifications[0].screen.text
    assert len(notifications[0].screen.buttons) == 1
    assert notifications[0].screen.buttons[0].action == "billing:close"
    assert notifications[0].screen.buttons[0].text == "Закрити"
    assert notifications[0].screen.documents == []
    assert monobank_client.receipt_calls == []
    assert monobank_client.fiscal_calls == []
    assert notifications[0].delivery_kind == "billing_bot_notification"
    assert notifications[0].delivery_id == 5
    assert notifications[1].delivery_kind == "billing_receipt_delivery"
    assert notifications[1].delivery_id == 1
    assert db.billing.notifications[0]["receipt_ids"] == []
    assert db.billing.sent == []
    assert storage_provider.writes == [{"receipt_id": 1, "payload": b"%PDF-1.4\n"}]


def test_save_bot_notification_delivery_result_marks_success_and_embedded_receipts() -> None:
    db = FakeDatabase(make_payment())
    db.billing.notifications[0]["receipt_ids"] = [1, 2]
    db.billing.receipts.extend(
        [
            {
                "id": 1,
                "payment_id": 7,
                "receipt_type": "receipt",
                "status": "done",
                "tax_url": "https://example.test/receipt/1",
                "file_base64": "",
                "bot_delivery_status": "claimed",
                "payload_json": {},
            },
            {
                "id": 2,
                "payment_id": 7,
                "receipt_type": "fiscal_check",
                "status": "done",
                "tax_url": "",
                "file_base64": "JVBERi0xLjQK",
                "bot_delivery_status": "claimed",
                "payload_json": {},
            },
        ]
    )
    storage_provider = FakeBillingReceiptStorageProvider()
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_receipt_storage_provider=storage_provider,
    )

    service.save_bot_notification_delivery_result(5, is_sent=True, error_text=None)

    assert db.billing.sent == [5]
    assert [row["bot_delivery_status"] for row in db.billing.receipts] == ["sent", "sent"]


def test_save_bot_notification_delivery_result_records_failure_default() -> None:
    db = FakeDatabase(make_payment())
    storage_provider = FakeBillingReceiptStorageProvider()
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_receipt_storage_provider=storage_provider,
    )

    service.save_bot_notification_delivery_result(5, is_sent=False, error_text=None)

    assert db.billing.failed == [{"id": 5, "error_text": "Telegram delivery failed"}]


def test_save_receipt_delivery_result_marks_sent_or_failed() -> None:
    db = FakeDatabase(make_payment())
    storage_provider = FakeBillingReceiptStorageProvider()
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_receipt_storage_provider=storage_provider,
    )

    service.save_receipt_delivery_result(10, is_sent=True, error_text=None)
    service.save_receipt_delivery_result(11, is_sent=False, error_text="send failed")

    assert db.billing.receipt_delivery_sent == [10]
    assert db.billing.receipt_delivery_failed == [{"id": 11, "error_text": "send failed"}]


def test_save_receipt_admin_alert_result_marks_sent_or_failed() -> None:
    db = FakeDatabase(make_payment())
    service = build_billing_bot_notification_service(db, FakeTimeService())

    service.save_receipt_admin_alert_result(10, is_sent=True, error_text=None)
    service.save_receipt_admin_alert_result(11, is_sent=False, error_text=None)

    assert db.billing.receipt_admin_alerted == [10]
    assert db.billing.failed == [
        {
            "id": 11,
            "error_text": "Telegram admin alert delivery failed",
            "type": "admin_alert",
        }
    ]


def test_dispatch_success_notification_does_not_fetch_or_create_receipts_in_monobank_test_mode() -> None:
    db = FakeDatabase(make_payment(provider_mode="test"))
    monobank_client = FakeMonobankClient()
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    notifications = service.dispatch_due_billing_notifications()

    assert len(notifications) == 1
    assert "Тестовий платіж" in notifications[0].screen.text
    assert "sandbox не створює фіскальні чеки" in notifications[0].screen.text
    assert notifications[0].screen.buttons == [notifications[0].screen.buttons[-1]]
    assert notifications[0].screen.buttons[0].action == "billing:close"
    assert monobank_client.receipt_calls == []
    assert monobank_client.fiscal_calls == []
    assert db.billing.receipts == []
    assert db.billing.notifications[0]["receipt_ids"] == []


def test_custom_provider_test_payment_does_not_show_monobank_sandbox_receipt_status() -> None:
    screen = build_payment_notification_screen(
        make_payment(provider="custompay", provider_mode="test"),
        receipts=[],
    )

    assert "Тестовий платіж" in screen.text
    assert "Monobank sandbox" not in screen.text
    assert "sandbox не створює" not in screen.text
    assert "Чек буде доступний" in screen.text


def test_receipt_retrieval_skips_monobank_test_mode_without_placeholder_rows() -> None:
    payment = make_payment(provider="monobank", provider_mode="test")
    db = FakeDatabase(payment)
    monobank_client = FakeMonobankClient()
    service = BillingReceiptRetrievalService(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    receipts = service.ensure_success_receipts(payment)

    assert receipts == []
    assert db.billing.receipts == []
    assert monobank_client.receipt_calls == []
    assert monobank_client.fiscal_calls == []


def test_receipt_retrieval_custom_provider_test_mode_is_not_skipped_as_monobank_sandbox() -> None:
    payment = make_payment(
        provider="custompay",
        provider_mode="test",
        provider_invoice_id="custom-test-invoice-7",
    )
    db = FakeDatabase(payment)
    provider = FakeCustomBillingProvider(
        BillingProviderReceiptFetchResult(
            receipt_type="fiscal_check",
            unavailable_reason="custom_provider_receipts_pending",
            provider_payload={"status": "pending"},
        )
    )
    factory_calls: list[dict[str, str]] = []

    def provider_factory(*, provider_key: str, provider_mode: str):
        factory_calls.append({"provider_key": provider_key, "provider_mode": provider_mode})
        return provider

    service = BillingReceiptRetrievalService(
        db,
        FakeTimeService(),
        billing_provider_factory=provider_factory,
    )

    receipts = service.ensure_success_receipts(payment)

    assert receipts == db.billing.receipts
    assert factory_calls == [{"provider_key": "custompay", "provider_mode": "test"}]
    assert len(provider.fiscal_calls) == 1
    assert provider.fiscal_calls[0]["invoice_id"] == "custom-test-invoice-7"
    assert db.billing.receipts[0]["status"] == "unavailable"


@pytest.mark.parametrize(
    "payment_mutator",
    [
        lambda payment: payment.pop("provider", None),
        lambda payment: payment.__setitem__("provider", ""),
    ],
    ids=["missing_provider", "blank_provider"],
)
def test_receipt_retrieval_falls_back_to_monobank_runtime_for_blank_or_missing_provider(
    payment_mutator: Callable[[dict[str, object]], object],
) -> None:
    payment = make_payment()
    payment_mutator(payment)
    db = FakeDatabase(payment)
    provider = FakeCustomBillingProvider(
        BillingProviderReceiptFetchResult(
            receipt_type="fiscal_check",
            unavailable_reason="compatibility_monobank_path",
        )
    )
    factory_calls: list[dict[str, str]] = []

    def provider_factory(*, provider_key: str, provider_mode: str):
        factory_calls.append({"provider_key": provider_key, "provider_mode": provider_mode})
        return provider

    service = BillingReceiptRetrievalService(
        db,
        FakeTimeService(),
        billing_provider_factory=provider_factory,
    )

    receipts = service.ensure_success_receipts(payment)

    assert receipts == db.billing.receipts
    assert factory_calls == [{"provider_key": "instant", "provider_mode": "production"}]
    assert len(provider.fiscal_calls) == 1
    assert provider.fiscal_calls[0]["invoice_id"] == "p2_demo"


def test_receipt_retrieval_uses_monobank_billing_provider_factory() -> None:
    db = FakeDatabase(make_payment())
    monobank_client = FakeMonobankClient()
    service = BillingReceiptRetrievalService(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    receipts = service.ensure_success_receipts(make_payment())

    assert receipts == db.billing.receipts
    assert monobank_client.fiscal_calls == ["p2_demo"]
    assert db.billing.receipts[0]["receipt_type"] == "fiscal_check"


def test_receipt_retrieval_persists_provider_normalized_fiscal_artifact() -> None:
    payment = make_payment(
        provider="custompay",
        provider_invoice_id="custom-invoice-7",
        provider_reference="custom-order-7",
    )
    db = FakeDatabase(payment)
    provider = FakeCustomBillingProvider(
        BillingProviderReceiptFetchResult(
            receipt_type="fiscal_check",
            artifacts=(
                BillingProviderReceiptArtifact(
                    receipt_type="fiscal_check",
                    status="new",
                    provider_check_id="55a1d9f7-7475-4088-86d2-2132c2261e71",
                    fiscalization_source="checkbox",
                    file_base64="JVBERi0xLjQK",
                    payload={
                        "artifact_id": "normalized-check-1",
                        "shape": "provider_port",
                    },
                ),
            ),
            provider_payload={"result": "normalized"},
        )
    )
    factory_calls: list[dict[str, str]] = []

    def provider_factory(*, provider_key: str, provider_mode: str):
        factory_calls.append({"provider_key": provider_key, "provider_mode": provider_mode})
        return provider

    service = BillingReceiptRetrievalService(
        db,
        FakeTimeService(),
        billing_provider_factory=provider_factory,
    )

    receipts = service.ensure_success_receipts(payment, source_place="custom_receipt_job")

    assert receipts == db.billing.receipts
    assert factory_calls == [{"provider_key": "custompay", "provider_mode": "production"}]
    assert len(provider.fiscal_calls) == 1
    call = provider.fiscal_calls[0]
    audit_context = call["audit_context"]
    assert call["invoice_id"] == "custom-invoice-7"
    assert audit_context.source_place == "custom_receipt_job"
    assert audit_context.actor_user_uuid == USER_UUID
    assert audit_context.telegram_user_id == 42
    assert audit_context.payment_id == 7
    assert audit_context.order_reference == "custom-order-7"
    assert audit_context.invoice_id == "custom-invoice-7"
    assert db.billing.receipts[0] == {
        "id": 1,
        "payment_id": 7,
        "receipt_type": "fiscal_check",
        "status": "done",
        "provider_check_id": "55a1d9f7-7475-4088-86d2-2132c2261e71",
        "fiscalization_source": "checkbox",
        "tax_url": "https://check.checkbox.ua/55a1d9f7-7475-4088-86d2-2132c2261e71",
        "file_base64": "JVBERi0xLjQK",
        "payload_json": {
            "artifact_id": "normalized-check-1",
            "shape": "provider_port",
        },
        "bot_delivery_status": "sent",
        "retry_count": 1,
        "next_retry_at": None,
        "current_time": FakeTimeService().now(),
    }


def test_receipt_retrieval_persists_provider_unavailable_result_payload() -> None:
    payment = make_payment(provider="custompay", provider_invoice_id="custom-invoice-7")
    db = FakeDatabase(payment)
    provider = FakeCustomBillingProvider(
        BillingProviderReceiptFetchResult(
            receipt_type="fiscal_check",
            unavailable_reason="custom_provider_receipts_pending",
            provider_payload={"status": "pending", "retry_after_seconds": 30},
        )
    )
    service = BillingReceiptRetrievalService(
        db,
        FakeTimeService(),
        billing_provider_factory=lambda **kwargs: provider,
    )

    receipts = service.ensure_success_receipts(payment)

    assert receipts == db.billing.receipts
    assert provider.fiscal_calls[0]["invoice_id"] == "custom-invoice-7"
    assert db.billing.receipts[0]["receipt_type"] == "fiscal_check"
    assert db.billing.receipts[0]["status"] == "unavailable"
    assert db.billing.receipts[0]["payload_json"] == {
        "reason": "custom_provider_receipts_pending",
        "provider_payload": {"status": "pending", "retry_after_seconds": 30},
    }


def test_dispatch_success_notification_does_not_retry_unavailable_receipt() -> None:
    db = FakeDatabase(make_payment())
    db.billing.receipts.append(
        {
            "id": 1,
            "payment_id": 7,
            "receipt_type": "receipt",
            "status": "unavailable",
            "payload_json": {"reason": "temporary"},
        }
    )
    monobank_client = FakeMonobankClient()
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    notifications = service.dispatch_due_billing_notifications()

    assert len(notifications) == 1
    assert monobank_client.receipt_calls == []
    assert not any(row["receipt_type"] == "receipt" and row["status"] == "done" for row in db.billing.receipts)


def test_dispatch_uses_status_snapshot_when_payment_changed_before_delivery() -> None:
    db = FakeDatabase(make_payment(status="reversed"))
    db.billing.notifications[0]["status_snapshot"] = "success"
    monobank_client = FakeMonobankClient()
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    notifications = service.dispatch_due_billing_notifications()

    assert "Оплата успішна" in notifications[0].screen.text
    assert "Оплата повернена" not in notifications[0].screen.text
    assert monobank_client.receipt_calls == []
    assert notifications[0].screen.buttons[0].action == "billing:close"


def test_dispatch_failure_notification_does_not_fetch_receipts() -> None:
    db = FakeDatabase(make_payment(status="failure", failure_reason="Insufficient funds"))
    monobank_client = FakeMonobankClient()
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    notifications = service.dispatch_due_billing_notifications()

    assert "Insufficient funds" in notifications[0].screen.text
    assert monobank_client.receipt_calls == []
    assert notifications[0].delivery_id == 5
    assert db.billing.sent == []


def test_dispatch_skips_notification_without_chat_id() -> None:
    db = FakeDatabase(make_payment(), chat_id=None)
    service = build_billing_bot_notification_service(db, FakeTimeService())

    notifications = service.dispatch_due_billing_notifications()

    assert notifications == []
    assert db.billing.skipped == [{"id": 5, "error_text": "User profile does not have a Telegram chat_id"}]


def test_dispatch_success_notification_keeps_user_notification_when_receipt_fetch_crashes() -> None:
    db = FakeDatabase(make_payment())
    monobank_client = FakeMonobankClient(receipt_error=RuntimeError("network timeout"))
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    notifications = service.dispatch_due_billing_notifications()

    assert len(notifications) == 1
    assert "Оплата успішна" in notifications[0].screen.text
    assert db.billing.failed == []
    assert db.billing.receipts == []


def test_monobank_receipt_fetch_provider_api_error_creates_unavailable_receipt_payload() -> None:
    db = FakeDatabase(make_payment())
    monobank_client = FakeMonobankClient(
        receipt_error=FakeProviderAPIError("receipt is not ready", status_code=404, error_code="not_found")
    )
    service = BillingReceiptRetrievalService(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    receipts = service._fetch_monobank_receipt(
        make_payment(),
        "p2_demo",
        source_place="billing_bot_receipt",
        retry_count=0,
        retry_delay_seconds=60,
        max_attempts=3,
    )

    assert receipts == db.billing.receipts
    assert monobank_client.receipt_calls == ["p2_demo"]
    assert db.billing.receipts[0]["receipt_type"] == "receipt"
    assert db.billing.receipts[0]["status"] == "unavailable"
    assert db.billing.receipts[0]["payload_json"] == {
        "status_code": 404,
        "error_code": "not_found",
        "error_text": "receipt is not ready",
    }


def test_monobank_fiscal_checks_provider_api_error_creates_unavailable_receipt_row() -> None:
    db = FakeDatabase(make_payment())
    monobank_client = FakeMonobankClient(
        fiscal_error=FakeProviderAPIError("fiscal checks are not ready", status_code=409, error_code="try_later")
    )
    service = BillingReceiptRetrievalService(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    receipts = service.ensure_success_receipts(make_payment())

    assert receipts == db.billing.receipts
    assert monobank_client.fiscal_calls == ["p2_demo"]
    assert db.billing.receipts[0]["receipt_type"] == "fiscal_check"
    assert db.billing.receipts[0]["status"] == "unavailable"


def test_dispatch_due_receipt_delivery_returns_ack_metadata() -> None:
    db = FakeDatabase(make_payment())
    db.billing.notifications = []
    db.billing.receipts.append(
        {
            "id": 3,
            "payment_id": 7,
            "receipt_type": "fiscal_check",
            "status": "done",
            "tax_url": None,
            "file_base64": "JVBERi0xLjQK",
            "bot_delivery_status": "queued",
            "payload_json": {},
        }
    )
    storage_provider = FakeBillingReceiptStorageProvider()
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_receipt_storage_provider=storage_provider,
    )

    notifications = service.dispatch_due_billing_notifications()

    assert len(notifications) == 1
    assert notifications[0].delivery_kind == "billing_receipt_delivery"
    assert notifications[0].delivery_id == 3
    assert notifications[0].screen.buttons[0].action == "billing:close"
    assert notifications[0].screen.documents[0].filename == "billing_receipt_3.pdf"
    assert notifications[0].screen.documents[0].caption == "Чек оплати"
    assert storage_provider.writes == [{"receipt_id": 3, "payload": b"%PDF-1.4\n"}]


def test_dispatch_due_receipt_delivery_marks_failed_when_storage_write_fails() -> None:
    db = FakeDatabase(make_payment())
    db.billing.notifications = []
    db.billing.receipts.append(
        {
            "id": 3,
            "payment_id": 7,
            "receipt_type": "fiscal_check",
            "status": "done",
            "tax_url": None,
            "file_base64": "JVBERi0xLjQK",
            "bot_delivery_status": "queued",
            "payload_json": {},
        }
    )
    service = build_billing_bot_notification_service(
        db,
        billing_receipt_storage_provider=FailingBillingReceiptStorageProvider(),
    )

    notifications = service.dispatch_due_billing_notifications()

    assert notifications == []
    assert db.billing.receipt_delivery_failed == [
        {
            "id": 3,
            "error_text": "RuntimeError: receipt storage unavailable",
        }
    ]


def test_receipt_delivery_screen_attaches_base64_receipt_file() -> None:
    storage_provider = FakeBillingReceiptStorageProvider()

    screen = build_receipt_delivery_screen(
        make_payment(),
        {
            "id": 3,
            "payment_id": 7,
            "receipt_type": "fiscal_check",
            "status": "done",
            "file_base64": "JVBERi0xLjQK",
            "payload_json": {},
        },
        billing_receipt_storage_provider=storage_provider,
    )

    assert screen.documents[0].filename == "billing_receipt_3.pdf"
    assert screen.documents[0].caption == "Чек оплати"
    assert storage_provider.writes == [{"receipt_id": 3, "payload": b"%PDF-1.4\n"}]


def test_payment_notification_screen_shows_double_time_granted_period() -> None:
    payment = make_payment(
        period_months=3,
        provider_status_json={
            "checkout_quote": {
                "granted_period_months": 6,
                "promotion": {"label": "Двойное время за поддержку проекта"},
            }
        },
    )

    screen = build_payment_notification_screen(payment, receipts=[])

    assert "Період: 3 міс. (нараховано 6 міс.)" in screen.text
    assert "Акція: Двойное время за поддержку проекта" in screen.text


def test_process_due_receipt_retries_exhausts_and_admin_alert_is_dispatched() -> None:
    db = FakeDatabase(make_payment())
    db.billing.notifications = []
    db.billing.success_receipt_retry_payments = [make_payment()]
    db.app_settings.value = {"receipt_retry_max_attempts": 1, "receipt_retry_interval_seconds": 60}
    monobank_client = FakeMonobankClient(
        receipt_error=RuntimeError("mono down"),
        fiscal_error=RuntimeError("mono down"),
    )
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    summary = service.process_due_receipt_retries(limit=10)
    notifications = service.dispatch_due_billing_notifications()

    assert summary["exhausted_count"] == 1
    assert db.task_logs.created[0]["task_type"] == "billing_receipt_retry"
    assert db.task_logs.created[0]["description"] == "Retrying billing receipt retrieval for successful payments."
    assert "Monobank" not in str(db.task_logs.updated[0][1]["description"])
    assert db.app_runtime_state.rows["billing.receipt_retry"] == {
        "last_run_at": "2026-05-06T12:00:00+00:00"
    }
    assert "billing.monobank_receipt_retry" not in db.app_runtime_state.rows
    assert notifications[0].telegram_user_id == 9001
    assert notifications[0].delivery_kind == "billing_receipt_admin_alert"
    assert notifications[0].delivery_id == 1
    assert "Проблема видачі чека оплати" in notifications[0].screen.text
    assert "Проблема видачі чека Monobank" not in notifications[0].screen.text
    assert db.billing.receipt_admin_alerted == []


def test_process_due_receipt_retries_respects_legacy_runtime_state_key_without_task_log() -> None:
    db = FakeDatabase(make_payment())
    db.billing.success_receipt_retry_payments = [make_payment()]
    db.app_settings.value = {"receipt_retry_interval_seconds": 60}
    db.app_runtime_state.rows["billing.monobank_receipt_retry"] = {
        "last_run_at": datetime(2026, 5, 6, 11, 59, 30, tzinfo=UTC).isoformat()
    }
    monobank_client = FakeMonobankClient(
        receipt_error=RuntimeError("should not call receipt"),
        fiscal_error=RuntimeError("should not call fiscal"),
    )
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    summary = service.process_due_receipt_retries(limit=10)

    assert summary == {"skipped": True, "reason": "not_due"}
    assert db.task_logs.created == []
    assert db.billing.receipts == []
    assert monobank_client.receipt_calls == []
    assert monobank_client.fiscal_calls == []
    assert "billing.receipt_retry" not in db.app_runtime_state.rows


def test_process_due_receipt_retries_does_not_refetch_exhausted_receipts() -> None:
    db = FakeDatabase(make_payment())
    db.billing.notifications = []
    db.billing.success_receipt_retry_payments = [make_payment()]
    db.billing.receipts.extend(
        [
            {
                "id": 1,
                "payment_id": 7,
                "receipt_type": "receipt",
                "status": "unavailable",
                "retry_count": 1,
                "payload_json": {"reason": "monobank_receipt_file_missing"},
            },
            {
                "id": 2,
                "payment_id": 7,
                "receipt_type": "fiscal_check",
                "status": "unavailable",
                "retry_count": 1,
                "payload_json": {"reason": "monobank_fiscal_checks_empty"},
            },
        ]
    )
    db.app_settings.value = {"receipt_retry_max_attempts": 1, "receipt_retry_interval_seconds": 60}
    monobank_client = FakeMonobankClient(
        receipt_error=RuntimeError("should not call receipt"),
        fiscal_error=RuntimeError("should not call fiscal"),
    )
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    summary = service.process_due_receipt_retries(limit=10)

    assert summary["exhausted_count"] == 1
    assert monobank_client.receipt_calls == []
    assert monobank_client.fiscal_calls == []


def test_done_receipt_without_deliverable_artifact_is_retried() -> None:
    db = FakeDatabase(make_payment())
    db.billing.receipts.append(
        {
            "id": 1,
            "payment_id": 7,
            "receipt_type": "fiscal_check",
            "status": "done",
            "tax_url": None,
            "file_base64": None,
            "payload_json": {},
        }
    )
    monobank_client = FakeMonobankClient()
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    service.receipt_retrieval.ensure_success_receipts(make_payment())

    assert monobank_client.fiscal_calls == ["p2_demo"]


def test_invalid_fiscal_check_file_base64_is_not_deliverable() -> None:
    db = FakeDatabase(make_payment())
    monobank_client = FakeMonobankClient()
    monobank_client.get_fiscal_checks = lambda invoice_id, audit_context: {  # type: ignore[method-assign]
        "checks": [{"id": "check-1", "status": "done", "file": "not-base64"}]
    }
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    service.receipt_retrieval.ensure_success_receipts(make_payment())
    notifications = service.dispatch_due_billing_notifications()

    assert len(notifications) == 1
    assert all(document.filename != "billing_receipt_1.pdf" for document in notifications[0].screen.documents)
    assert any(
        row["receipt_type"] == "fiscal_check"
        and row["status"] == "unavailable"
        for row in db.billing.receipts
    )
    assert db.billing.notifications[0]["receipt_ids"] == []


def test_checkbox_fiscal_check_id_is_enough_for_public_receipt_link() -> None:
    db = FakeDatabase(make_payment())
    monobank_client = FakeMonobankClient()
    monobank_client.get_fiscal_checks = lambda invoice_id, audit_context: {  # type: ignore[method-assign]
        "checks": [
            {
                "id": "55a1d9f7-7475-4088-86d2-2132c2261e71",
                "type": "sale",
                "status": "new",
                "fiscalizationSource": "checkbox",
            }
        ]
    }
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    service.receipt_retrieval.ensure_success_receipts(make_payment())

    assert db.billing.receipts[0]["status"] == "done"
    assert db.billing.receipts[0]["tax_url"] == (
        "https://check.checkbox.ua/55a1d9f7-7475-4088-86d2-2132c2261e71"
    )
    assert db.billing.receipts[0]["bot_delivery_status"] == "sent"


def test_existing_checkbox_fiscal_check_id_does_not_refetch_receipt() -> None:
    db = FakeDatabase(make_payment())
    db.billing.receipts.append(
        {
            "id": 1,
            "payment_id": 7,
            "receipt_type": "fiscal_check",
            "status": "new",
            "provider_check_id": "55a1d9f7-7475-4088-86d2-2132c2261e71",
            "fiscalization_source": "checkbox",
            "tax_url": None,
            "file_base64": None,
            "retry_count": 0,
            "payload_json": {},
        }
    )
    monobank_client = FakeMonobankClient(fiscal_error=RuntimeError("should not refetch"))
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    receipts = service.receipt_retrieval.ensure_success_receipts(make_payment())

    assert receipts == db.billing.receipts
    assert monobank_client.fiscal_calls == []


def test_existing_checkbox_without_provider_check_id_is_not_final() -> None:
    db = FakeDatabase(make_payment())
    db.billing.receipts.append(
        {
            "id": 1,
            "payment_id": 7,
            "receipt_type": "fiscal_check",
            "status": "new",
            "provider_check_id": None,
            "fiscalization_source": "checkbox",
            "tax_url": None,
            "file_base64": None,
            "retry_count": 0,
            "payload_json": {},
        }
    )
    monobank_client = FakeMonobankClient()

    def get_fiscal_checks(invoice_id, audit_context):  # type: ignore[no-untyped-def]
        monobank_client.fiscal_calls.append(invoice_id)
        return {
            "checks": [
                {
                    "id": "55a1d9f7-7475-4088-86d2-2132c2261e71",
                    "type": "sale",
                    "status": "new",
                    "fiscalizationSource": "checkbox",
                }
            ]
        }

    monobank_client.get_fiscal_checks = get_fiscal_checks  # type: ignore[method-assign]
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    service.receipt_retrieval.ensure_success_receipts(make_payment())

    assert monobank_client.fiscal_calls == ["p2_demo"]
    assert db.billing.receipts[-1]["provider_check_id"] == "55a1d9f7-7475-4088-86d2-2132c2261e71"


def test_empty_fiscal_checks_payload_creates_retryable_receipt_row() -> None:
    db = FakeDatabase(make_payment())
    monobank_client = FakeMonobankClient()
    monobank_client.get_fiscal_checks = lambda invoice_id, audit_context: {"checks": []}  # type: ignore[method-assign]
    service = build_billing_bot_notification_service(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    service.receipt_retrieval.ensure_success_receipts(make_payment())

    assert any(
        row["receipt_type"] == "fiscal_check"
        and row["status"] == "unavailable"
        and row["payload_json"]["reason"] == "monobank_fiscal_checks_empty"
        for row in db.billing.receipts
    )
