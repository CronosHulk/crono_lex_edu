from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, cast

from app.billing.helpers.amounts import amount_minor_to_uah
from app.billing.helpers.client_payments import build_public_payment_failure_message
from app.billing.runtime_settings import (
    BillingRuntimeSettingsValidationError,
    read_billing_runtime_settings,
)
from app.billing.services.checkout_service import serialize_payment_for_client
from app.billing.services.fiscal_check_delivery import ensure_success_fiscal_checks_with_event
from app.billing.services.payment_status import (
    PostUpgradeRescanCallback,
    apply_provider_status_payload,
)
from app.billing.services.provider_port import (
    BillingInvoiceStatusProviderFactory,
    BillingInvoiceStatusProviderPort,
    BillingProviderAuditContext,
    BillingProviderPaymentStatus,
    BillingReceiptFiscalProviderFactory,
    require_billing_invoice_status_provider_factory,
)
from app.billing.services.provider_runtime import (
    BillingPaymentProviderRuntime,
    resolve_payment_provider_runtime,
    validate_payment_provider_credentials,
)
from app.billing.services.receipt_retrieval_service import BillingReceiptRetrievalService
from app.domain.billing.constants import BILLING_TERMINAL_STATUSES
from app.subscriptions.user_entitlements import read_user_uuid
from app.time_utils import TimeService

CLIENT_POLLING_PROVIDER_UNAVAILABLE_CODE = "provider_status_temporarily_unavailable"
CLIENT_POLLING_PROVIDER_UNAVAILABLE_MESSAGE = (
    "Payment status is temporarily unavailable. CronoLex will keep checking it in the background."
)


class BillingPaymentStatusError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class BillingPaymentStatusNotFoundError(BillingPaymentStatusError):
    pass


class BillingPaymentStatusConfigurationError(BillingPaymentStatusError):
    pass


class BillingPaymentStatusServiceBillingPort(Protocol):
    def get_payment_by_id(self, payment_id: int) -> dict[str, Any] | None: ...

    def create_payment_event(
        self,
        *,
        payment_id: int,
        event_type: str,
        source: str,
        provider_status: str | None,
        payload_json: dict[str, Any],
        current_time: Any,
    ) -> Any: ...

    def update_payment_provider_status(
        self,
        payment_id: int,
        *,
        status: str,
        provider_status_json: dict[str, Any],
        failure_code: str | None,
        failure_reason: str | None,
        paid_at: Any | None,
        current_time: Any,
    ) -> dict[str, Any] | None: ...

    def apply_subscription_purchase_for_payment(
        self,
        payment: dict[str, Any],
        *,
        current_time: Any,
    ) -> Any: ...

    def reverse_subscription_purchase_projection_for_payment(
        self,
        payment_id: int,
        *,
        current_time: Any,
    ) -> Any: ...

    def list_payment_receipts(self, payment_id: int) -> list[dict[str, Any]]: ...

    def create_receipt(
        self,
        *,
        payment_id: int,
        receipt_type: str,
        status: str,
        provider_check_id: str | None = None,
        fiscalization_source: str | None = None,
        tax_url: str | None = None,
        file_base64: str | None = None,
        payload_json: dict[str, Any] | None = None,
        bot_delivery_status: str | None = None,
        retry_count: int = 0,
        next_retry_at: datetime | None = None,
        current_time: datetime,
    ) -> dict[str, Any]: ...


class BillingPaymentStatusServiceUserProfilesPort(Protocol):
    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None: ...


class BillingPaymentStatusServiceAppSettingsPort(Protocol):
    def get_value(self, key: str) -> Any: ...


class BillingPaymentStatusServiceDatabasePort(Protocol):
    billing: BillingPaymentStatusServiceBillingPort
    user_profiles: BillingPaymentStatusServiceUserProfilesPort
    settings: Any
    app_settings: BillingPaymentStatusServiceAppSettingsPort


class BillingPaymentStatusService:
    def __init__(
        self,
        db: BillingPaymentStatusServiceDatabasePort,
        time_service: TimeService,
        *,
        billing_provider_factory: BillingInvoiceStatusProviderFactory | None = None,
        billing_receipt_fiscal_provider_factory: BillingReceiptFiscalProviderFactory
        | None = None,
        post_upgrade_rescan: PostUpgradeRescanCallback | None = None,
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.billing_invoice_status_provider_factory = (
            billing_provider_factory
        )
        self.billing_receipt_fiscal_provider_factory = (
            billing_receipt_fiscal_provider_factory
            or cast(BillingReceiptFiscalProviderFactory | None, billing_provider_factory)
        )
        self.post_upgrade_rescan = post_upgrade_rescan
        self.receipt_retrieval = BillingReceiptRetrievalService(
            db,
            time_service,
            billing_provider_factory=self.billing_receipt_fiscal_provider_factory,
        )

    def get_client_payment_status(
        self,
        user: dict[str, Any],
        *,
        payment_id: int,
        request_ip: str | None,
    ) -> dict[str, Any]:
        payment = self.db.billing.get_payment_by_id(payment_id)
        if payment is None:
            raise BillingPaymentStatusNotFoundError("Billing payment not found")
        user_uuid = self._read_user_uuid(user)
        if str(payment["user_uuid"]) != user_uuid:
            raise BillingPaymentStatusNotFoundError("Billing payment not found")

        settings = self._runtime_settings()
        poll_attempted = False
        poll_error: dict[str, str] | None = None
        if self._should_poll(payment, settings=settings):
            poll_attempted = True
            try:
                provider_payload = self._fetch_payment_status_payload(
                    payment, request_ip=request_ip
                )
            except Exception as error:
                error_type = type(error).__name__
                error_message = str(error)[:1000]
                poll_error = build_client_polling_error_payload()
                self.db.billing.create_payment_event(
                    payment_id=int(payment["id"]),
                    event_type="client_status_polling_error",
                    source="client_status_polling",
                    provider_status=None,
                    payload_json={
                        "client_error_code": poll_error["code"],
                        "error_type": error_type,
                        "error_message": error_message,
                    },
                    current_time=self.time_service.now(),
                )
            else:
                if provider_payload is not None:
                    payload, provider_status = provider_payload
                    payment = (
                        apply_provider_status_payload(
                            self.db,
                            self.time_service,
                            payment=payment,
                            provider_status=provider_status,
                            payload=payload,
                            source="client_status_polling",
                            post_upgrade_rescan=self.post_upgrade_rescan,
                        )
                        or payment
                    )
                    ensure_success_fiscal_checks_with_event(
                        db=self.db,
                        time_service=self.time_service,
                        receipt_retrieval=self.receipt_retrieval,
                        payment=payment,
                        source="client_status_polling",
                        source_place="client_status_fiscal_check",
                    )

        return {
            "payment": serialize_payment_for_client(payment),
            "order": {
                "plan_key": payment["plan_key"],
                "period_months": payment["period_months"],
                "amount_minor": payment["amount_minor"],
                "amount_uah": amount_minor_to_uah(int(payment["amount_minor"])),
                "currency": payment["currency"],
            },
            "status": build_client_status_payload(
                payment, current_time=self.time_service.now(), settings=settings
            ),
            "polling": {
                "attempted": poll_attempted,
                "error": poll_error,
                "webhook_wait_seconds": int(settings["webhook_wait_seconds"]),
                "frontend_poll_timeout_seconds": int(settings["frontend_poll_timeout_seconds"]),
                "long_processing_seconds": int(settings["long_processing_seconds"]),
            },
        }

    def _fetch_payment_status_payload(
        self,
        payment: dict[str, Any],
        *,
        request_ip: str | None,
    ) -> tuple[dict[str, Any], BillingProviderPaymentStatus] | None:
        provider_invoice_id = str(payment.get("provider_invoice_id") or "").strip()
        if not provider_invoice_id:
            return None
        provider_runtime = resolve_payment_provider_runtime(payment)
        self._validate_provider_credentials(provider_runtime)
        provider = self._billing_provider(
            provider_runtime.provider_key,
            provider_runtime.provider_mode,
        )
        payload = provider.get_invoice_status(
            provider_invoice_id,
            audit_context=BillingProviderAuditContext(
                source_place="client_status_polling",
                actor_user_uuid=payment["user_uuid"],
                telegram_user_id=int(payment["telegram_user_id"]),
                payment_id=int(payment["id"]),
                order_reference=payment.get("provider_reference"),
                invoice_id=provider_invoice_id,
                request_ip=request_ip,
            ),
        )
        return payload, provider.resolve_payment_status(payload)

    def _should_poll(self, payment: dict[str, Any], *, settings: dict[str, Any]) -> bool:
        if payment["status"] in BILLING_TERMINAL_STATUSES:
            return False
        if not payment.get("provider_invoice_id"):
            return False
        return elapsed_seconds(payment["created"], self.time_service.now()) >= int(
            settings["webhook_wait_seconds"]
        )

    def _read_user_uuid(self, user: dict[str, Any]) -> str:
        user_uuid = read_user_uuid(user)
        if not user_uuid:
            profile = self.db.user_profiles.get_profile(int(user["telegram_user_id"]))
            user_uuid = read_user_uuid(profile)
        if not user_uuid:
            raise BillingPaymentStatusNotFoundError("User profile not found")
        return str(user_uuid)

    def _runtime_settings(self) -> dict[str, Any]:
        try:
            return read_billing_runtime_settings(self.db)
        except BillingRuntimeSettingsValidationError as error:
            raise BillingPaymentStatusConfigurationError(str(error)) from error

    def _validate_provider_credentials(
        self, provider_runtime: BillingPaymentProviderRuntime
    ) -> None:
        try:
            validate_payment_provider_credentials(self.db.settings, provider_runtime)
        except BillingRuntimeSettingsValidationError as error:
            raise BillingPaymentStatusConfigurationError(str(error)) from error

    def _billing_provider(
        self, provider_key: str, provider_mode: str
    ) -> BillingInvoiceStatusProviderPort:
        return require_billing_invoice_status_provider_factory(
            self.billing_invoice_status_provider_factory
        )(provider_key=provider_key, provider_mode=provider_mode)


def build_client_polling_error_payload() -> dict[str, str]:
    return {
        "code": CLIENT_POLLING_PROVIDER_UNAVAILABLE_CODE,
        "message": CLIENT_POLLING_PROVIDER_UNAVAILABLE_MESSAGE,
    }


def build_client_status_payload(
    payment: dict[str, Any],
    *,
    current_time: datetime,
    settings: dict[str, Any],
) -> dict[str, Any]:
    status = str(payment["status"])
    is_terminal = status in BILLING_TERMINAL_STATUSES
    elapsed = elapsed_seconds(payment["created"], current_time)
    is_long_processing = not is_terminal and elapsed >= int(settings["long_processing_seconds"])
    should_stop_polling = not is_terminal and elapsed >= int(
        settings["frontend_poll_timeout_seconds"]
    )
    return {
        "value": status,
        "is_terminal": is_terminal,
        "is_success": status == "success",
        "is_failure": status in {"failure", "reversed", "expired"},
        "is_long_processing": is_long_processing,
        "should_stop_polling": should_stop_polling,
        "failure_message": build_public_payment_failure_message(
            status, payment.get("failure_reason")
        ),
        "message": build_client_status_message(
            status,
            is_long_processing=is_long_processing or should_stop_polling,
            failure_reason=payment.get("failure_reason"),
        ),
    }


def build_client_status_message(
    status: str, *, is_long_processing: bool, failure_reason: str | None
) -> str:
    if status == "success":
        return "Payment successful"
    if status in {"failure", "reversed", "expired"}:
        return build_public_payment_failure_message(status, failure_reason) or "Payment failed"
    if is_long_processing:
        return "Payment is still processing. CronoLex will notify you in Telegram when the status changes."
    return "Waiting for payment confirmation"


def elapsed_seconds(started: datetime, current_time: datetime) -> int:
    if started.tzinfo is None and current_time.tzinfo is not None:
        started = started.replace(tzinfo=current_time.tzinfo)
    if current_time.tzinfo is None and started.tzinfo is not None:
        current_time = current_time.replace(tzinfo=started.tzinfo)
    return max(int((current_time - started).total_seconds()), 0)
