from __future__ import annotations

from typing import Any, Protocol

from fastapi import APIRouter, HTTPException, Request

from app.billing.services.webhook_service import MonobankWebhookError


class BillingWebhookRuntimeService(Protocol):
    def handle_monobank_webhook(
        self,
        *,
        raw_body: bytes,
        headers: dict[str, str],
        request_url: str,
        request_ip: str | None,
    ) -> dict[str, Any]: ...


class BillingRouterRuntime(Protocol):
    billing_webhook_service: BillingWebhookRuntimeService


def build_billing_router(service: BillingRouterRuntime) -> APIRouter:
    router = APIRouter(prefix="/billing")

    @router.post("/monobank/webhook")
    async def monobank_webhook(request: Request) -> dict:
        raw_body = await request.body()
        try:
            return service.billing_webhook_service.handle_monobank_webhook(
                raw_body=raw_body,
                headers=dict(request.headers),
                request_url=str(request.url),
                request_ip=request.client.host if request.client else None,
            )
        except MonobankWebhookError as error:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error

    return router
