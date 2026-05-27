from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.billing_api as billing_router
from app.billing.services.webhook_service import MonobankWebhookError


class FakeBillingRuntime:
    def __init__(self, billing_webhook_service: object | None = None) -> None:
        self.billing_webhook_service = billing_webhook_service or FakeBillingWebhookService()


class FakeBillingWebhookService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def handle_monobank_webhook(
        self,
        *,
        raw_body: bytes,
        headers: dict[str, Any],
        request_url: str,
        request_ip: str | None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "raw_body": raw_body,
                "headers": headers,
                "request_url": request_url,
                "request_ip": request_ip,
            }
        )
        return {"ok": True}


class RejectingBillingWebhookService(FakeBillingWebhookService):
    def handle_monobank_webhook(
        self,
        *,
        raw_body: bytes,
        headers: dict[str, Any],
        request_url: str,
        request_ip: str | None,
    ) -> dict[str, Any]:
        raise MonobankWebhookError(400, "invalid_signature", "Invalid Monobank webhook signature")


def test_billing_webhook_router_delegates_request_payload() -> None:
    webhook_service = FakeBillingWebhookService()
    app = FastAPI()
    app.include_router(billing_router.build_billing_router(FakeBillingRuntime(webhook_service)))

    response = TestClient(app).post(
        "/billing/monobank/webhook",
        content=b'{"invoiceId":"p2_demo"}',
        headers={"X-Sign": "signature"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert webhook_service.calls[0]["raw_body"] == b'{"invoiceId":"p2_demo"}'
    assert webhook_service.calls[0]["headers"]["x-sign"] == "signature"
    assert webhook_service.calls[0]["request_url"].endswith("/billing/monobank/webhook")
    assert webhook_service.calls[0]["request_ip"] == "testclient"


def test_billing_webhook_router_translates_service_error() -> None:
    app = FastAPI()
    app.include_router(
        billing_router.build_billing_router(FakeBillingRuntime(RejectingBillingWebhookService()))
    )

    response = TestClient(app).post("/billing/monobank/webhook", content=b"{}")

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid Monobank webhook signature"}
