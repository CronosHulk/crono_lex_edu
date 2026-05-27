from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.billing.router import build_billing_router
from app.admin_api.context import AdminRouterContext
from app.application.admin.billing.errors import (
    AdminBillingAuditLogNotFoundError,
    AdminBillingPaymentNotFoundError,
    AdminBillingReadAccessDeniedError,
    AdminBillingReadValidationError,
)


class FakeAdminBillingReadService:
    def __init__(self) -> None:
        self.payment_list_calls = []
        self.payment_detail_calls = []
        self.audit_list_calls = []
        self.audit_detail_calls = []

    def list_payments(self, *, actor, params):
        self.payment_list_calls.append({"actor": actor, "params": params})
        return {"actor": actor, "params": params, "payments": []}

    def get_payment_detail(self, *, actor, payment_id):
        self.payment_detail_calls.append({"actor": actor, "payment_id": payment_id})
        return {"actor": actor, "payment_id": payment_id}

    def list_monobank_audit_logs(self, *, actor, params):
        self.audit_list_calls.append({"actor": actor, "params": params})
        return {"actor": actor, "params": params, "audit_logs": []}

    def get_monobank_audit_log_detail(self, *, actor, audit_log_id):
        self.audit_detail_calls.append({"actor": actor, "audit_log_id": audit_log_id})
        return {"actor": actor, "audit_log_id": audit_log_id}


class InvalidPaymentFilterBillingReadService(FakeAdminBillingReadService):
    def list_payments(self, *, actor, params):
        self.payment_list_calls.append({"actor": actor, "params": params})
        raise AdminBillingReadValidationError("user_id must be a valid UUID")


class InvalidAuditFilterBillingReadService(FakeAdminBillingReadService):
    def list_monobank_audit_logs(self, *, actor, params):
        self.audit_list_calls.append({"actor": actor, "params": params})
        raise AdminBillingReadValidationError("payment_id must be a positive integer")


class MissingPaymentBillingReadService(FakeAdminBillingReadService):
    def get_payment_detail(self, *, actor, payment_id):
        self.payment_detail_calls.append({"actor": actor, "payment_id": payment_id})
        raise AdminBillingPaymentNotFoundError()


class MissingAuditLogBillingReadService(FakeAdminBillingReadService):
    def get_monobank_audit_log_detail(self, *, actor, audit_log_id):
        self.audit_detail_calls.append({"actor": actor, "audit_log_id": audit_log_id})
        raise AdminBillingAuditLogNotFoundError()


class AccessDeniedBillingReadService(FakeAdminBillingReadService):
    def list_payments(self, *, actor, params):
        self.payment_list_calls.append({"actor": actor, "params": params})
        raise AdminBillingReadAccessDeniedError("Access denied")


def build_billing_test_client(billing_service, actor) -> TestClient:
    app = FastAPI()
    app.include_router(
        build_billing_router(
            AdminRouterContext(audio_storage_provider=lambda: object(),
                current_admin_user=lambda request: actor,
                admin_ai_usage_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("ai usage service should not be used")
                ),
                admin_auth_service=lambda: (_ for _ in ()).throw(AssertionError("auth service should not be used")),
                admin_billing_read_service=lambda: billing_service,
                admin_bootstrap_service=lambda: (_ for _ in ()).throw(
                    AssertionError("bootstrap service should not be used")
                ),
                admin_dashboard_service=lambda: (_ for _ in ()).throw(
                    AssertionError("dashboard service should not be used")
                ),
                admin_dictionary_action_service=lambda: (_ for _ in ()).throw(
                    AssertionError("dictionary action service should not be used")
                ),
                admin_dictionary_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("dictionary read service should not be used")
                ),
                admin_dictionary_service=lambda: (_ for _ in ()).throw(
                    AssertionError("dictionary service should not be used")
                ),
                admin_entity_service=lambda: (_ for _ in ()).throw(
                    AssertionError("entity service should not be used")
                ),
                admin_exercise_text_service=lambda: (_ for _ in ()).throw(
                    AssertionError("exercise text service should not be used")
                ),
                admin_exercise_text_generation_service=lambda: (_ for _ in ()).throw(
                    AssertionError("exercise text generation service should not be used")
                ),
                admin_exercise_text_tts_service=lambda: (_ for _ in ()).throw(
                    AssertionError("exercise text tts service should not be used")
                ),
                admin_import_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("import read service should not be used")
                ),
                admin_log_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("log read service should not be used")
                ),
                admin_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("read service should not be used")
                ),
                admin_settings_service=lambda: (_ for _ in ()).throw(
                    AssertionError("settings service should not be used")
                ),
                admin_user_dictionary_bulk_action=lambda: (_ for _ in ()).throw(
                    AssertionError("user dictionary bulk action should not be used")
                ),
                admin_user_dictionary_promote_action=lambda: (_ for _ in ()).throw(
                    AssertionError("user dictionary promote action should not be used")
                ),
                admin_user_dictionary_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("user dictionary read service should not be used")
                ),
                admin_user_action_service=lambda: (_ for _ in ()).throw(
                    AssertionError("user action service should not be used")
                ),
                admin_user_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("user read service should not be used")
                ),
            )
        )
    )
    return TestClient(app)


def test_admin_billing_routes_use_billing_service_context_directly() -> None:
    billing_service = FakeAdminBillingReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_billing_test_client(billing_service, actor)

    payments_response = client.get(
        "/billing/payments",
        params={
            "page": 2,
            "page_size": 100,
            "search": "paid",
            "status": ["paid", "pending"],
            "provider_mode": ["production"],
            "user_id": "user-1",
        },
    )
    payment_detail_response = client.get("/billing/payments/7")
    audit_response = client.get(
        "/billing/monobank-audit",
        params={
            "page": 3,
            "page_size": 50,
            "search": "invoice",
            "direction": ["incoming"],
            "provider_mode": ["sandbox"],
            "payment_id": 7,
            "invoice_id": "inv-1",
        },
    )
    audit_detail_response = client.get("/billing/monobank-audit/9")

    assert payments_response.status_code == 200
    assert payments_response.json() == {
        "actor": actor,
        "params": {
            "page": 2,
            "page_size": 100,
            "search": "paid",
            "status": ["paid", "pending"],
            "provider_mode": ["production"],
            "user_id": "user-1",
        },
        "payments": [],
    }
    assert payment_detail_response.status_code == 200
    assert payment_detail_response.json() == {"actor": actor, "payment_id": 7}
    assert audit_response.status_code == 200
    assert audit_response.json() == {
        "actor": actor,
        "params": {
            "page": 3,
            "page_size": 50,
            "search": "invoice",
            "direction": ["incoming"],
            "provider_mode": ["sandbox"],
            "payment_id": 7,
            "invoice_id": "inv-1",
        },
        "audit_logs": [],
    }
    assert audit_detail_response.status_code == 200
    assert audit_detail_response.json() == {"actor": actor, "audit_log_id": 9}
    assert billing_service.payment_list_calls == [
        {
            "actor": actor,
            "params": {
                "page": 2,
                "page_size": 100,
                "search": "paid",
                "status": ["paid", "pending"],
                "provider_mode": ["production"],
                "user_id": "user-1",
            },
        }
    ]
    assert billing_service.payment_detail_calls == [{"actor": actor, "payment_id": 7}]
    assert billing_service.audit_list_calls == [
        {
            "actor": actor,
            "params": {
                "page": 3,
                "page_size": 50,
                "search": "invoice",
                "direction": ["incoming"],
                "provider_mode": ["sandbox"],
                "payment_id": 7,
                "invoice_id": "inv-1",
            },
        }
    ]
    assert billing_service.audit_detail_calls == [{"actor": actor, "audit_log_id": 9}]


def test_admin_billing_router_maps_payment_list_errors() -> None:
    billing_service = InvalidPaymentFilterBillingReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_billing_test_client(billing_service, actor)

    response = client.get("/billing/payments", params={"user_id": "not-a-uuid"})

    assert response.status_code == 400
    assert response.json() == {"detail": "user_id must be a valid UUID"}
    assert billing_service.payment_list_calls == [
        {
            "actor": actor,
            "params": {
                "page": 1,
                "page_size": 50,
                "search": "",
                "status": None,
                "provider_mode": None,
                "user_id": "not-a-uuid",
            },
        }
    ]


def test_admin_billing_router_maps_audit_list_errors() -> None:
    billing_service = InvalidAuditFilterBillingReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_billing_test_client(billing_service, actor)

    response = client.get("/billing/monobank-audit", params={"payment_id": 0})

    assert response.status_code == 400
    assert response.json() == {"detail": "payment_id must be a positive integer"}
    assert billing_service.audit_list_calls == [
        {
            "actor": actor,
            "params": {
                "page": 1,
                "page_size": 50,
                "search": "",
                "direction": None,
                "provider_mode": None,
                "payment_id": 0,
                "invoice_id": None,
            },
        }
    ]


def test_admin_billing_router_maps_payment_detail_errors() -> None:
    billing_service = MissingPaymentBillingReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_billing_test_client(billing_service, actor)

    response = client.get("/billing/payments/404")

    assert response.status_code == 404
    assert response.json() == {"detail": "Billing payment not found"}
    assert billing_service.payment_detail_calls == [{"actor": actor, "payment_id": 404}]


def test_admin_billing_router_maps_audit_detail_errors() -> None:
    billing_service = MissingAuditLogBillingReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_billing_test_client(billing_service, actor)

    response = client.get("/billing/monobank-audit/404")

    assert response.status_code == 404
    assert response.json() == {"detail": "Monobank audit log not found"}
    assert billing_service.audit_detail_calls == [{"actor": actor, "audit_log_id": 404}]


def test_admin_billing_router_maps_access_denied_to_403() -> None:
    billing_service = AccessDeniedBillingReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_billing_test_client(billing_service, actor)

    response = client.get("/billing/payments")

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied"}
