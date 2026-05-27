from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.admin_api.billing.http_errors import admin_billing_read_error_status_code
from app.admin_api.context import AdminRouterContext
from app.application.admin.billing.errors import AdminBillingReadError


def build_billing_router(context: AdminRouterContext) -> APIRouter:
    router = APIRouter(prefix="/billing")

    @router.get("/payments")
    def admin_billing_payments(
        request: Request,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50),
        search: str = "",
        status: list[str] | None = Query(default=None),
        provider_mode: list[str] | None = Query(default=None),
        user_id: str | None = None,
    ) -> dict:
        try:
            return context.admin_billing_read_service().list_payments(
                actor=context.current_admin_user(request),
                params={
                    "page": page,
                    "page_size": page_size,
                    "search": search,
                    "status": status,
                    "provider_mode": provider_mode,
                    "user_id": user_id,
                },
            )
        except AdminBillingReadError as error:
            raise HTTPException(status_code=admin_billing_read_error_status_code(error), detail=error.detail) from error

    @router.get("/payments/{payment_id}")
    def admin_billing_payment_detail(payment_id: int, request: Request) -> dict:
        try:
            return context.admin_billing_read_service().get_payment_detail(
                actor=context.current_admin_user(request),
                payment_id=payment_id,
            )
        except AdminBillingReadError as error:
            raise HTTPException(status_code=admin_billing_read_error_status_code(error), detail=error.detail) from error

    @router.get("/monobank-audit")
    def admin_monobank_audit_logs(
        request: Request,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50),
        search: str = "",
        direction: list[str] | None = Query(default=None),
        provider_mode: list[str] | None = Query(default=None),
        payment_id: int | None = None,
        invoice_id: str | None = None,
    ) -> dict:
        try:
            return context.admin_billing_read_service().list_monobank_audit_logs(
                actor=context.current_admin_user(request),
                params={
                    "page": page,
                    "page_size": page_size,
                    "search": search,
                    "direction": direction,
                    "provider_mode": provider_mode,
                    "payment_id": payment_id,
                    "invoice_id": invoice_id,
                },
            )
        except AdminBillingReadError as error:
            raise HTTPException(status_code=admin_billing_read_error_status_code(error), detail=error.detail) from error

    @router.get("/monobank-audit/{audit_log_id}")
    def admin_monobank_audit_log_detail(audit_log_id: int, request: Request) -> dict:
        try:
            return context.admin_billing_read_service().get_monobank_audit_log_detail(
                actor=context.current_admin_user(request),
                audit_log_id=audit_log_id,
            )
        except AdminBillingReadError as error:
            raise HTTPException(status_code=admin_billing_read_error_status_code(error), detail=error.detail) from error

    return router
