from __future__ import annotations

from typing import Any

from app.billing.providers.monobank.webhook_payload import (
    BillingWebhookPayloadError,
)
from app.billing.providers.monobank.webhook_payload import (
    normalize_invoice_id as _normalize_monobank_invoice_id,
)
from app.billing.providers.monobank.webhook_payload import (
    normalize_provider_status as _normalize_monobank_provider_status,
)
from app.billing.providers.monobank.webhook_payload import (
    parse_monobank_webhook_body as _parse_monobank_webhook_body,
)
from app.billing.providers.monobank.webhook_payload import (
    parse_monobank_webhook_payload as _parse_monobank_webhook_payload,
)
from app.billing.runtime_settings import (
    MONOBANK_MODE_PRODUCTION,
    MONOBANK_MODE_TEST,
)
from app.billing.services.provider_port import (
    BillingProviderAuditContext,
    BillingProviderWebhookPayload,
    BillingWebhookPublicKeyProviderFactory,
    BillingWebhookPublicKeyProviderPort,
    BillingWebhookSignatureVerifier,
    require_billing_webhook_public_key_provider_factory,
    require_billing_webhook_signature_verifier,
)
from app.billing.services.provider_runtime import monobank_webhook_provider_key


class MonobankWebhookAdapter:
    def __init__(
        self,
        *,
        billing_webhook_public_key_provider_factory: BillingWebhookPublicKeyProviderFactory
        | None = None,
        monobank_signature_verifier: BillingWebhookSignatureVerifier | None = None,
        public_key_cache: dict[str, str] | None = None,
    ) -> None:
        self.billing_webhook_public_key_provider_factory = (
            billing_webhook_public_key_provider_factory
        )
        self.monobank_signature_verifier = monobank_signature_verifier
        self._public_key_cache = public_key_cache if public_key_cache is not None else {}

    def parse_webhook_body(self, raw_body: bytes) -> dict[str, Any]:
        return _parse_monobank_webhook_body(raw_body)

    def parse_webhook_payload(self, raw_body: bytes) -> BillingProviderWebhookPayload:
        return _parse_monobank_webhook_payload(raw_body)

    def normalize_invoice_id(self, value: Any) -> str:
        return _normalize_monobank_invoice_id(value)

    def normalize_provider_status(self, value: Any) -> str:
        return _normalize_monobank_provider_status(value)

    def verify_signature(
        self, *, provider_mode: str, signature_base64: str, raw_body: bytes
    ) -> bool:
        if provider_mode not in {MONOBANK_MODE_TEST, MONOBANK_MODE_PRODUCTION}:
            self._raise_error(
                400, "provider_mode_unknown", "Unable to resolve Monobank mode for webhook"
            )

        verify_signature = require_billing_webhook_signature_verifier(
            self.monobank_signature_verifier
        )
        provider_key = monobank_webhook_provider_key()
        public_key = self._get_public_key(provider_key, provider_mode)
        if verify_signature(
            public_key_base64=public_key,
            signature_base64=signature_base64,
            raw_body=raw_body,
        ):
            return True
        self._public_key_cache.pop(provider_mode, None)
        refreshed_public_key = self._get_public_key(provider_key, provider_mode)
        return verify_signature(
            public_key_base64=refreshed_public_key,
            signature_base64=signature_base64,
            raw_body=raw_body,
        )

    def _get_public_key(self, provider_key: str, provider_mode: str) -> str:
        cached = self._public_key_cache.get(provider_mode)
        if cached:
            return cached
        payload = self._webhook_public_key_provider(provider_key, provider_mode).get_public_key(
            audit_context=BillingProviderAuditContext(
                source_place="webhook_signature_verification"
            )
        )
        key = str(payload.get("key") or "").strip()
        if not key:
            self._raise_error(
                400,
                "pubkey_unavailable",
                "Monobank public key is unavailable",
            )
        self._public_key_cache[provider_mode] = key
        return key

    def _webhook_public_key_provider(
        self, provider_key: str, provider_mode: str
    ) -> BillingWebhookPublicKeyProviderPort:
        return require_billing_webhook_public_key_provider_factory(
            self.billing_webhook_public_key_provider_factory
        )(provider_key=provider_key, provider_mode=provider_mode)

    @staticmethod
    def _raise_error(status_code: int, error_code: str, message: str) -> None:
        raise BillingWebhookPayloadError(status_code, error_code, message)


__all__ = [
    "MonobankWebhookAdapter",
    "BillingWebhookPayloadError",
]
