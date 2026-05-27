from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, time, timedelta
from math import ceil
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from app.billing.helpers.amounts import amount_minor_to_uah
from app.billing.runtime_settings import (
    DOUBLE_TIME_FOR_PROJECT_SUPPORT_LABEL,
    BillingRuntimeSettingsValidationError,
    read_billing_runtime_settings,
)
from app.billing.services.checkout_provider_config import (
    BillingCheckoutProviderConfig,
    build_checkout_plan_icon_url,
    build_checkout_subscription_description,
    build_checkout_webhook_url,
    resolve_checkout_provider_config,
    supported_checkout_period_months,
    validate_checkout_provider_credentials,
)
from app.billing.services.payment_status import (
    PostUpgradeRescanCallback,
    apply_provider_status_payload,
)
from app.billing.services.provider_port import (
    BillingInvoiceStatusProviderFactory,
    BillingInvoiceStatusProviderPort,
    BillingProviderAuditContext,
    BillingProviderInvoiceCreateRequest,
    BillingProviderInvoiceLine,
    billing_provider_api_error_details,
    require_billing_invoice_status_provider_factory,
)
from app.domain.billing.constants import BILLING_PROVIDER_INSTANT, BILLING_PROVIDER_MONOBANK
from app.subscriptions.periods import add_months
from app.subscriptions.plans import (
    PLAN_FREE,
    PLAN_PREMIUM,
    PLAN_PREMIUM_PLUS,
    get_subscription_plan,
)
from app.subscriptions.user_entitlements import read_user_uuid
from app.time_utils import TimeService

CHECKOUT_PLAN_KEYS = {PLAN_PREMIUM, PLAN_PREMIUM_PLUS}
CHECKOUT_PLAN_RANKS = {
    PLAN_FREE: 0,
    PLAN_PREMIUM: 1,
    PLAN_PREMIUM_PLUS: 2,
}
PAYMENT_TERMINAL_MAINTENANCE_DETAIL = (
    "Вибачте, платіжний термінал зараз на технічному обслуговуванні. "
    "Оплата недоступна з 23:30 до 00:30. Будь ласка, зайдіть пізніше."
)
PAYMENT_TERMINAL_MAINTENANCE_START = time(23, 30)
PAYMENT_TERMINAL_MAINTENANCE_END = time(0, 30)
PAYMENT_TERMINAL_TIMEZONE = ZoneInfo("Europe/Kyiv")


class BillingCheckoutError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class BillingCheckoutValidationError(BillingCheckoutError):
    pass


class BillingCheckoutProfileNotFoundError(BillingCheckoutError):
    pass


class BillingCheckoutMaintenanceError(BillingCheckoutError):
    pass


class BillingCheckoutProviderUnavailableError(BillingCheckoutError):
    pass


class BillingCheckoutBillingPort(Protocol):
    def create_payment(
        self,
        *,
        user_uuid: str | uuid.UUID,
        telegram_user_id: int,
        plan_key: str,
        period_months: int,
        amount_minor: int,
        provider: str,
        provider_mode: str,
        provider_reference: str,
        return_url: str,
        source_path: str | None,
        expires_at: datetime | None,
        current_time: datetime,
    ) -> dict[str, Any]: ...

    def mark_payment_invoice_created(
        self,
        payment_id: int,
        *,
        provider_invoice_id: str,
        checkout_url: str,
        provider_status_json: dict[str, Any],
        current_time: datetime,
    ) -> dict[str, Any] | None: ...

    def update_payment_return_url(
        self,
        payment_id: int,
        *,
        return_url: str,
        current_time: datetime,
    ) -> dict[str, Any] | None: ...

    def create_offer_acceptance(
        self,
        *,
        payment_id: int,
        user_uuid: str | uuid.UUID,
        offer_text_hash: str,
        offer_version: str | None,
        accepted_ip: str | None,
        accepted_user_agent: str | None,
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


class BillingCheckoutSubscriptionPort(Protocol):
    def get_by_user_uuid(self, user_uuid: str | uuid.UUID) -> dict[str, Any] | None: ...


class BillingCheckoutUserProfilePort(Protocol):
    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None: ...


class BillingCheckoutAppSettingsPort(Protocol):
    def get_value(self, key: str) -> dict[str, Any] | None: ...


class BillingCheckoutSettingsPort(Protocol):
    app_api_base_url: str
    app_web_base_url: str


class BillingCheckoutDatabasePort(Protocol):
    billing: BillingCheckoutBillingPort
    subscriptions: BillingCheckoutSubscriptionPort
    user_profiles: BillingCheckoutUserProfilePort
    app_settings: BillingCheckoutAppSettingsPort
    settings: BillingCheckoutSettingsPort


class BillingCheckoutService:
    def __init__(
        self,
        db: BillingCheckoutDatabasePort,
        time_service: TimeService,
        *,
        billing_provider_factory: BillingInvoiceStatusProviderFactory | None = None,
        post_upgrade_rescan: PostUpgradeRescanCallback | None = None,
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.billing_provider_factory = (
            billing_provider_factory
            or None
        )
        self.post_upgrade_rescan = post_upgrade_rescan

    def get_offer(self) -> dict[str, Any]:
        settings = self._runtime_settings()
        offer_text = str(settings["offer_text"])
        return {
            "offer_text": offer_text,
            "offer_text_hash": hash_offer_text(offer_text),
            "offer_version": hash_offer_text(offer_text)[:16],
        }

    def create_checkout(
        self,
        user: dict[str, Any],
        *,
        plan_key: str,
        period_months: int,
        offer_accepted: bool,
        offer_text_hash: str,
        source_path: str | None,
        request_ip: str | None,
        user_agent: str | None,
    ) -> dict[str, Any]:
        if not offer_accepted:
            raise BillingCheckoutValidationError("offer_accepted must be true")
        normalized_plan = str(plan_key or "").strip()
        if normalized_plan == PLAN_FREE:
            raise BillingCheckoutValidationError("Free plan does not require checkout")
        if normalized_plan not in CHECKOUT_PLAN_KEYS:
            raise BillingCheckoutValidationError("plan_key must be one of: premium, premium_plus")
        get_subscription_plan(normalized_plan)

        settings = self._runtime_settings()
        if normalized_plan == PLAN_PREMIUM_PLUS and not settings["premium_plus_checkout_enabled"]:
            raise BillingCheckoutValidationError("Premium+ checkout is disabled")
        provider_config = self._checkout_provider_config(settings)
        current_time = self.time_service.now()
        if is_payment_terminal_maintenance_time(current_time, provider_config.provider_key):
            raise BillingCheckoutMaintenanceError(PAYMENT_TERMINAL_MAINTENANCE_DETAIL)
        self._validate_checkout_provider_credentials(provider_config)

        period = int(period_months)
        if period not in set(
            supported_checkout_period_months(
                provider_config, settings["enabled_period_months"]
            )
        ):
            raise BillingCheckoutValidationError("Unsupported billing period")
        price_uah = settings["plan_prices_uah"][normalized_plan].get(str(period))
        if price_uah is None:
            raise BillingCheckoutValidationError(
                "Price is not configured for selected plan and period"
            )

        user_uuid = self._read_user_uuid(user)
        subscription = self.db.subscriptions.get_by_user_uuid(user_uuid)
        quote = build_checkout_quote(
            settings,
            subscription,
            target_plan_key=normalized_plan,
            period_months=period,
            current_time=current_time,
        )
        amount_minor = int(quote["amount_minor"])
        provider_reference = f"clx-{uuid.uuid4().hex}"
        initial_return_url = self._base_return_url()
        webhook_url = build_checkout_webhook_url(
            provider_config,
            self.db.settings.app_api_base_url,
        )
        expires_at = current_time + timedelta(seconds=int(settings["invoice_validity_seconds"]))
        offer = self.get_offer()
        if str(offer_text_hash or "").strip() != offer["offer_text_hash"]:
            raise BillingCheckoutValidationError("offer_text_hash does not match current offer")
        self._validate_no_active_paid_downgrade(
            subscription,
            target_plan_key=normalized_plan,
            current_time=current_time,
        )
        description = build_checkout_subscription_description(
            provider_config,
            normalized_plan,
            period,
            quote=quote,
        )

        payment = self.db.billing.create_payment(
            user_uuid=user_uuid,
            telegram_user_id=int(user["telegram_user_id"]),
            plan_key=normalized_plan,
            period_months=period,
            amount_minor=amount_minor,
            provider=provider_config.provider_key,
            provider_mode=provider_config.provider_mode,
            provider_reference=provider_reference,
            return_url=initial_return_url,
            source_path=normalize_source_path(source_path),
            expires_at=expires_at,
            current_time=current_time,
        )
        return_url = self._return_url(int(payment["id"]))
        self.db.billing.update_payment_return_url(
            int(payment["id"]),
            return_url=return_url,
            current_time=current_time,
        )
        self.db.billing.create_offer_acceptance(
            payment_id=int(payment["id"]),
            user_uuid=user_uuid,
            offer_text_hash=offer["offer_text_hash"],
            offer_version=offer["offer_version"],
            accepted_ip=request_ip,
            accepted_user_agent=trim_optional(user_agent, 512),
            current_time=current_time,
        )
        try:
            invoice = self._billing_provider(
                provider_config.provider_key,
                provider_config.provider_mode,
            ).create_invoice(
                BillingProviderInvoiceCreateRequest(
                    amount_minor=amount_minor,
                    currency=980,
                    reference=provider_reference,
                    destination=description,
                    comment=f"Користувач: {user['telegram_user_id']}; платіж: {payment['id']}",
                    lines=(
                        BillingProviderInvoiceLine(
                            name=description,
                            quantity=1,
                            amount_minor=amount_minor,
                            code=normalized_plan,
                            total_minor=amount_minor,
                            icon_url=build_checkout_plan_icon_url(
                                provider_config,
                                self.db.settings.app_web_base_url,
                                normalized_plan,
                            ),
                        ),
                    ),
                    redirect_url=return_url,
                    webhook_url=webhook_url,
                    validity_seconds=int(settings["invoice_validity_seconds"]),
                ),
                audit_context=BillingProviderAuditContext(
                    source_place="checkout",
                    actor_user_uuid=user_uuid,
                    telegram_user_id=int(user["telegram_user_id"]),
                    payment_id=int(payment["id"]),
                    order_reference=provider_reference,
                    request_ip=request_ip,
                ),
            )
        except Exception as error:
            self._mark_checkout_invoice_failure(payment, error, provider_config=provider_config)
            raise BillingCheckoutProviderUnavailableError(
                provider_config.invoice_unavailable_detail
            ) from error
        updated_payment = self.db.billing.mark_payment_invoice_created(
            int(payment["id"]),
            provider_invoice_id=invoice.provider_invoice_id,
            checkout_url=invoice.checkout_url,
            provider_status_json={"invoice": invoice.payload, "checkout_quote": quote},
            current_time=self.time_service.now(),
        )
        activated_payment = self._apply_instant_checkout_status(
            updated_payment or payment,
            provider_config=provider_config,
        )
        return {
            "payment": serialize_payment_for_client(activated_payment),
            "checkout": {
                "page_url": invoice.checkout_url,
            },
            "order": {
                "plan_key": normalized_plan,
                "period_months": period,
                "amount_minor": amount_minor,
                "amount_uah": format_amount_minor_as_uah(amount_minor),
                "currency": 980,
                "quote": quote,
            },
        }

    def _validate_no_active_paid_downgrade(
        self,
        subscription: dict[str, Any] | None,
        *,
        target_plan_key: str,
        current_time: Any,
    ) -> None:
        current_plan_key = str((subscription or {}).get("plan_key") or PLAN_FREE)
        if CHECKOUT_PLAN_RANKS.get(current_plan_key, 0) <= CHECKOUT_PLAN_RANKS.get(
            target_plan_key, 0
        ):
            return
        if (
            subscription_remaining_seconds(
                (subscription or {}).get("end"), current_time=current_time
            )
            <= 0
        ):
            return
        raise BillingCheckoutValidationError(
            "Downgrade is available after the current paid period ends"
        )

    def _read_user_uuid(self, user: dict[str, Any]) -> str:
        user_uuid = read_user_uuid(user)
        if not user_uuid:
            profile = self.db.user_profiles.get_profile(int(user["telegram_user_id"]))
            user_uuid = read_user_uuid(profile)
        if not user_uuid:
            raise BillingCheckoutProfileNotFoundError("User profile not found")
        return str(user_uuid)

    def _runtime_settings(self) -> dict[str, Any]:
        try:
            return read_billing_runtime_settings(self.db)
        except BillingRuntimeSettingsValidationError as error:
            detail = str(error)
            if detail.startswith("billing_provider "):
                detail = "Unsupported billing provider"
            raise BillingCheckoutValidationError(detail) from error

    def _checkout_provider_config(
        self,
        settings: dict[str, Any],
    ) -> BillingCheckoutProviderConfig:
        try:
            return resolve_checkout_provider_config(
                settings,
                self.db.settings,
                validate_credentials=False,
            )
        except BillingRuntimeSettingsValidationError as error:
            raise BillingCheckoutValidationError(str(error)) from error

    def _validate_checkout_provider_credentials(
        self,
        provider_config: BillingCheckoutProviderConfig,
    ) -> None:
        try:
            validate_checkout_provider_credentials(provider_config, self.db.settings)
        except BillingRuntimeSettingsValidationError as error:
            raise BillingCheckoutValidationError(str(error)) from error

    def _apply_instant_checkout_status(
        self,
        payment: dict[str, Any],
        *,
        provider_config: BillingCheckoutProviderConfig,
    ) -> dict[str, Any]:
        if provider_config.provider_key != BILLING_PROVIDER_INSTANT:
            return payment
        provider = self._billing_provider(provider_config.provider_key, provider_config.provider_mode)
        payload = provider.get_invoice_status(
            str(payment["provider_invoice_id"]),
            audit_context=BillingProviderAuditContext(
                source_place="checkout",
                actor_user_uuid=str(payment["user_uuid"]),
                telegram_user_id=int(payment["telegram_user_id"]),
                payment_id=int(payment["id"]),
                order_reference=payment.get("provider_reference"),
                invoice_id=str(payment["provider_invoice_id"]),
            ),
        )
        return (
            apply_provider_status_payload(
                self.db,
                self.time_service,
                payment=payment,
                provider_status=provider.resolve_payment_status(payload),
                payload=payload,
                source="checkout",
                post_upgrade_rescan=self.post_upgrade_rescan,
            )
            or payment
        )

    def _billing_provider(
        self, provider_key: str, provider_mode: str
    ) -> BillingInvoiceStatusProviderPort:
        return require_billing_invoice_status_provider_factory(self.billing_provider_factory)(
            provider_key=provider_key,
            provider_mode=provider_mode,
        )

    def _mark_checkout_invoice_failure(
        self,
        payment: dict[str, Any],
        error: Exception,
        *,
        provider_config: BillingCheckoutProviderConfig,
    ) -> None:
        current_time = self.time_service.now()
        payload = {
            "source": "checkout",
            "error_type": type(error).__name__,
            "error_text": str(error)[:1000],
        }
        api_error_details = billing_provider_api_error_details(error)
        if api_error_details is not None:
            payload["provider_status_code"] = api_error_details.status_code
            payload["provider_error_code"] = api_error_details.error_code
        self.db.billing.update_payment_provider_status(
            int(payment["id"]),
            status="failure",
            provider_status_json=payload,
            failure_code=str(
                payload.get("provider_error_code") or "checkout_invoice_creation_failed"
            )[:128],
            failure_reason=provider_config.invoice_unavailable_detail,
            paid_at=None,
            current_time=current_time,
        )
        self.db.billing.create_payment_event(
            payment_id=int(payment["id"]),
            event_type="checkout_invoice_creation_failed",
            source="checkout",
            provider_status=None,
            payload_json=payload,
            current_time=current_time,
        )

    def _base_return_url(self) -> str:
        return f"{self.db.settings.app_web_base_url.rstrip('/')}/plans"

    def _return_url(self, payment_id: int) -> str:
        return f"{self._base_return_url()}?payment_id={int(payment_id)}&check_payment=true"


def hash_offer_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def format_amount_minor_as_uah(amount_minor: int) -> int | float:
    return amount_minor_to_uah(amount_minor)


def is_payment_terminal_maintenance_time(
    value: Any,
    provider_key: str | None = None,
) -> bool:
    if provider_key != BILLING_PROVIDER_MONOBANK:
        return False
    if value.tzinfo is None:
        kyiv_time = value.replace(tzinfo=PAYMENT_TERMINAL_TIMEZONE).time()
    else:
        kyiv_time = value.astimezone(PAYMENT_TERMINAL_TIMEZONE).time()
    return (
        kyiv_time >= PAYMENT_TERMINAL_MAINTENANCE_START
        or kyiv_time < PAYMENT_TERMINAL_MAINTENANCE_END
    )


def build_checkout_quote(
    settings: dict[str, Any],
    subscription: dict[str, Any] | None,
    *,
    target_plan_key: str,
    period_months: int,
    current_time: Any,
) -> dict[str, Any]:
    base_amount_uah = int(settings["plan_prices_uah"][target_plan_key][str(period_months)])
    granted_period_months = promoted_period_months(settings, period_months)
    current_plan_key = str((subscription or {}).get("plan_key") or PLAN_FREE)
    current_start = (subscription or {}).get("start")
    current_end = (subscription or {}).get("end")
    if (
        current_plan_key == target_plan_key
        and current_plan_key in CHECKOUT_PLAN_KEYS
        and subscription_remaining_seconds(current_end, current_time=current_time) > 0
    ):
        period_start = current_end
        period_end = add_months(period_start, granted_period_months)
        return with_checkout_promotion(
            settings,
            {
                "kind": "renewal",
                "target_plan_key": target_plan_key,
                "period_months": int(period_months),
                "granted_period_months": granted_period_months,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "current_period_end": current_end.isoformat(),
                "amount_minor": base_amount_uah * 100,
                "currency": 980,
            },
        )
    if (
        CHECKOUT_PLAN_RANKS.get(current_plan_key, 0) < CHECKOUT_PLAN_RANKS.get(target_plan_key, 0)
        and current_plan_key in CHECKOUT_PLAN_KEYS
        and subscription_remaining_seconds(current_end, current_time=current_time) > 0
    ):
        if current_start is None:
            current_start = current_time
        remaining_seconds = subscription_remaining_seconds(current_end, current_time=current_time)
        total_seconds = max(subscription_period_seconds(current_start, current_end), 1)
        current_monthly_uah = int(settings["plan_prices_uah"][current_plan_key]["1"])
        target_monthly_uah = int(settings["plan_prices_uah"][target_plan_key]["1"])
        upgrade_diff_uah = max(target_monthly_uah - current_monthly_uah, 0)
        remainder_amount_uah = max(ceil(upgrade_diff_uah * remaining_seconds / total_seconds), 1)
        extension_months = max(granted_period_months - 1, 0)
        extension_amount_uah = (
            max(base_amount_uah - target_monthly_uah, 0) if extension_months else 0
        )
        period_end = add_months(current_end, extension_months) if extension_months else current_end
        amount_uah = remainder_amount_uah + extension_amount_uah
        return with_checkout_promotion(
            settings,
            {
                "kind": "upgrade",
                "base_plan_key": current_plan_key,
                "target_plan_key": target_plan_key,
                "period_months": int(period_months),
                "granted_period_months": granted_period_months,
                "period_start": current_time.isoformat(),
                "period_end": period_end.isoformat(),
                "current_period_end": current_end.isoformat(),
                "remaining_seconds": remaining_seconds,
                "remainder_amount_minor": remainder_amount_uah * 100,
                "extension_months": extension_months,
                "paid_extension_months": max(int(period_months) - 1, 0),
                "extension_amount_minor": extension_amount_uah * 100,
                "amount_minor": amount_uah * 100,
                "currency": 980,
            },
        )
    return with_checkout_promotion(
        settings,
        {
            "kind": "subscription",
            "target_plan_key": target_plan_key,
            "period_months": int(period_months),
            "granted_period_months": granted_period_months,
            "amount_minor": base_amount_uah * 100,
            "currency": 980,
        },
    )


def promoted_period_months(settings: dict[str, Any], period_months: int) -> int:
    months = int(period_months)
    if bool(settings.get("double_time_for_project_support_enabled")):
        return months * 2
    return months


def with_checkout_promotion(settings: dict[str, Any], quote: dict[str, Any]) -> dict[str, Any]:
    if not bool(settings.get("double_time_for_project_support_enabled")):
        return quote
    return {
        **quote,
        "promotion": {
            "key": "double_time_for_project_support",
            "label": DOUBLE_TIME_FOR_PROJECT_SUPPORT_LABEL,
            "period_multiplier": 2,
        },
    }


def subscription_remaining_seconds(end: Any, *, current_time: Any) -> int:
    if end is None:
        return 0
    if getattr(end, "tzinfo", None) is None and getattr(current_time, "tzinfo", None) is not None:
        end = end.replace(tzinfo=current_time.tzinfo)
    if getattr(current_time, "tzinfo", None) is None and getattr(end, "tzinfo", None) is not None:
        current_time = current_time.replace(tzinfo=end.tzinfo)
    return max(int((end - current_time).total_seconds()), 0)


def subscription_period_seconds(start: Any, end: Any) -> int:
    if start is None or end is None:
        return 0
    if getattr(start, "tzinfo", None) is None and getattr(end, "tzinfo", None) is not None:
        start = start.replace(tzinfo=end.tzinfo)
    if getattr(end, "tzinfo", None) is None and getattr(start, "tzinfo", None) is not None:
        end = end.replace(tzinfo=start.tzinfo)
    return max(int((end - start).total_seconds()), 0)


def normalize_source_path(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    if len(normalized) > 512:
        raise BillingCheckoutValidationError("source_path must be at most 512 chars")
    if not normalized.startswith("/") or normalized.startswith("//"):
        raise BillingCheckoutValidationError("source_path must be an internal path starting with /")
    return normalized


def trim_optional(value: str | None, max_length: int) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    return normalized[:max_length]


def serialize_payment_for_client(payment: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": payment["id"],
        "status": payment["status"],
        "plan_key": payment["plan_key"],
        "period_months": payment["period_months"],
        "amount_minor": payment["amount_minor"],
        "currency": payment["currency"],
        "source_path": payment["source_path"],
    }
