from __future__ import annotations

from typing import Any

from app.domain.billing.constants import BILLING_PAYMENT_PROVIDERS, BILLING_PROVIDER_INSTANT
from app.subscriptions.plan_limits import CUSTOMER_PLAN_KEYS
from app.subscriptions.plans import PLAN_PREMIUM, PLAN_PREMIUM_PLUS

BILLING_RUNTIME_SETTINGS_KEY = "billing.runtime_settings"
BILLING_MONOBANK_MODE_SETTINGS_KEY = "billing.monobank_mode"

MONOBANK_MODE_DISABLED = "disabled"
MONOBANK_MODE_TEST = "test"
MONOBANK_MODE_PRODUCTION = "production"
MONOBANK_MODES = {MONOBANK_MODE_DISABLED, MONOBANK_MODE_TEST, MONOBANK_MODE_PRODUCTION}

BILLING_PERIOD_OPTIONS = {1, 3, 6, 12}
BILLING_PRICE_PLAN_KEYS = {PLAN_PREMIUM, PLAN_PREMIUM_PLUS}

DEFAULT_BILLING_OFFER_TEXT = """CronoLex subscription offer

By buying a paid CronoLex subscription, you get access to the selected paid plan for the selected period. The subscription starts only after the payment provider confirms successful payment.

The user is responsible for entering correct payment data on the payment provider checkout page. CronoLex does not store card numbers or bank authentication data.

If payment is still processing, CronoLex may notify the user about the final status in Telegram. Paid access is granted only after a successful payment status.

Paid subscriptions are not manually downgraded to the free plan by the user. After the paid period expires, CronoLex automatically switches the subscription back to the free plan.

Support questions can be sent through the support link configured in CronoLex.
"""

DOUBLE_TIME_FOR_PROJECT_SUPPORT_LABEL = "Двойное время за поддержку проекта"
DOUBLE_TIME_FOR_PROJECT_SUPPORT_TEXT = (
    "Вдячні вам за готовність підтримати проєкт монетою на ранньому етапі тестування. "
    "За будь-яку оплату ви отримаєте подвоєний час підписки."
)

DEFAULT_BILLING_RUNTIME_SETTINGS = {
    "billing_provider": BILLING_PROVIDER_INSTANT,
    "monobank_mode": MONOBANK_MODE_DISABLED,
    "double_time_for_project_support_enabled": False,
    "premium_plus_checkout_enabled": True,
    "enabled_period_months": [1, 3, 6, 12],
    "plan_prices_uah": {
        PLAN_PREMIUM: {"1": 10, "3": 30, "6": 60, "12": 120},
        PLAN_PREMIUM_PLUS: {"1": 20, "3": 60, "6": 120, "12": 240},
    },
    "invoice_validity_seconds": 3600,
    "webhook_wait_seconds": 20,
    "frontend_poll_interval_seconds": 10,
    "frontend_poll_timeout_seconds": 60,
    "long_processing_seconds": 60,
    "reconciliation_interval_seconds": 3600,
    "subscription_recovery_interval_seconds": 600,
    "receipt_retry_interval_seconds": 2,
    "receipt_retry_delay_seconds": 2,
    "receipt_retry_max_attempts": 3,
    "success_recheck_interval_days": 7,
    "success_recheck_hour": 6,
    "success_recheck_window_days": 7,
    "subscription_expiration_hour": 0,
    "offer_text": DEFAULT_BILLING_OFFER_TEXT,
}

BILLING_RUNTIME_SETTING_FIELDS = set(DEFAULT_BILLING_RUNTIME_SETTINGS)


class BillingRuntimeSettingsValidationError(ValueError):
    pass


def read_billing_runtime_settings(db: Any) -> dict[str, Any]:
    repository = getattr(db, "app_settings", None)
    stored = repository.get_value(BILLING_RUNTIME_SETTINGS_KEY) if repository is not None else None
    settings = normalize_billing_runtime_settings(stored or {}, partial=True)
    stored_mode = (
        repository.get_value(BILLING_MONOBANK_MODE_SETTINGS_KEY) if repository is not None else None
    )
    if stored_mode is not None:
        settings["monobank_mode"] = normalize_monobank_mode_settings(stored_mode)["monobank_mode"]
    return settings


def normalize_monobank_mode_settings(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise BillingRuntimeSettingsValidationError("monobank_mode settings must be an object")
    unknown_fields = set(value) - {"monobank_mode"}
    if unknown_fields:
        unknown_list = ", ".join(sorted(unknown_fields))
        raise BillingRuntimeSettingsValidationError(
            f"Unsupported monobank_mode settings fields: {unknown_list}"
        )
    raw_mode = value["monobank_mode"] if "monobank_mode" in value else MONOBANK_MODE_DISABLED
    return {
        "monobank_mode": _ensure_allowed_billing_value(
            str(raw_mode).strip(),
            MONOBANK_MODES,
            "monobank_mode",
        )
    }


def validate_monobank_mode_token(settings: Any, monobank_mode: str) -> None:
    if monobank_mode == MONOBANK_MODE_DISABLED:
        return
    if monobank_mode == MONOBANK_MODE_TEST:
        token = getattr(settings, "monobank_token_test", "")
        env_key = "MONOBANK_TOKEN_TEST"
    elif monobank_mode == MONOBANK_MODE_PRODUCTION:
        token = getattr(settings, "monobank_token", "")
        env_key = "MONOBANK_TOKEN"
    else:
        _ensure_allowed_billing_value(monobank_mode, MONOBANK_MODES, "monobank_mode")
        return
    if not str(token or "").strip():
        raise BillingRuntimeSettingsValidationError(f"{env_key} is not configured")


def normalize_billing_runtime_settings(value: Any, *, partial: bool = False) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BillingRuntimeSettingsValidationError("billing_settings must be an object")
    unknown_fields = set(value) - BILLING_RUNTIME_SETTING_FIELDS
    if unknown_fields:
        unknown_list = ", ".join(sorted(unknown_fields))
        raise BillingRuntimeSettingsValidationError(
            f"Unsupported billing_settings fields: {unknown_list}"
        )
    normalized = _clone_default_settings() if partial else {}
    for field_name, raw in value.items():
        if field_name == "billing_provider":
            normalized[field_name] = _ensure_allowed_billing_value(
                str(raw).strip(),
                BILLING_PAYMENT_PROVIDERS,
                field_name,
            )
        elif field_name == "monobank_mode":
            normalized[field_name] = _ensure_allowed_billing_value(
                str(raw).strip(), MONOBANK_MODES, field_name
            )
        elif field_name == "enabled_period_months":
            normalized[field_name] = _normalize_period_months(raw, field_name)
        elif field_name == "double_time_for_project_support_enabled":
            normalized[field_name] = _normalize_bool(raw, field_name)
        elif field_name == "premium_plus_checkout_enabled":
            normalized[field_name] = _normalize_bool(raw, field_name)
        elif field_name == "plan_prices_uah":
            base_prices = normalized.get(field_name) if partial else None
            normalized[field_name] = _normalize_plan_prices(raw, base=base_prices, partial=partial)
        elif field_name == "invoice_validity_seconds":
            normalized[field_name] = _normalize_int_range(
                raw, field_name, min_value=60, max_value=86_400
            )
        elif field_name == "webhook_wait_seconds":
            normalized[field_name] = _normalize_int_range(
                raw, field_name, min_value=1, max_value=120
            )
        elif field_name == "frontend_poll_interval_seconds":
            normalized[field_name] = _normalize_int_range(
                raw, field_name, min_value=1, max_value=30
            )
        elif field_name == "frontend_poll_timeout_seconds":
            normalized[field_name] = _normalize_int_range(
                raw, field_name, min_value=10, max_value=300
            )
        elif field_name == "long_processing_seconds":
            normalized[field_name] = _normalize_int_range(
                raw, field_name, min_value=10, max_value=600
            )
        elif field_name == "reconciliation_interval_seconds":
            normalized[field_name] = _normalize_int_range(
                raw, field_name, min_value=30, max_value=3600
            )
        elif field_name == "subscription_recovery_interval_seconds":
            normalized[field_name] = _normalize_int_range(
                raw, field_name, min_value=60, max_value=3600
            )
        elif field_name == "receipt_retry_interval_seconds":
            normalized[field_name] = _normalize_int_range(
                raw, field_name, min_value=2, max_value=3600
            )
        elif field_name == "receipt_retry_delay_seconds":
            normalized[field_name] = _normalize_int_range(
                raw, field_name, min_value=2, max_value=3600
            )
        elif field_name == "receipt_retry_max_attempts":
            normalized[field_name] = _normalize_int_range(
                raw, field_name, min_value=1, max_value=20
            )
        elif field_name == "success_recheck_interval_days":
            normalized[field_name] = _normalize_int_range(raw, field_name, min_value=1, max_value=7)
        elif field_name == "success_recheck_hour":
            normalized[field_name] = _normalize_int_range(
                raw, field_name, min_value=0, max_value=23
            )
        elif field_name == "success_recheck_window_days":
            normalized[field_name] = _normalize_int_range(
                raw, field_name, min_value=1, max_value=60
            )
        elif field_name == "subscription_expiration_hour":
            normalized[field_name] = _normalize_int_range(
                raw, field_name, min_value=0, max_value=23
            )
        elif field_name == "offer_text":
            normalized[field_name] = _normalize_offer_text(raw)
    return normalized


def _clone_default_settings() -> dict[str, Any]:
    return {
        **DEFAULT_BILLING_RUNTIME_SETTINGS,
        "enabled_period_months": list(DEFAULT_BILLING_RUNTIME_SETTINGS["enabled_period_months"]),
        "plan_prices_uah": {
            plan_key: dict(prices)
            for plan_key, prices in DEFAULT_BILLING_RUNTIME_SETTINGS["plan_prices_uah"].items()
        },
    }


def _normalize_period_months(raw: Any, field_name: str) -> list[int]:
    if not isinstance(raw, list) or not raw:
        raise BillingRuntimeSettingsValidationError(f"{field_name} must be a non-empty list")
    values = []
    for item in raw:
        value = int(
            _ensure_allowed_billing_value(
                _normalize_int(item, field_name), BILLING_PERIOD_OPTIONS, field_name
            )
        )
        if value not in values:
            values.append(value)
    return values


def _normalize_plan_prices(
    raw: Any, *, base: dict[str, dict[str, int]] | None = None, partial: bool
) -> dict[str, dict[str, int]]:
    if not isinstance(raw, dict):
        raise BillingRuntimeSettingsValidationError("plan_prices_uah must be an object")
    unknown_plans = set(raw) - BILLING_PRICE_PLAN_KEYS
    if unknown_plans:
        raise BillingRuntimeSettingsValidationError(
            f"Unsupported plan_prices_uah plans: {', '.join(sorted(unknown_plans))}"
        )
    source = base or DEFAULT_BILLING_RUNTIME_SETTINGS["plan_prices_uah"]
    normalized = {plan_key: dict(prices) for plan_key, prices in source.items()} if partial else {}
    for plan_key, raw_prices in raw.items():
        if plan_key not in CUSTOMER_PLAN_KEYS:
            raise BillingRuntimeSettingsValidationError(f"Unsupported billing plan: {plan_key}")
        if not isinstance(raw_prices, dict):
            raise BillingRuntimeSettingsValidationError(
                f"plan_prices_uah.{plan_key} must be an object"
            )
        base_prices = normalized.get(plan_key, {}) if partial else {}
        normalized[plan_key] = _normalize_period_prices(
            raw_prices, plan_key=plan_key, base=base_prices, partial=partial
        )
    return normalized


def _normalize_period_prices(
    raw: dict[Any, Any],
    *,
    plan_key: str,
    base: dict[str, int],
    partial: bool,
) -> dict[str, int]:
    normalized = dict(base) if partial else {}
    for raw_period, raw_price in raw.items():
        period = int(
            _ensure_allowed_billing_value(
                _normalize_int(raw_period, f"plan_prices_uah.{plan_key}.period"),
                BILLING_PERIOD_OPTIONS,
                "period",
            )
        )
        normalized[str(period)] = _normalize_int_range(
            raw_price,
            f"plan_prices_uah.{plan_key}.{period}",
            min_value=1,
            max_value=1_000_000,
        )
    if not partial:
        missing_periods = {str(period) for period in BILLING_PERIOD_OPTIONS} - set(normalized)
        if missing_periods:
            raise BillingRuntimeSettingsValidationError(
                f"plan_prices_uah.{plan_key} missing periods: {', '.join(sorted(missing_periods))}"
            )
    return normalized


def _normalize_offer_text(raw: Any) -> str:
    value = str(raw or "").strip()
    if len(value) < 20:
        raise BillingRuntimeSettingsValidationError("offer_text must be at least 20 chars")
    if len(value) > 50_000:
        raise BillingRuntimeSettingsValidationError("offer_text must be at most 50000 chars")
    return value


def _normalize_bool(raw: Any, field_name: str) -> bool:
    if not isinstance(raw, bool):
        raise BillingRuntimeSettingsValidationError(f"{field_name} must be a boolean")
    return raw


def _normalize_int_range(raw: Any, field_name: str, *, min_value: int, max_value: int) -> int:
    value = _normalize_int(raw, field_name)
    if value < min_value or value > max_value:
        raise BillingRuntimeSettingsValidationError(
            f"{field_name} must be between {min_value} and {max_value}"
        )
    return value


def _normalize_int(raw: Any, field_name: str) -> int:
    if isinstance(raw, bool):
        raise BillingRuntimeSettingsValidationError(f"{field_name} must be an integer")
    if isinstance(raw, float) and not raw.is_integer():
        raise BillingRuntimeSettingsValidationError(f"{field_name} must be an integer")
    if isinstance(raw, str):
        normalized = raw.strip()
        if not normalized or not normalized.isdecimal():
            raise BillingRuntimeSettingsValidationError(f"{field_name} must be an integer")
        raw = normalized
    try:
        return int(raw)
    except (TypeError, ValueError) as error:
        raise BillingRuntimeSettingsValidationError(f"{field_name} must be an integer") from error


def _ensure_allowed_billing_value(
    value: Any, allowed_values: set[Any] | list[Any] | tuple[Any, ...], field_name: str
) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise BillingRuntimeSettingsValidationError(f"{field_name} is required")
    if len(text) > 100:
        raise BillingRuntimeSettingsValidationError(f"{field_name} must be at most 100 characters")
    allowed = {str(item) for item in allowed_values}
    if text not in allowed:
        expected = ", ".join(sorted(allowed))
        raise BillingRuntimeSettingsValidationError(f"{field_name} must be one of: {expected}")
    return text
