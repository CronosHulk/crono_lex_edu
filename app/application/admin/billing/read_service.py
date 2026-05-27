from __future__ import annotations

from collections.abc import Callable
from typing import Any, ParamSpec, Protocol, TypeVar
from uuid import UUID

import app.validation.pagination as validation_pagination
import app.validation.request_values as request_values
from app.application.admin.billing.errors import (
    AdminBillingAuditLogNotFoundError,
    AdminBillingPaymentNotFoundError,
    AdminBillingReadAccessDeniedError,
    AdminBillingReadValidationError,
)
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)
from app.domain.billing.constants import (
    BILLING_PAYMENT_STATUSES,
    BILLING_PROVIDER_MODES,
    MONOBANK_AUDIT_DIRECTIONS,
    MONOBANK_AUDIT_PROVIDER_MODES,
)

DEFAULT_PAGE_SIZE = 50
ALLOWED_PAGE_SIZES = {50, 100}
P = ParamSpec("P")
T = TypeVar("T")


class AdminBillingReadAclPermissionsPort(Protocol):
    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None: ...


class AdminBillingReadRepositoryPort(Protocol):
    def list_admin_payments(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def get_admin_payment_detail(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None: ...

    def list_admin_monobank_audit_logs(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def get_admin_monobank_audit_log_detail(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None: ...


class AdminBillingReadDatabasePort(Protocol):
    acl_permissions: AdminBillingReadAclPermissionsPort
    billing: AdminBillingReadRepositoryPort


class AdminBillingReadService:
    def __init__(self, db: AdminBillingReadDatabasePort) -> None:
        self.db = db

    def list_payments(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        self._require_settings_view_access(actor)
        page, page_size = _billing_validation(
            validation_pagination.normalize_pagination,
            params,
            default_page_size=DEFAULT_PAGE_SIZE,
            allowed_page_sizes=ALLOWED_PAGE_SIZES,
        )
        return self.db.billing.list_admin_payments(
            page=page,
            page_size=page_size,
            status=_billing_validation(
                request_values.ensure_allowed_values,
                params.get("status"),
                BILLING_PAYMENT_STATUSES,
                "status",
            ),
            provider_mode=_billing_validation(
                request_values.ensure_allowed_values,
                params.get("provider_mode"),
                BILLING_PROVIDER_MODES,
                "provider_mode",
            ),
            user_id=normalize_optional_user_uuid(params.get("user_id")),
            search=_billing_validation(request_values.ensure_text, params.get("search"), "search", max_length=120),
        )

    def get_payment_detail(self, *, actor: dict[str, Any], payment_id: int) -> dict[str, Any]:
        self._require_settings_view_access(actor)
        payment = self.db.billing.get_admin_payment_detail(
            _billing_validation(request_values.ensure_positive_int, payment_id, "payment_id")
        )
        if payment is None:
            raise AdminBillingPaymentNotFoundError()
        return payment

    def list_monobank_audit_logs(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        self._require_settings_view_access(actor)
        page, page_size = _billing_validation(
            validation_pagination.normalize_pagination,
            params,
            default_page_size=DEFAULT_PAGE_SIZE,
            allowed_page_sizes=ALLOWED_PAGE_SIZES,
        )
        raw_payment_id = params.get("payment_id")
        return self.db.billing.list_admin_monobank_audit_logs(
            page=page,
            page_size=page_size,
            direction=_billing_validation(
                request_values.ensure_allowed_values,
                params.get("direction"),
                MONOBANK_AUDIT_DIRECTIONS,
                "direction",
            ),
            provider_mode=_billing_validation(
                request_values.ensure_allowed_values,
                params.get("provider_mode"),
                MONOBANK_AUDIT_PROVIDER_MODES,
                "provider_mode",
            ),
            payment_id=(
                _billing_validation(request_values.ensure_positive_int, raw_payment_id, "payment_id")
                if raw_payment_id is not None
                else None
            ),
            invoice_id=_billing_validation(
                request_values.ensure_text,
                params.get("invoice_id"),
                "invoice_id",
                max_length=120,
            ),
            search=_billing_validation(request_values.ensure_text, params.get("search"), "search", max_length=120),
        )

    def get_monobank_audit_log_detail(self, *, actor: dict[str, Any], audit_log_id: int) -> dict[str, Any]:
        self._require_settings_view_access(actor)
        audit_log = self.db.billing.get_admin_monobank_audit_log_detail(
            _billing_validation(request_values.ensure_positive_int, audit_log_id, "audit_log_id")
        )
        if audit_log is None:
            raise AdminBillingAuditLogNotFoundError()
        return {"audit_log": audit_log}

    def _require_settings_view_access(self, actor: dict[str, Any]) -> None:
        try:
            require_admin_access_allowed(self.db, actor, action="settings/view")
        except AdminPermissionDeniedError as error:
            raise AdminBillingReadAccessDeniedError(error.detail) from error


def normalize_optional_user_uuid(value: Any) -> str:
    text = _billing_validation(request_values.ensure_text, value, "user_id", max_length=64)
    if not text:
        return ""
    try:
        return str(UUID(text))
    except ValueError as error:
        raise AdminBillingReadValidationError("user_id must be a valid UUID") from error


def _billing_validation(validator: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        return validator(*args, **kwargs)
    except request_values.RequestValueValidationError as error:
        raise AdminBillingReadValidationError(error.detail) from error
