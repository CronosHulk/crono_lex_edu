from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, cast
from uuid import UUID

from app.billing.runtime_settings import (
    MONOBANK_MODE_DISABLED,
    MONOBANK_MODE_PRODUCTION,
    MONOBANK_MODE_TEST,
    BillingRuntimeSettingsValidationError,
    read_billing_runtime_settings,
)
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
    BillingProviderWebhookPayload,
    BillingReceiptFiscalProviderFactory,
    BillingWebhookPublicKeyProviderFactory,
    BillingWebhookSignatureVerifier,
    billing_provider_audit_duration_ms,
    mask_billing_provider_audit_headers,
    require_billing_invoice_status_provider_factory,
)
from app.billing.services.provider_runtime import resolve_payment_provider_runtime
from app.billing.services.receipt_retrieval_service import BillingReceiptRetrievalService
from app.time_utils import TimeService

MONOBANK_AUDIT_MODE_UNKNOWN = "unknown"


class BillingWebhookAppSettingsPort(Protocol):
    def get_value(self, key: str) -> dict[str, Any] | None: ...


class BillingWebhookBillingPort(Protocol):
    def get_payment_by_provider_invoice_id(
        self, provider_invoice_id: str
    ) -> dict[str, Any] | None: ...

    def create_payment_event(
        self,
        *,
        payment_id: int | None,
        event_type: str,
        source: str,
        provider_status: str | None,
        payload_json: dict[str, Any],
        current_time: datetime,
    ) -> dict[str, Any]: ...

    def update_payment_provider_status(
        self,
        payment_id: int,
        *,
        status: str,
        provider_status_json: dict[str, Any],
        failure_code: str | None,
        failure_reason: str | None,
        paid_at: datetime | None,
        current_time: datetime,
    ) -> dict[str, Any] | None: ...

    def apply_subscription_purchase_for_payment(
        self,
        payment: dict[str, Any],
        *,
        current_time: datetime,
    ) -> dict[str, Any]: ...

    def reverse_subscription_purchase_projection_for_payment(
        self,
        payment_id: int,
        *,
        current_time: datetime,
    ) -> dict[str, Any] | None: ...

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

    def create_monobank_audit_log(
        self,
        *,
        direction: str,
        provider_mode: str,
        source_place: str,
        started: datetime,
        actor_user_uuid: str | UUID | None = None,
        telegram_user_id: int | None = None,
        payment_id: int | None = None,
        order_reference: str | None = None,
        invoice_id: str | None = None,
        request_method: str | None = None,
        request_url: str | None = None,
        request_ip: str | None = None,
        request_headers_json: dict[str, Any] | None = None,
        request_body_json: dict[str, Any] | list[Any] | None = None,
        request_raw_body: str | None = None,
        response_status_code: int | None = None,
        response_headers_json: dict[str, Any] | None = None,
        response_body_json: dict[str, Any] | list[Any] | None = None,
        response_raw_body: str | None = None,
        signature_valid: bool | None = None,
        processing_result: str | None = None,
        error_text: str | None = None,
        finished: datetime | None = None,
        duration_ms: int | None = None,
    ) -> dict[str, Any]: ...


class BillingWebhookDatabasePort(Protocol):
    billing: BillingWebhookBillingPort
    app_settings: BillingWebhookAppSettingsPort


class MonobankWebhookAdapter(Protocol):
    def parse_webhook_payload(self, raw_body: bytes) -> BillingProviderWebhookPayload: ...

    def verify_signature(
        self, *, provider_mode: str, signature_base64: str, raw_body: bytes
    ) -> bool: ...


class _UnconfiguredMonobankWebhookAdapter:
    def parse_webhook_payload(self, raw_body: bytes) -> BillingProviderWebhookPayload:
        raise MonobankWebhookError(
            500,
            "monobank_webhook_adapter_not_configured",
            "Monobank webhook adapter is not configured",
        )

    def verify_signature(
        self, *, provider_mode: str, signature_base64: str, raw_body: bytes
    ) -> bool:
        raise MonobankWebhookError(
            500,
            "monobank_webhook_adapter_not_configured",
            "Monobank webhook adapter is not configured",
        )


class BillingWebhookService:
    def __init__(
        self,
        db: BillingWebhookDatabasePort,
        time_service: TimeService,
        *,
        billing_provider_factory: BillingInvoiceStatusProviderFactory | None = None,
        billing_receipt_fiscal_provider_factory: BillingReceiptFiscalProviderFactory
        | None = None,
        billing_webhook_public_key_provider_factory: BillingWebhookPublicKeyProviderFactory
        | None = None,
        monobank_signature_verifier: BillingWebhookSignatureVerifier | None = None,
        post_upgrade_rescan: PostUpgradeRescanCallback | None = None,
        monobank_webhook_adapter: MonobankWebhookAdapter | None = None,
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
        self.billing_webhook_public_key_provider_factory = (
            billing_webhook_public_key_provider_factory
            or cast(BillingWebhookPublicKeyProviderFactory | None, billing_provider_factory)
        )
        self.monobank_signature_verifier = monobank_signature_verifier
        self.post_upgrade_rescan = post_upgrade_rescan
        self.monobank_webhook_adapter = (
            monobank_webhook_adapter
            or _UNCONFIGURED_MONOBANK_WEBHOOK_ADAPTER
        )
        self.receipt_retrieval = BillingReceiptRetrievalService(
            db,
            time_service,
            billing_provider_factory=self.billing_receipt_fiscal_provider_factory,
        )

    def handle_monobank_webhook(
        self,
        *,
        raw_body: bytes,
        headers: dict[str, Any],
        request_url: str,
        request_ip: str | None,
    ) -> dict[str, Any]:
        started = self.time_service.now()
        response_status = 200
        response_body: dict[str, Any] = {"ok": True}
        parsed_body: dict[str, Any] | None = None
        signature_valid: bool | None = None
        processing_result = "accepted"
        error_text: str | None = None
        payment: dict[str, Any] | None = None
        provider_mode = MONOBANK_AUDIT_MODE_UNKNOWN
        invoice_id: str | None = None

        try:
            webhook_payload = self._parse_webhook_payload(raw_body)
            parsed_body = webhook_payload.payload
            invoice_id = webhook_payload.invoice_id
            provider_status = webhook_payload.provider_status
            payment = self.db.billing.get_payment_by_provider_invoice_id(invoice_id)
            if payment is not None:
                provider_mode = str(payment["provider_mode"])
            else:
                provider_mode = self._fallback_provider_mode()

            signature = str(headers.get("x-sign") or headers.get("X-Sign") or "").strip()
            if not signature:
                raise MonobankWebhookError(400, "missing_signature", "Missing X-Sign header")

            signature_valid = self._verify_monobank_webhook_signature(
                provider_mode=provider_mode,
                signature_base64=signature,
                raw_body=raw_body,
            )
            if not signature_valid:
                raise MonobankWebhookError(
                    400, "invalid_signature", "Invalid Monobank webhook signature"
                )
            if payment is None:
                raise MonobankWebhookError(
                    404, "payment_not_found", "Billing payment was not found for invoice"
                )

            status_payload = parsed_body
            verified_provider_status = provider_status
            try:
                status_payload, verified_provider_status = self._fetch_verified_status_payload(
                    payment=payment,
                    invoice_id=invoice_id,
                    request_ip=request_ip,
                )
            except Exception as error:
                self.db.billing.create_payment_event(
                    payment_id=int(payment["id"]),
                    event_type="webhook_status_verification_error",
                    source="monobank_webhook",
                    provider_status=provider_status,
                    payload_json={
                        "error_type": type(error).__name__,
                        "error_text": str(error)[:1000],
                        "webhook_payload": parsed_body,
                    },
                    current_time=self.time_service.now(),
                )
                raise MonobankWebhookError(
                    502,
                    "status_verification_failed",
                    "Unable to verify Monobank webhook status",
                ) from error
            updated_payment = self._apply_webhook_status(
                payment=payment,
                provider_status=verified_provider_status,
                payload=status_payload,
            )
            ensure_success_fiscal_checks_with_event(
                db=self.db,
                time_service=self.time_service,
                receipt_retrieval=self.receipt_retrieval,
                payment=updated_payment or payment,
                source="monobank_webhook",
                source_place="webhook_fiscal_check",
            )
            processing_result = f"status_{verified_provider_status.provider_status}"
            response_body = {
                "ok": True,
                "payment_id": updated_payment["id"]
                if updated_payment is not None
                else payment["id"],
                "status": verified_provider_status.provider_status,
            }
            return response_body
        except MonobankWebhookError as error:
            response_status = error.status_code
            response_body = {"ok": False, "error": error.error_code}
            processing_result = error.error_code
            error_text = error.message
            raise
        except Exception as error:
            response_status = 500
            response_body = {"ok": False, "error": "webhook_processing_failed"}
            processing_result = "webhook_processing_failed"
            error_text = str(error)
            raise
        finally:
            finished = self.time_service.now()
            self.db.billing.create_monobank_audit_log(
                direction="incoming",
                provider_mode=provider_mode,
                source_place="webhook",
                actor_user_uuid=payment.get("user_uuid") if payment else None,
                telegram_user_id=int(payment["telegram_user_id"]) if payment else None,
                payment_id=int(payment["id"]) if payment else None,
                order_reference=payment.get("provider_reference") if payment else None,
                invoice_id=invoice_id,
                request_method="POST",
                request_url=request_url,
                request_ip=request_ip,
                request_headers_json=mask_billing_provider_audit_headers(headers),
                request_body_json=parsed_body,
                request_raw_body=decode_raw_body(raw_body),
                response_status_code=response_status,
                response_headers_json={"Content-Type": "application/json"},
                response_body_json=response_body,
                signature_valid=signature_valid,
                processing_result=processing_result,
                error_text=error_text,
                started=started,
                finished=finished,
                duration_ms=billing_provider_audit_duration_ms(started, finished),
            )

    def _apply_webhook_status(
        self,
        *,
        payment: dict[str, Any],
        provider_status: BillingProviderPaymentStatus,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        return apply_provider_status_payload(
            self.db,
            self.time_service,
            payment=payment,
            provider_status=provider_status,
            payload=payload,
            source="monobank_webhook",
            post_upgrade_rescan=self.post_upgrade_rescan,
        )

    def _fetch_verified_status_payload(
        self,
        *,
        payment: dict[str, Any],
        invoice_id: str,
        request_ip: str | None,
    ) -> tuple[dict[str, Any], BillingProviderPaymentStatus]:
        provider_runtime = resolve_payment_provider_runtime(payment)
        provider = self._invoice_status_provider(
            provider_runtime.provider_key,
            provider_runtime.provider_mode,
        )
        payload = provider.get_invoice_status(
            invoice_id,
            audit_context=BillingProviderAuditContext(
                source_place="webhook_status_verification",
                actor_user_uuid=payment.get("user_uuid"),
                telegram_user_id=int(payment["telegram_user_id"]),
                payment_id=int(payment["id"]),
                order_reference=payment.get("provider_reference"),
                invoice_id=invoice_id,
                request_ip=request_ip,
            ),
        )
        return payload, provider.resolve_payment_status(payload)

    def _invoice_status_provider(
        self, provider_key: str, provider_mode: str
    ) -> BillingInvoiceStatusProviderPort:
        return require_billing_invoice_status_provider_factory(
            self.billing_invoice_status_provider_factory
        )(provider_key=provider_key, provider_mode=provider_mode)

    def _fallback_provider_mode(self) -> str:
        try:
            mode = str(read_billing_runtime_settings(self.db)["monobank_mode"])
        except BillingRuntimeSettingsValidationError as error:
            raise MonobankWebhookError(400, "invalid_billing_settings", str(error)) from error
        if mode in {MONOBANK_MODE_TEST, MONOBANK_MODE_PRODUCTION}:
            return mode
        if mode == MONOBANK_MODE_DISABLED:
            return MONOBANK_AUDIT_MODE_UNKNOWN
        return MONOBANK_AUDIT_MODE_UNKNOWN

    def _parse_webhook_payload(self, raw_body: bytes) -> BillingProviderWebhookPayload:
        try:
            return self.monobank_webhook_adapter.parse_webhook_payload(raw_body)
        except MonobankWebhookError:
            raise
        except Exception as error:
            raise _adapt_monobank_payload_error(error) from error

    def _verify_monobank_webhook_signature(
        self,
        *,
        provider_mode: str,
        signature_base64: str,
        raw_body: bytes,
    ) -> bool:
        try:
            return self.monobank_webhook_adapter.verify_signature(
                provider_mode=provider_mode,
                signature_base64=signature_base64,
                raw_body=raw_body,
            )
        except MonobankWebhookError:
            raise
        except Exception as error:
            raise _adapt_monobank_payload_error(error) from error


class MonobankWebhookError(Exception):
    def __init__(self, status_code: int, error_code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message


_UNCONFIGURED_MONOBANK_WEBHOOK_ADAPTER = _UnconfiguredMonobankWebhookAdapter()


def parse_monobank_webhook_body(raw_body: bytes) -> dict[str, Any]:
    raise MonobankWebhookError(500, "removed", "monobank_webhook_payload API is moved to provider boundary")


def normalize_invoice_id(value: Any) -> str:
    raise MonobankWebhookError(500, "removed", "monobank_webhook_payload API is moved to provider boundary")


def normalize_provider_status(value: Any) -> str:
    raise MonobankWebhookError(500, "removed", "monobank_webhook_payload API is moved to provider boundary")


def parse_monobank_webhook_payload(
    raw_body: bytes,
) -> BillingProviderWebhookPayload:
    raise MonobankWebhookError(500, "removed", "monobank_webhook_payload API is moved to provider boundary")


def _monobank_webhook_error_from_payload_error(
    error: Exception,
) -> MonobankWebhookError:
    status_code = getattr(error, "status_code", None)
    error_code = getattr(error, "error_code", None)
    message = getattr(error, "message", None)
    if (
        isinstance(status_code, int)
        and isinstance(error_code, str)
        and isinstance(message, str)
    ):
        return MonobankWebhookError(status_code, error_code, message)
    raise error


def _adapt_monobank_payload_error(error: Exception) -> MonobankWebhookError:
    return _monobank_webhook_error_from_payload_error(error)


def decode_raw_body(raw_body: bytes) -> str:
    try:
        return raw_body.decode("utf-8")
    except UnicodeDecodeError:
        return raw_body.hex()
