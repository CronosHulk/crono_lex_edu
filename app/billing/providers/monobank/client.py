from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

import httpx

from app.billing.providers.monobank.audit import (
    MonobankAuditContext,
    MonobankAuditLogger,
    duration_ms,
    mask_headers,
)
from app.billing.runtime_settings import MONOBANK_MODE_PRODUCTION, MONOBANK_MODE_TEST
from app.config import Settings

MONOBANK_API_BASE_URL = "https://api.monobank.ua"
MONOBANK_JSON_HEADERS = {"Content-Type": "application/json"}


class MonobankConfigurationError(RuntimeError):
    pass


class MonobankAPIError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        response_payload: dict[str, Any] | list[Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.response_payload = response_payload


@dataclass(frozen=True)
class MonobankCreateInvoiceRequest:
    amount: int
    merchant_paym_info: dict[str, Any]
    redirect_url: str
    webhook_url: str
    validity: int
    ccy: int = 980
    payment_type: str = "debit"

    def to_payload(self) -> dict[str, Any]:
        return {
            "amount": self.amount,
            "ccy": self.ccy,
            "merchantPaymInfo": self.merchant_paym_info,
            "redirectUrl": self.redirect_url,
            "webHookUrl": self.webhook_url,
            "validity": self.validity,
            "paymentType": self.payment_type,
        }


class MonobankInvoicePayloadRequest(Protocol):
    def to_payload(self) -> dict[str, Any]:
        ...


class MonobankClient:
    def __init__(
        self,
        *,
        settings: Settings,
        provider_mode: str,
        audit_logger: MonobankAuditLogger,
        http_client: httpx.Client | None = None,
        base_url: str = MONOBANK_API_BASE_URL,
        clock: Any | None = None,
    ) -> None:
        self.settings = settings
        self.provider_mode = provider_mode
        self.audit_logger = audit_logger
        self.http_client = http_client
        self.base_url = base_url.rstrip("/")
        self.clock = clock or (lambda: datetime.now(UTC))
        self.token = resolve_monobank_token(settings, provider_mode)

    def create_invoice(
        self,
        request: MonobankInvoicePayloadRequest,
        *,
        audit_context: MonobankAuditContext,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/merchant/invoice/create",
            audit_context=audit_context,
            json_body=request.to_payload(),
        )

    def get_invoice_status(self, invoice_id: str, *, audit_context: MonobankAuditContext) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/merchant/invoice/status",
            audit_context=MonobankAuditContext(
                **{**audit_context.__dict__, "invoice_id": audit_context.invoice_id or invoice_id}
            ),
            query_params={"invoiceId": invoice_id},
        )

    def get_receipt(self, invoice_id: str, *, audit_context: MonobankAuditContext) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/merchant/invoice/receipt",
            audit_context=MonobankAuditContext(
                **{**audit_context.__dict__, "invoice_id": audit_context.invoice_id or invoice_id}
            ),
            query_params={"invoiceId": invoice_id},
        )

    def get_fiscal_checks(self, invoice_id: str, *, audit_context: MonobankAuditContext) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/merchant/invoice/fiscal-checks",
            audit_context=MonobankAuditContext(
                **{**audit_context.__dict__, "invoice_id": audit_context.invoice_id or invoice_id}
            ),
            query_params={"invoiceId": invoice_id},
        )

    def get_public_key(self, *, audit_context: MonobankAuditContext) -> dict[str, Any]:
        return self._request("GET", "/api/merchant/pubkey", audit_context=audit_context)

    def _request(
        self,
        method: str,
        path: str,
        *,
        audit_context: MonobankAuditContext,
        json_body: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        started = self.clock()
        headers = {**MONOBANK_JSON_HEADERS, "X-Token": self.token}
        url = f"{self.base_url}{path}"
        response_status_code: int | None = None
        response_headers: dict[str, Any] = {}
        response_body: dict[str, Any] | list[Any] | None = None
        response_raw_body: str | None = None
        error_text: str | None = None
        finished: datetime | None = None
        resolved_invoice_id = audit_context.invoice_id
        try:
            response = self._send_request(method, url, headers=headers, json_body=json_body, query_params=query_params)
            response_status_code = response.status_code
            response_headers = dict(response.headers)
            response_body, response_raw_body = _decode_response_body(response)
            if response.is_error:
                raise _build_api_error(response_status_code, response_body, response_raw_body)
            if not isinstance(response_body, dict):
                raise MonobankAPIError("Monobank response must be a JSON object", status_code=response_status_code)
            resolved_invoice_id = resolved_invoice_id or str(response_body.get("invoiceId") or "") or None
            return response_body
        except Exception as error:
            error_text = str(error)
            raise
        finally:
            finished = self.clock()
            self.audit_logger.create_monobank_audit_log(
                direction="outgoing",
                provider_mode=self.provider_mode,
                source_place=audit_context.source_place,
                actor_user_uuid=audit_context.actor_user_uuid,
                telegram_user_id=audit_context.telegram_user_id,
                payment_id=audit_context.payment_id,
                order_reference=audit_context.order_reference,
                invoice_id=resolved_invoice_id,
                request_method=method,
                request_url=_format_request_url(url, query_params),
                request_ip=audit_context.request_ip,
                request_headers_json=mask_headers(headers),
                request_body_json=json_body,
                response_status_code=response_status_code,
                response_headers_json=mask_headers(response_headers),
                response_body_json=response_body,
                response_raw_body=response_raw_body,
                error_text=error_text,
                started=started,
                finished=finished,
                duration_ms=duration_ms(started, finished),
            )

    def _send_request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json_body: dict[str, Any] | None,
        query_params: dict[str, Any] | None,
    ) -> httpx.Response:
        if self.http_client is not None:
            return self.http_client.request(method, url, headers=headers, json=json_body, params=query_params)
        with httpx.Client(timeout=30.0) as client:
            return client.request(method, url, headers=headers, json=json_body, params=query_params)


def resolve_monobank_token(settings: Settings, provider_mode: str) -> str:
    if provider_mode == MONOBANK_MODE_TEST:
        token = settings.monobank_token_test
    elif provider_mode == MONOBANK_MODE_PRODUCTION:
        token = settings.monobank_token
    else:
        raise MonobankConfigurationError(f"Unsupported Monobank mode for provider calls: {provider_mode}")
    if not str(token or "").strip():
        raise MonobankConfigurationError(f"Monobank token is not configured for mode: {provider_mode}")
    return token.strip()


def _decode_response_body(response: httpx.Response) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
    text = response.text
    if not text:
        return {}, None
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return None, text
    if isinstance(payload, (dict, list)):
        return payload, None
    return None, text


def _build_api_error(
    status_code: int,
    response_body: dict[str, Any] | list[Any] | None,
    response_raw_body: str | None,
) -> MonobankAPIError:
    if isinstance(response_body, dict):
        err_code = str(response_body.get("errCode") or "") or None
        err_text = str(response_body.get("errText") or "") or f"Monobank request failed with HTTP {status_code}"
        return MonobankAPIError(err_text, status_code=status_code, error_code=err_code, response_payload=response_body)
    return MonobankAPIError(
        response_raw_body or f"Monobank request failed with HTTP {status_code}",
        status_code=status_code,
        response_payload=response_body,
    )


def _format_request_url(url: str, query_params: dict[str, Any] | None) -> str:
    if not query_params:
        return url
    query = httpx.QueryParams(query_params)
    return f"{url}?{query}"
