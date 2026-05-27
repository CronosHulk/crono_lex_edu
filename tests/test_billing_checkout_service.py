from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

import app.billing.services.checkout_provider_config as provider_config_module
from app.billing.providers.instant.provider import InstantPaymentProvider
from app.billing.runtime_settings import (
    BILLING_RUNTIME_SETTINGS_KEY,
    DEFAULT_BILLING_RUNTIME_SETTINGS,
)
from app.billing.services.checkout_service import (
    PAYMENT_TERMINAL_MAINTENANCE_DETAIL,
    BillingCheckoutMaintenanceError,
    BillingCheckoutProfileNotFoundError,
    BillingCheckoutProviderUnavailableError,
    BillingCheckoutService,
    BillingCheckoutValidationError,
    format_amount_minor_as_uah,
    is_payment_terminal_maintenance_time,
    normalize_source_path,
)
from app.billing.services.provider_port import (
    BillingProviderAuditContext,
    BillingProviderInvoiceCreateRequest,
    BillingProviderInvoiceCreateResult,
)

USER_UUID = "11111111-1111-4111-8111-111111111111"


class FakeTimeService:
    def __init__(self, current_time: datetime | None = None) -> None:
        self.current_time = current_time or datetime(2026, 5, 6, 12, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current_time


class FakeProfiles:
    def get_profile(self, telegram_user_id: int) -> dict[str, object] | None:
        if telegram_user_id != 42:
            return None
        return {"telegram_user_id": 42, "user_uuid": USER_UUID}


class FakeSubscriptions:
    def __init__(self) -> None:
        self.row: dict[str, object] | None = None

    def get_by_user_uuid(self, user_uuid: str) -> dict[str, object] | None:
        if str(user_uuid) != USER_UUID:
            return None
        return self.row


class FakeAppSettings:
    def __init__(self, value: dict[str, object] | None = None) -> None:
        self.value = value

    def get_value(self, key: str) -> dict[str, object] | None:
        if key != BILLING_RUNTIME_SETTINGS_KEY:
            return None
        return self.value


class FakeBillingRepository:
    def __init__(self) -> None:
        self.payments: list[dict[str, object]] = []
        self.acceptances: list[dict[str, object]] = []
        self.events: list[dict[str, object]] = []
        self.purchases: list[dict[str, object]] = []
        self.receipts: list[dict[str, object]] = []

    def create_payment(self, **kwargs) -> dict[str, object]:
        row = {
            "id": len(self.payments) + 1,
            "status": "created",
            "provider": "monobank",
            "provider_invoice_id": None,
            "checkout_url": None,
            "failure_code": None,
            "failure_reason": None,
            "provider_status_json": {},
            "paid_at": None,
            "currency": 980,
            **kwargs,
        }
        self.payments.append(row)
        return dict(row)

    def mark_payment_invoice_created(self, payment_id: int, **kwargs) -> dict[str, object] | None:
        row = self.payments[payment_id - 1]
        row.update(
            {
                "status": "invoice_created",
                "provider_invoice_id": kwargs["provider_invoice_id"],
                "checkout_url": kwargs["checkout_url"],
                "provider_status_json": kwargs["provider_status_json"],
                "updated": kwargs["current_time"],
            }
        )
        return dict(row)

    def update_payment_return_url(self, payment_id: int, **kwargs) -> dict[str, object] | None:
        row = self.payments[payment_id - 1]
        row.update(
            {
                "return_url": kwargs["return_url"],
                "updated": kwargs["current_time"],
            }
        )
        return dict(row)

    def update_payment_provider_status(self, payment_id: int, **kwargs) -> dict[str, object] | None:
        row = self.payments[payment_id - 1]
        row.update(
            {
                "status": kwargs["status"],
                "provider_status_json": kwargs["provider_status_json"],
                "failure_code": kwargs["failure_code"],
                "failure_reason": kwargs["failure_reason"],
                "updated": kwargs["current_time"],
            }
        )
        return dict(row)

    def create_payment_event(self, **kwargs) -> dict[str, object]:
        row = {"id": len(self.events) + 1, **kwargs}
        self.events.append(row)
        return dict(row)

    def create_offer_acceptance(self, **kwargs) -> dict[str, object]:
        row = {"id": len(self.acceptances) + 1, **kwargs}
        self.acceptances.append(row)
        return dict(row)

    def apply_subscription_purchase_for_payment(
        self,
        payment: dict[str, object],
        *,
        current_time: datetime,
    ) -> dict[str, object]:
        purchase = {
            "id": len(self.purchases) + 1,
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
        self.purchases.append(purchase)
        return {
            "purchase": dict(purchase),
            "subscription": {
                "user_uuid": payment["user_uuid"],
                "plan_key": payment["plan_key"],
                "start": current_time,
                "end": current_time,
            },
        }

    def reverse_subscription_purchase_projection_for_payment(
        self,
        payment_id: int,
        *,
        current_time: datetime,
    ) -> None:
        _ = (payment_id, current_time)
        return None

    def list_payment_receipts(self, payment_id: int):
        return [dict(row) for row in self.receipts if row["payment_id"] == payment_id]

    def create_receipt(self, **kwargs):
        row = {"id": len(self.receipts) + 1, **kwargs}
        self.receipts.append(row)
        return dict(row)


class FakeDatabase:
    def __init__(self, billing_settings: dict[str, object] | None = None) -> None:
        self.settings = SimpleNamespace(
            app_api_base_url="https://api.example",
            app_web_base_url="https://web.example",
            monobank_token_test="test-token",
            monobank_token="production-token",
        )
        self.app_settings = FakeAppSettings(billing_settings)
        self.user_profiles = FakeProfiles()
        self.subscriptions = FakeSubscriptions()
        self.billing = FakeBillingRepository()


class FakeMonobankClient:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self.error = error

    def create_invoice(self, request, *, audit_context):
        self.calls.append({"request": request, "audit_context": audit_context})
        if self.error is not None:
            raise self.error
        return BillingProviderInvoiceCreateResult(
            provider_invoice_id="p2_demo",
            checkout_url="https://pay.example/p2_demo",
            payload={"invoiceId": "p2_demo", "pageUrl": "https://pay.example/p2_demo"},
        )


class FakeBillingProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_invoice(self, request, *, audit_context):
        self.calls.append({"request": request, "audit_context": audit_context})
        return BillingProviderInvoiceCreateResult(
            provider_invoice_id="p2_provider",
            checkout_url="https://pay.example/p2_provider",
            payload={"invoiceId": "p2_provider", "pageUrl": "https://pay.example/p2_provider"},
        )


class FakeProviderAPIError(Exception):
    def __init__(self, message: str, *, status_code: int, error_code: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


def billing_settings(**overrides) -> dict[str, object]:
    value = {
        **DEFAULT_BILLING_RUNTIME_SETTINGS,
        "monobank_mode": "test",
        "offer_text": "CronoLex paid subscription offer text for tests.",
    }
    value.update(overrides)
    return value


def monobank_provider_factory(provider: object):
    def factory(provider_key: str, provider_mode: str):
        _ = (provider_key, provider_mode)
        return provider

    return factory


def test_get_offer_returns_text_hash_and_version() -> None:
    service = BillingCheckoutService(FakeDatabase(billing_settings()), FakeTimeService())

    payload = service.get_offer()

    assert payload["offer_text"] == "CronoLex paid subscription offer text for tests."
    assert len(payload["offer_text_hash"]) == 64
    assert payload["offer_version"] == payload["offer_text_hash"][:16]


def test_format_amount_minor_as_uah_preserves_fractional_hryvnia() -> None:
    assert format_amount_minor_as_uah(1000) == 10
    assert format_amount_minor_as_uah(1055) == 10.55


@pytest.mark.parametrize(
    ("current_time", "expected"),
    [
        (datetime(2026, 5, 6, 20, 29, tzinfo=UTC), False),
        (datetime(2026, 5, 6, 20, 30, tzinfo=UTC), True),
        (datetime(2026, 5, 6, 21, 29, tzinfo=UTC), True),
        (datetime(2026, 5, 6, 21, 30, tzinfo=UTC), False),
    ],
)
def test_payment_terminal_maintenance_window_uses_kyiv_time(current_time: datetime, expected: bool) -> None:
    assert is_payment_terminal_maintenance_time(current_time, "monobank") is expected


def test_create_checkout_creates_payment_acceptance_and_monobank_invoice() -> None:
    db = FakeDatabase(billing_settings(billing_provider="monobank"))
    monobank_client = FakeMonobankClient()
    service = BillingCheckoutService(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    payload = service.create_checkout(
        {"telegram_user_id": 42},
        plan_key="premium",
        period_months=1,
        offer_accepted=True,
        offer_text_hash=service.get_offer()["offer_text_hash"],
        source_path="/learning",
        request_ip="127.0.0.1",
        user_agent="pytest",
    )

    assert payload["payment"]["status"] == "invoice_created"
    assert "provider_invoice_id" not in payload["payment"]
    assert "provider_reference" not in payload["payment"]
    assert "provider_mode" not in payload["payment"]
    assert "checkout_url" not in payload["payment"]
    assert payload["checkout"] == {"page_url": "https://pay.example/p2_demo"}
    assert payload["order"]["plan_key"] == "premium"
    assert payload["order"]["period_months"] == 1
    assert payload["order"]["amount_minor"] == 1000
    assert payload["order"]["amount_uah"] == 10
    assert payload["order"]["currency"] == 980
    assert payload["order"]["quote"]["kind"] == "subscription"
    assert db.billing.payments[0]["source_path"] == "/learning"
    assert db.billing.acceptances[0]["payment_id"] == 1
    assert db.billing.acceptances[0]["accepted_ip"] == "127.0.0.1"
    invoice_request = monobank_client.calls[0]["request"]
    audit_context = monobank_client.calls[0]["audit_context"]
    assert type(invoice_request) is BillingProviderInvoiceCreateRequest
    assert type(audit_context) is BillingProviderAuditContext
    assert audit_context.source_place == "checkout"
    assert audit_context.actor_user_uuid == USER_UUID
    assert audit_context.telegram_user_id == 42
    assert audit_context.payment_id == 1
    assert audit_context.request_ip == "127.0.0.1"
    assert invoice_request.amount_minor == 1000
    assert db.billing.payments[0]["return_url"] == "https://web.example/plans?payment_id=1&check_payment=true"
    assert invoice_request.redirect_url == "https://web.example/plans?payment_id=1&check_payment=true"
    assert invoice_request.webhook_url == "https://api.example/api/v1/billing/monobank/webhook"
    assert invoice_request.destination == "Підписка CronoLex Premium на 1 міс."
    assert invoice_request.lines[0].name == "Підписка CronoLex Premium на 1 міс."
    assert invoice_request.lines[0].icon_url == (
        "https://web.example/billing/premium-crown.svg"
    )
    assert invoice_request.comment == "Користувач: 42; платіж: 1"
    assert invoice_request.reference.startswith("clx-")


def test_create_checkout_sends_neutral_invoice_request_and_persists_provider() -> None:
    db = FakeDatabase(billing_settings(billing_provider="monobank"))
    provider = FakeBillingProvider()
    factory_calls: list[dict[str, object]] = []

    def billing_provider_factory(**kwargs):
        factory_calls.append(kwargs)
        return provider

    service = BillingCheckoutService(
        db,
        FakeTimeService(),
        billing_provider_factory=billing_provider_factory,
    )

    payload = service.create_checkout(
        {"telegram_user_id": 42},
        plan_key="premium",
        period_months=1,
        offer_accepted=True,
        offer_text_hash=service.get_offer()["offer_text_hash"],
        source_path="/plans",
        request_ip="127.0.0.1",
        user_agent="pytest",
    )

    assert factory_calls == [{"provider_key": "monobank", "provider_mode": "test"}]
    assert db.billing.payments[0]["provider"] == "monobank"
    assert db.billing.payments[0]["provider_mode"] == "test"
    assert payload["checkout"] == {"page_url": "https://pay.example/p2_provider"}
    assert db.billing.payments[0]["provider_invoice_id"] == "p2_provider"
    invoice_request = provider.calls[0]["request"]
    audit_context = provider.calls[0]["audit_context"]
    assert type(invoice_request) is BillingProviderInvoiceCreateRequest
    assert type(audit_context) is BillingProviderAuditContext
    assert audit_context.source_place == "checkout"
    assert audit_context.actor_user_uuid == USER_UUID
    assert audit_context.telegram_user_id == 42
    assert audit_context.payment_id == 1
    assert audit_context.request_ip == "127.0.0.1"
    assert invoice_request.amount_minor == 1000
    assert invoice_request.currency == 980
    assert invoice_request.reference == db.billing.payments[0]["provider_reference"]
    assert invoice_request.destination == "Підписка CronoLex Premium на 1 міс."
    assert invoice_request.redirect_url == "https://web.example/plans?payment_id=1&check_payment=true"
    assert invoice_request.webhook_url == "https://api.example/api/v1/billing/monobank/webhook"
    assert invoice_request.validity_seconds == 3600
    assert invoice_request.lines[0].code == "premium"
    assert invoice_request.lines[0].amount_minor == 1000
    assert invoice_request.lines[0].icon_url == "https://web.example/billing/premium-crown.svg"


def test_create_checkout_default_instant_provider_marks_payment_success_immediately() -> None:
    db = FakeDatabase(billing_settings(monobank_mode="disabled"))
    factory_calls: list[dict[str, str]] = []

    def billing_provider_factory(provider_key: str, provider_mode: str):
        factory_calls.append({"provider_key": provider_key, "provider_mode": provider_mode})
        return InstantPaymentProvider()

    service = BillingCheckoutService(
        db,
        FakeTimeService(),
        billing_provider_factory=billing_provider_factory,
    )

    payload = service.create_checkout(
        {"telegram_user_id": 42},
        plan_key="premium",
        period_months=1,
        offer_accepted=True,
        offer_text_hash=service.get_offer()["offer_text_hash"],
        source_path="/plans",
        request_ip="127.0.0.1",
        user_agent="pytest",
    )

    assert payload["payment"]["status"] == "success"
    assert payload["checkout"]["page_url"] == "https://web.example/plans?payment_id=1&check_payment=true"
    assert db.billing.payments[0]["provider"] == "instant"
    assert db.billing.payments[0]["status"] == "success"
    assert factory_calls[0] == {"provider_key": "instant", "provider_mode": "instant"}
    assert db.billing.events[0]["event_type"] == "terminal_status"
    assert db.billing.events[1]["event_type"] == "subscription_activated"


def test_create_checkout_default_instant_provider_ignores_missing_monobank_tokens() -> None:
    db = FakeDatabase(billing_settings(monobank_mode="disabled"))
    db.settings.monobank_token = ""
    db.settings.monobank_token_test = ""
    factory_calls: list[dict[str, str]] = []

    def billing_provider_factory(provider_key: str, provider_mode: str):
        factory_calls.append({"provider_key": provider_key, "provider_mode": provider_mode})
        return InstantPaymentProvider()

    service = BillingCheckoutService(
        db,
        FakeTimeService(),
        billing_provider_factory=billing_provider_factory,
    )

    payload = service.create_checkout(
        {"telegram_user_id": 42},
        plan_key="premium",
        period_months=1,
        offer_accepted=True,
        offer_text_hash=service.get_offer()["offer_text_hash"],
        source_path="/plans",
        request_ip=None,
        user_agent=None,
    )

    assert payload["payment"]["status"] == "success"
    assert db.billing.payments[0]["provider"] == "instant"
    assert factory_calls[0] == {"provider_key": "instant", "provider_mode": "instant"}


def test_create_checkout_default_instant_provider_queues_post_upgrade_rescan_on_success() -> None:
    db = FakeDatabase(billing_settings(monobank_mode="disabled"))
    rescan_calls: list[dict[str, object]] = []

    service = BillingCheckoutService(
        db,
        FakeTimeService(),
        billing_provider_factory=lambda provider_key, provider_mode: InstantPaymentProvider(),
        post_upgrade_rescan=lambda **kwargs: rescan_calls.append(dict(kwargs)) or {"status": "queued", "task_log_id": 10},
    )

    payload = service.create_checkout(
        {"telegram_user_id": 42},
        plan_key="premium",
        period_months=1,
        offer_accepted=True,
        offer_text_hash=service.get_offer()["offer_text_hash"],
        source_path="/plans",
        request_ip=None,
        user_agent=None,
    )

    assert payload["payment"]["status"] == "success"
    assert rescan_calls == [
        {
            "telegram_user_id": 42,
            "user_uuid": USER_UUID,
            "current_time": FakeTimeService().current_time,
        }
    ]
    queued_events = [
        row
        for row in db.billing.events
        if row["event_type"] == "post_upgrade_google_doc_rescan_queued"
    ]
    assert len(queued_events) == 1
    assert queued_events[0]["source"] == "checkout"
    assert queued_events[0]["payload_json"] == {"status": "queued", "task_log_id": 10}


def test_create_checkout_marks_double_time_support_promotion_in_quote() -> None:
    db = FakeDatabase(
        billing_settings(
            billing_provider="monobank",
            double_time_for_project_support_enabled=True,
        )
    )
    monobank_client = FakeMonobankClient()
    service = BillingCheckoutService(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    payload = service.create_checkout(
        {"telegram_user_id": 42},
        plan_key="premium",
        period_months=3,
        offer_accepted=True,
        offer_text_hash=service.get_offer()["offer_text_hash"],
        source_path="/plans",
        request_ip=None,
        user_agent=None,
    )

    quote = payload["order"]["quote"]
    assert payload["order"]["period_months"] == 3
    assert quote["period_months"] == 3
    assert quote["granted_period_months"] == 6
    assert quote["promotion"] == {
        "key": "double_time_for_project_support",
        "label": "Двойное время за поддержку проекта",
        "period_multiplier": 2,
    }
    assert db.billing.payments[0]["provider_status_json"]["checkout_quote"]["granted_period_months"] == 6
    assert db.billing.payments[0]["period_months"] == 3


def test_create_checkout_rejects_payment_terminal_maintenance_before_payment_write() -> None:
    db = FakeDatabase(billing_settings(billing_provider="monobank"))
    monobank_client = FakeMonobankClient()
    service = BillingCheckoutService(
        db,
        FakeTimeService(datetime(2026, 5, 6, 20, 45, tzinfo=UTC)),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    with pytest.raises(BillingCheckoutMaintenanceError) as error:
        service.create_checkout(
            {"telegram_user_id": 42},
            plan_key="premium",
            period_months=1,
            offer_accepted=True,
            offer_text_hash=service.get_offer()["offer_text_hash"],
            source_path="/plans",
            request_ip=None,
            user_agent=None,
        )

    assert error.value.detail == PAYMENT_TERMINAL_MAINTENANCE_DETAIL
    assert db.billing.payments == []
    assert monobank_client.calls == []


def test_create_checkout_allows_instant_provider_during_payment_terminal_maintenance() -> None:
    db = FakeDatabase(billing_settings(billing_provider="instant", monobank_mode="disabled"))
    factory_calls: list[dict[str, str]] = []

    def billing_provider_factory(provider_key: str, provider_mode: str):
        factory_calls.append({"provider_key": provider_key, "provider_mode": provider_mode})
        return InstantPaymentProvider()

    service = BillingCheckoutService(
        db,
        FakeTimeService(datetime(2026, 5, 6, 20, 45, tzinfo=UTC)),
        billing_provider_factory=billing_provider_factory,
    )

    payload = service.create_checkout(
        {"telegram_user_id": 42},
        plan_key="premium",
        period_months=1,
        offer_accepted=True,
        offer_text_hash=service.get_offer()["offer_text_hash"],
        source_path="/plans",
        request_ip=None,
        user_agent=None,
    )

    assert payload["payment"]["status"] == "success"
    assert payload["checkout"]["page_url"] == "https://web.example/plans?payment_id=1&check_payment=true"
    assert db.billing.payments[0]["provider"] == "instant"
    assert db.billing.payments[0]["status"] == "success"
    assert factory_calls[0] == {"provider_key": "instant", "provider_mode": "instant"}


def test_create_checkout_rejects_maintenance_before_missing_production_token() -> None:
    db = FakeDatabase(billing_settings(billing_provider="monobank", monobank_mode="production"))
    db.settings.monobank_token = ""
    service = BillingCheckoutService(db, FakeTimeService(datetime(2026, 5, 6, 20, 45, tzinfo=UTC)))

    with pytest.raises(BillingCheckoutMaintenanceError) as error:
        service.create_checkout(
            {"telegram_user_id": 42},
            plan_key="premium",
            period_months=1,
            offer_accepted=True,
            offer_text_hash=service.get_offer()["offer_text_hash"],
            source_path="/plans",
            request_ip=None,
            user_agent=None,
        )

    assert error.value.detail == PAYMENT_TERMINAL_MAINTENANCE_DETAIL
    assert db.billing.payments == []


def test_create_checkout_rejects_downgrade_from_active_premium_plus_before_payment_write() -> None:
    db = FakeDatabase(billing_settings())
    db.subscriptions.row = {
        "plan_key": "premium_plus",
        "end": datetime(2026, 5, 20, 12, tzinfo=UTC),
    }
    service = BillingCheckoutService(db, FakeTimeService())

    with pytest.raises(BillingCheckoutValidationError) as error:
        service.create_checkout(
            {"telegram_user_id": 42},
            plan_key="premium",
            period_months=1,
            offer_accepted=True,
            offer_text_hash=service.get_offer()["offer_text_hash"],
            source_path="/plans",
            request_ip=None,
            user_agent=None,
        )

    assert "current paid period" in str(error.value.detail)
    assert db.billing.payments == []


def test_create_checkout_rejects_premium_plus_when_checkout_disabled() -> None:
    db = FakeDatabase(
        billing_settings(
            billing_provider="monobank",
            premium_plus_checkout_enabled=False,
        )
    )
    monobank_client = FakeMonobankClient()
    service = BillingCheckoutService(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    with pytest.raises(BillingCheckoutValidationError) as error:
        service.create_checkout(
            {"telegram_user_id": 42},
            plan_key="premium_plus",
            period_months=1,
            offer_accepted=True,
            offer_text_hash=service.get_offer()["offer_text_hash"],
            source_path="/plans",
            request_ip=None,
            user_agent=None,
        )

    assert error.value.detail == "Premium+ checkout is disabled"
    assert db.billing.payments == []
    assert monobank_client.calls == []


def test_create_checkout_rejects_period_unsupported_by_provider_before_payment_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        provider_config_module,
        "MONOBANK_SUPPORTED_PERIOD_MONTHS",
        (1, 3),
    )
    db = FakeDatabase(
        billing_settings(
            billing_provider="monobank",
            enabled_period_months=[1, 6],
        )
    )
    monobank_client = FakeMonobankClient()
    service = BillingCheckoutService(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    with pytest.raises(BillingCheckoutValidationError) as error:
        service.create_checkout(
            {"telegram_user_id": 42},
            plan_key="premium",
            period_months=6,
            offer_accepted=True,
            offer_text_hash=service.get_offer()["offer_text_hash"],
            source_path="/plans",
            request_ip=None,
            user_agent=None,
        )

    assert error.value.detail == "Unsupported billing period"
    assert db.billing.payments == []
    assert monobank_client.calls == []


def test_create_checkout_charges_prorated_upgrade_remainder() -> None:
    db = FakeDatabase(billing_settings(billing_provider="monobank"))
    db.subscriptions.row = {
        "plan_key": "premium",
        "start": datetime(2026, 5, 1, 12, tzinfo=UTC),
        "end": datetime(2026, 5, 11, 12, tzinfo=UTC),
    }
    monobank_client = FakeMonobankClient()
    service = BillingCheckoutService(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    payload = service.create_checkout(
        {"telegram_user_id": 42},
        plan_key="premium_plus",
        period_months=1,
        offer_accepted=True,
        offer_text_hash=service.get_offer()["offer_text_hash"],
        source_path="/plans",
        request_ip=None,
        user_agent=None,
    )

    assert payload["order"]["amount_minor"] == 500
    assert payload["order"]["quote"]["kind"] == "upgrade"
    assert payload["order"]["quote"]["base_plan_key"] == "premium"
    assert db.billing.payments[0]["amount_minor"] == 500
    invoice_request = monobank_client.calls[0]["request"]
    assert invoice_request.amount_minor == 500
    assert invoice_request.destination == "Доплата за покращення CronoLex Premium до Premium+"
    assert invoice_request.lines[0].icon_url == (
        "https://web.example/billing/premium-plus-crown.svg"
    )


def test_create_checkout_uses_renewal_description_for_current_paid_plan() -> None:
    db = FakeDatabase(billing_settings(billing_provider="monobank"))
    db.subscriptions.row = {
        "plan_key": "premium",
        "start": datetime(2026, 5, 1, 12, tzinfo=UTC),
        "end": datetime(2026, 5, 11, 12, tzinfo=UTC),
    }
    monobank_client = FakeMonobankClient()
    service = BillingCheckoutService(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    payload = service.create_checkout(
        {"telegram_user_id": 42},
        plan_key="premium",
        period_months=1,
        offer_accepted=True,
        offer_text_hash=service.get_offer()["offer_text_hash"],
        source_path="/plans",
        request_ip=None,
        user_agent=None,
    )

    assert payload["order"]["amount_minor"] == 1000
    assert payload["order"]["quote"]["kind"] == "renewal"
    assert payload["order"]["quote"]["period_start"] == "2026-05-11T12:00:00+00:00"
    assert payload["order"]["quote"]["period_end"] == "2026-06-11T12:00:00+00:00"
    invoice_request = monobank_client.calls[0]["request"]
    assert invoice_request.destination == "Продовження підписки CronoLex Premium на 1 міс."
    assert invoice_request.lines[0].name == "Продовження підписки CronoLex Premium на 1 міс."


def test_create_checkout_keeps_discounted_period_price_for_upgrade() -> None:
    settings = billing_settings()
    settings["billing_provider"] = "monobank"
    settings["plan_prices_uah"]["premium_plus"]["12"] = 180
    db = FakeDatabase(settings)
    db.subscriptions.row = {
        "plan_key": "premium",
        "start": datetime(2026, 5, 1, 12, tzinfo=UTC),
        "end": datetime(2026, 5, 11, 12, tzinfo=UTC),
    }
    monobank_client = FakeMonobankClient()
    service = BillingCheckoutService(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    payload = service.create_checkout(
        {"telegram_user_id": 42},
        plan_key="premium_plus",
        period_months=12,
        offer_accepted=True,
        offer_text_hash=service.get_offer()["offer_text_hash"],
        source_path="/plans",
        request_ip=None,
        user_agent=None,
    )

    assert payload["order"]["amount_minor"] == 16500
    assert payload["order"]["quote"]["remainder_amount_minor"] == 500
    assert payload["order"]["quote"]["extension_amount_minor"] == 16000
    assert db.billing.payments[0]["amount_minor"] == 16500
    assert monobank_client.calls[0]["request"].amount_minor == 16500


def test_create_checkout_rejects_disabled_monobank() -> None:
    service = BillingCheckoutService(
        FakeDatabase(billing_settings(billing_provider="monobank", monobank_mode="disabled")),
        FakeTimeService(),
    )

    with pytest.raises(BillingCheckoutValidationError) as error:
        service.create_checkout(
            {"telegram_user_id": 42},
            plan_key="premium",
            period_months=1,
            offer_accepted=True,
            offer_text_hash=service.get_offer()["offer_text_hash"],
            source_path="/plans",
            request_ip=None,
            user_agent=None,
        )

    assert "disabled" in str(error.value.detail)


def test_create_checkout_rejects_missing_offer_acceptance() -> None:
    service = BillingCheckoutService(FakeDatabase(billing_settings()), FakeTimeService())

    with pytest.raises(BillingCheckoutValidationError) as error:
        service.create_checkout(
            {"telegram_user_id": 42},
            plan_key="premium",
            period_months=1,
            offer_accepted=False,
            offer_text_hash=service.get_offer()["offer_text_hash"],
            source_path="/plans",
            request_ip=None,
            user_agent=None,
        )

    assert "offer_accepted" in str(error.value.detail)


def test_create_checkout_rejects_unconfigured_token_before_payment_write() -> None:
    db = FakeDatabase(billing_settings(billing_provider="monobank", monobank_mode="production"))
    db.settings.monobank_token = ""
    service = BillingCheckoutService(db, FakeTimeService())

    with pytest.raises(BillingCheckoutValidationError) as error:
        service.create_checkout(
            {"telegram_user_id": 42},
            plan_key="premium",
            period_months=1,
            offer_accepted=True,
            offer_text_hash=service.get_offer()["offer_text_hash"],
            source_path="/plans",
            request_ip=None,
            user_agent=None,
        )

    assert error.value.detail == "MONOBANK_TOKEN is not configured"
    assert db.billing.payments == []


def test_create_checkout_rejects_stale_offer_hash_before_payment_write() -> None:
    db = FakeDatabase(billing_settings())
    service = BillingCheckoutService(db, FakeTimeService())

    with pytest.raises(BillingCheckoutValidationError) as error:
        service.create_checkout(
            {"telegram_user_id": 42},
            plan_key="premium",
            period_months=1,
            offer_accepted=True,
            offer_text_hash="0" * 64,
            source_path="/plans",
            request_ip=None,
            user_agent=None,
        )

    assert "offer_text_hash" in str(error.value.detail)
    assert db.billing.payments == []


def test_create_checkout_rejects_missing_profile_before_payment_write() -> None:
    db = FakeDatabase(billing_settings())
    service = BillingCheckoutService(db, FakeTimeService())

    with pytest.raises(BillingCheckoutProfileNotFoundError) as error:
        service.create_checkout(
            {"telegram_user_id": 7},
            plan_key="premium",
            period_months=1,
            offer_accepted=True,
            offer_text_hash=service.get_offer()["offer_text_hash"],
            source_path="/plans",
            request_ip=None,
            user_agent=None,
        )

    assert error.value.detail == "User profile not found"
    assert db.billing.payments == []


def test_create_checkout_marks_local_payment_failed_when_invoice_creation_fails() -> None:
    db = FakeDatabase(billing_settings(billing_provider="monobank"))
    monobank_client = FakeMonobankClient(RuntimeError("network timeout"))
    service = BillingCheckoutService(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    with pytest.raises(BillingCheckoutProviderUnavailableError) as error:
        service.create_checkout(
            {"telegram_user_id": 42},
            plan_key="premium",
            period_months=1,
            offer_accepted=True,
            offer_text_hash=service.get_offer()["offer_text_hash"],
            source_path="/plans",
            request_ip="127.0.0.1",
            user_agent=None,
        )

    assert error.value.detail == "Monobank checkout is temporarily unavailable"
    assert db.billing.payments[0]["status"] == "failure"
    assert db.billing.payments[0]["failure_code"] == "checkout_invoice_creation_failed"
    assert db.billing.payments[0]["failure_reason"] == "Monobank checkout is temporarily unavailable"
    assert db.billing.events[0]["event_type"] == "checkout_invoice_creation_failed"
    assert db.billing.events[0]["payload_json"]["error_type"] == "RuntimeError"


def test_create_checkout_marks_local_payment_failed_from_provider_api_error_shape() -> None:
    db = FakeDatabase(billing_settings(billing_provider="monobank"))
    monobank_client = FakeMonobankClient(
        FakeProviderAPIError("invoice rejected", status_code=422, error_code="invoice_rejected")
    )
    service = BillingCheckoutService(
        db,
        FakeTimeService(),
        billing_provider_factory=monobank_provider_factory(monobank_client),
    )

    with pytest.raises(BillingCheckoutProviderUnavailableError):
        service.create_checkout(
            {"telegram_user_id": 42},
            plan_key="premium",
            period_months=1,
            offer_accepted=True,
            offer_text_hash=service.get_offer()["offer_text_hash"],
            source_path="/plans",
            request_ip="127.0.0.1",
            user_agent=None,
        )

    payment = db.billing.payments[0]
    assert payment["status"] == "failure"
    assert payment["provider_status_json"]["provider_status_code"] == 422
    assert payment["provider_status_json"]["provider_error_code"] == "invoice_rejected"
    assert payment["failure_code"] == "invoice_rejected"


def test_normalize_source_path_rejects_non_internal_path() -> None:
    with pytest.raises(BillingCheckoutValidationError) as error:
        normalize_source_path("https://example.test/plans")

    assert error.value.detail == "source_path must be an internal path starting with /"
