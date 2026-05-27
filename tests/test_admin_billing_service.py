from __future__ import annotations

import pytest

from app.application.admin.billing.errors import (
    AdminBillingAuditLogNotFoundError,
    AdminBillingPaymentNotFoundError,
    AdminBillingReadAccessDeniedError,
    AdminBillingReadValidationError,
)
from app.application.admin.billing.read_service import AdminBillingReadService

ACTOR = {"telegram_user_id": 1, "acl_group_title": "admin"}


class FakeAclPermissions:
    def __init__(self, disabled_actions: set[str] | None = None) -> None:
        self.disabled_actions = disabled_actions or set()

    def get_effective_rule(self, *, group_title, action, environment):
        if action in self.disabled_actions:
            return "disabled"
        return "enabled"


class FakeBillingRepository:
    def __init__(self) -> None:
        self.payment_params = None
        self.audit_params = None

    def list_admin_payments(self, **kwargs):
        self.payment_params = kwargs
        return {"items": [], "page": kwargs["page"], "page_size": kwargs["page_size"], "total": 0, "pages": 0}

    def get_admin_payment_detail(self, payment_id):
        if payment_id == 404:
            return None
        return {"payment": {"id": payment_id}, "events": [], "receipts": [], "offer_acceptances": [], "monobank_audit_logs": []}

    def list_admin_monobank_audit_logs(self, **kwargs):
        self.audit_params = kwargs
        return {"items": [], "page": kwargs["page"], "page_size": kwargs["page_size"], "total": 0, "pages": 0}

    def get_admin_monobank_audit_log_detail(self, audit_log_id):
        if audit_log_id == 404:
            return None
        return {"id": audit_log_id}


class FakeDb:
    def __init__(self, disabled_actions: set[str] | None = None) -> None:
        self.acl_permissions = FakeAclPermissions(disabled_actions=disabled_actions)
        self.billing = FakeBillingRepository()


def test_admin_billing_service_validates_payment_filters() -> None:
    db = FakeDb()
    service = AdminBillingReadService(db)

    result = service.list_payments(
        actor=ACTOR,
        params={
            "page": 2,
            "page_size": 100,
            "status": ["success"],
            "provider_mode": ["test"],
            "search": "order",
            "user_id": "00000000-0000-0000-0000-000000000042",
        }
    )

    assert result["page"] == 2
    assert db.billing.payment_params["status"] == ["success"]
    assert db.billing.payment_params["provider_mode"] == ["test"]


def test_admin_billing_service_rejects_unknown_status() -> None:
    service = AdminBillingReadService(FakeDb())

    with pytest.raises(AdminBillingReadValidationError) as error:
        service.list_payments(actor=ACTOR, params={"page": 1, "page_size": 50, "status": ["paid"]})

    assert "status contains unsupported value" in error.value.detail


def test_admin_billing_service_rejects_invalid_user_uuid() -> None:
    service = AdminBillingReadService(FakeDb())

    with pytest.raises(AdminBillingReadValidationError) as error:
        service.list_payments(actor=ACTOR, params={"page": 1, "page_size": 50, "user_id": "not-a-uuid"})

    assert error.value.detail == "user_id must be a valid UUID"


@pytest.mark.parametrize("mode", ["payments", "audit_logs"])
def test_admin_billing_service_rejects_invalid_pagination(mode: str) -> None:
    service = AdminBillingReadService(FakeDb())

    with pytest.raises(AdminBillingReadValidationError) as error:
        if mode == "payments":
            service.list_payments(actor=ACTOR, params={"page": "1", "page_size": "25"})
        else:
            service.list_monobank_audit_logs(actor=ACTOR, params={"page": "1", "page_size": "25"})

    assert "page_size" in error.value.detail


def test_admin_billing_service_validates_audit_filters() -> None:
    db = FakeDb()
    service = AdminBillingReadService(db)

    service.list_monobank_audit_logs(
        actor=ACTOR,
        params={
            "page": 1,
            "page_size": 50,
            "direction": ["incoming"],
            "provider_mode": ["unknown"],
            "payment_id": 42,
            "invoice_id": "invoice",
            "search": "webhook",
        }
    )

    assert db.billing.audit_params["direction"] == ["incoming"]
    assert db.billing.audit_params["provider_mode"] == ["unknown"]
    assert db.billing.audit_params["payment_id"] == 42


def test_admin_billing_service_rejects_invalid_audit_payment_id() -> None:
    service = AdminBillingReadService(FakeDb())

    with pytest.raises(AdminBillingReadValidationError) as error:
        service.list_monobank_audit_logs(actor=ACTOR, params={"page": 1, "page_size": 50, "payment_id": "bad"})

    assert error.value.detail == "payment_id must be a positive integer"


def test_admin_billing_service_raises_for_missing_detail() -> None:
    service = AdminBillingReadService(FakeDb())

    with pytest.raises(AdminBillingPaymentNotFoundError) as payment_error:
        service.get_payment_detail(actor=ACTOR, payment_id=404)
    with pytest.raises(AdminBillingAuditLogNotFoundError) as audit_error:
        service.get_monobank_audit_log_detail(actor=ACTOR, audit_log_id=404)

    assert payment_error.value.detail == "Billing payment not found"
    assert audit_error.value.detail == "Monobank audit log not found"


@pytest.mark.parametrize("mode", ["payments", "payment_detail", "audit_logs", "audit_detail"])
def test_admin_billing_service_preserves_denied_acl_detail_before_validation(mode: str) -> None:
    service = AdminBillingReadService(FakeDb(disabled_actions={"settings/view"}))

    with pytest.raises(AdminBillingReadAccessDeniedError) as error:
        if mode == "payments":
            service.list_payments(actor=ACTOR, params={"page": 1, "page_size": 50, "status": ["paid"]})
        elif mode == "payment_detail":
            service.get_payment_detail(actor=ACTOR, payment_id=404)
        elif mode == "audit_logs":
            service.list_monobank_audit_logs(actor=ACTOR, params={"page": 1, "page_size": 50, "payment_id": "bad"})
        else:
            service.get_monobank_audit_log_detail(actor=ACTOR, audit_log_id=404)

    assert error.value.detail == "Access denied"
