from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from app.billing.runtime_settings import (
    MONOBANK_MODE_DISABLED,
    MONOBANK_MODE_PRODUCTION,
    MONOBANK_MODE_TEST,
    BillingRuntimeSettingsValidationError,
    validate_monobank_mode_token,
)
from app.domain.billing.constants import (
    BILLING_PAYMENT_PROVIDERS,
    BILLING_PROVIDER_INSTANT,
    BILLING_PROVIDER_MONOBANK,
)
from app.subscriptions.plans import PLAN_PREMIUM, PLAN_PREMIUM_PLUS

CHECKOUT_PLAN_UK_LABELS = {
    PLAN_PREMIUM: "Premium",
    PLAN_PREMIUM_PLUS: "Premium+",
}

MONOBANK_CHECKOUT_WEBHOOK_PATH = "/api/v1/billing/monobank/webhook"
MONOBANK_CHECKOUT_UNAVAILABLE_DETAIL = "Monobank checkout is temporarily unavailable"
MONOBANK_SUPPORTED_PERIOD_MONTHS = (1, 3, 6, 12)
MONOBANK_PLAN_ICON_PATHS = {
    PLAN_PREMIUM: "/billing/premium-crown.svg",
    PLAN_PREMIUM_PLUS: "/billing/premium-plus-crown.svg",
}
INSTANT_CHECKOUT_WEBHOOK_PATH = "/api/v1/billing/instant/webhook"
INSTANT_CHECKOUT_UNAVAILABLE_DETAIL = "Instant checkout is temporarily unavailable"
INSTANT_PLAN_ICON_PATHS = {
    PLAN_PREMIUM: "/billing/premium-crown.svg",
    PLAN_PREMIUM_PLUS: "/billing/premium-plus-crown.svg",
}


@dataclass(frozen=True)
class BillingCheckoutProviderConfig:
    provider_key: str
    provider_mode: str
    webhook_path: str
    invoice_unavailable_detail: str
    plan_icon_paths: Mapping[str, str]
    supported_period_months: tuple[int, ...]


class CheckoutProviderConfigResolver(Protocol):
    def __call__(
        self,
        runtime_settings: dict[str, Any],
        provider_settings: Any,
        *,
        validate_credentials: bool,
    ) -> BillingCheckoutProviderConfig: ...


class CheckoutProviderCredentialValidator(Protocol):
    def __call__(
        self,
        config: BillingCheckoutProviderConfig,
        provider_settings: Any,
    ) -> None: ...


def resolve_checkout_provider_config(
    runtime_settings: dict[str, Any],
    provider_settings: Any,
    *,
    validate_credentials: bool = True,
) -> BillingCheckoutProviderConfig:
    provider_key = str(runtime_settings.get("billing_provider") or "").strip()
    if provider_key not in BILLING_PAYMENT_PROVIDERS:
        raise BillingRuntimeSettingsValidationError("Unsupported billing provider")
    resolver = CHECKOUT_PROVIDER_CONFIG_RESOLVERS.get(provider_key)
    if resolver is None:
        raise BillingRuntimeSettingsValidationError("Unsupported billing provider")
    return resolver(
        runtime_settings,
        provider_settings,
        validate_credentials=validate_credentials,
    )


def validate_checkout_provider_credentials(
    config: BillingCheckoutProviderConfig,
    provider_settings: Any,
) -> None:
    validator = CHECKOUT_PROVIDER_CREDENTIAL_VALIDATORS.get(config.provider_key)
    if validator is None:
        raise BillingRuntimeSettingsValidationError("Unsupported billing provider")
    validator(config, provider_settings)


def build_checkout_subscription_description(
    config: BillingCheckoutProviderConfig,
    plan_key: str,
    period_months: int,
    *,
    quote: dict[str, Any] | None = None,
) -> str:
    _ = config
    plan_label = CHECKOUT_PLAN_UK_LABELS.get(plan_key, plan_key)
    if (quote or {}).get("kind") == "upgrade":
        base_plan_key = str((quote or {}).get("base_plan_key") or "")
        base_label = CHECKOUT_PLAN_UK_LABELS.get(base_plan_key, base_plan_key)
        return f"Доплата за покращення CronoLex {base_label} до {plan_label}"
    if (quote or {}).get("kind") == "renewal":
        return f"Продовження підписки CronoLex {plan_label} на {int(period_months)} міс."
    return f"Підписка CronoLex {plan_label} на {int(period_months)} міс."


def supported_checkout_period_months(
    config: BillingCheckoutProviderConfig,
    enabled_period_months: list[int] | tuple[int, ...],
) -> list[int]:
    supported_periods = set(config.supported_period_months)
    return [int(period) for period in enabled_period_months if int(period) in supported_periods]


def build_checkout_plan_icon_url(
    config: BillingCheckoutProviderConfig,
    web_base_url: str,
    plan_key: str,
) -> str:
    return f"{str(web_base_url).rstrip('/')}{config.plan_icon_paths[plan_key]}"


def build_checkout_webhook_url(
    config: BillingCheckoutProviderConfig,
    api_base_url: str,
) -> str:
    return f"{str(api_base_url).rstrip('/')}{config.webhook_path}"


def _resolve_monobank_checkout_provider_config(
    runtime_settings: dict[str, Any],
    provider_settings: Any,
    *,
    validate_credentials: bool,
) -> BillingCheckoutProviderConfig:
    provider_mode = str(runtime_settings.get("monobank_mode") or "").strip()
    if provider_mode == MONOBANK_MODE_DISABLED:
        raise BillingRuntimeSettingsValidationError("Monobank checkout is disabled")
    if provider_mode not in {MONOBANK_MODE_TEST, MONOBANK_MODE_PRODUCTION}:
        raise BillingRuntimeSettingsValidationError("Unsupported Monobank mode")
    config = BillingCheckoutProviderConfig(
        provider_key=BILLING_PROVIDER_MONOBANK,
        provider_mode=provider_mode,
        webhook_path=MONOBANK_CHECKOUT_WEBHOOK_PATH,
        invoice_unavailable_detail=MONOBANK_CHECKOUT_UNAVAILABLE_DETAIL,
        plan_icon_paths=MONOBANK_PLAN_ICON_PATHS,
        supported_period_months=MONOBANK_SUPPORTED_PERIOD_MONTHS,
    )
    if validate_credentials:
        validate_checkout_provider_credentials(config, provider_settings)
    return config


def _resolve_instant_checkout_provider_config(
    runtime_settings: dict[str, Any],
    provider_settings: Any,
    *,
    validate_credentials: bool,
) -> BillingCheckoutProviderConfig:
    _ = (runtime_settings, provider_settings, validate_credentials)
    return BillingCheckoutProviderConfig(
        provider_key=BILLING_PROVIDER_INSTANT,
        provider_mode=BILLING_PROVIDER_INSTANT,
        webhook_path=INSTANT_CHECKOUT_WEBHOOK_PATH,
        invoice_unavailable_detail=INSTANT_CHECKOUT_UNAVAILABLE_DETAIL,
        plan_icon_paths=INSTANT_PLAN_ICON_PATHS,
        supported_period_months=MONOBANK_SUPPORTED_PERIOD_MONTHS,
    )


def _validate_monobank_checkout_provider_credentials(
    config: BillingCheckoutProviderConfig,
    provider_settings: Any,
) -> None:
    validate_monobank_mode_token(provider_settings, config.provider_mode)


def _validate_instant_checkout_provider_credentials(
    config: BillingCheckoutProviderConfig,
    provider_settings: Any,
) -> None:
    _ = (config, provider_settings)


CHECKOUT_PROVIDER_CONFIG_RESOLVERS: Mapping[str, CheckoutProviderConfigResolver] = {
    BILLING_PROVIDER_INSTANT: _resolve_instant_checkout_provider_config,
    BILLING_PROVIDER_MONOBANK: _resolve_monobank_checkout_provider_config,
}

CHECKOUT_PROVIDER_CREDENTIAL_VALIDATORS: Mapping[str, CheckoutProviderCredentialValidator] = {
    BILLING_PROVIDER_INSTANT: _validate_instant_checkout_provider_credentials,
    BILLING_PROVIDER_MONOBANK: _validate_monobank_checkout_provider_credentials,
}
