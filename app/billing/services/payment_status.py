from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, cast

from app.billing.services.provider_port import BillingProviderPaymentStatus
from app.domain.billing.constants import BILLING_TERMINAL_STATUSES
from app.subscriptions.paywall import PaywallService
from app.subscriptions.plan_limits import read_plan_limit_settings
from app.time_utils import TimeService

PostUpgradeRescanCallback = Callable[..., dict[str, Any] | None]


class BillingPaymentStatusBillingPort(Protocol):
    def create_payment_event(
        self,
        *,
        payment_id: int,
        event_type: str,
        source: str,
        provider_status: str,
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


class BillingPaymentStatusTerminalNotificationBillingPort(Protocol):
    def create_terminal_bot_notification(
        self,
        *,
        payment_id: int,
        status_snapshot: str,
        current_time: Any,
    ) -> Any: ...


class BillingPaymentStatusDatabasePort(Protocol):
    billing: BillingPaymentStatusBillingPort


def apply_provider_status_payload(
    db: BillingPaymentStatusDatabasePort,
    time_service: TimeService,
    *,
    payment: dict[str, Any],
    provider_status: BillingProviderPaymentStatus,
    payload: dict[str, Any],
    source: str,
    post_upgrade_rescan: PostUpgradeRescanCallback | None = None,
) -> dict[str, Any] | None:
    normalized_status = provider_status.provider_status
    current_time = time_service.now()
    internal_status = provider_status.internal_status
    previous_status = str(payment.get("status") or "")
    if should_ignore_provider_status(previous_status, internal_status):
        db.billing.create_payment_event(
            payment_id=int(payment["id"]),
            event_type="status_update_ignored",
            source=source,
            provider_status=normalized_status,
            payload_json={
                "reason": "stale_non_terminal_after_terminal_status",
                "current_status": previous_status,
                "provider_payload": payload,
            },
            current_time=current_time,
        )
        return payment
    paid_at = current_time if internal_status == "success" else None
    updated_payment = db.billing.update_payment_provider_status(
        int(payment["id"]),
        status=internal_status,
        provider_status_json=payload,
        failure_code=provider_status.failure_code,
        failure_reason=provider_status.failure_reason,
        paid_at=paid_at,
        current_time=current_time,
    )
    event_type = "terminal_status" if internal_status in BILLING_TERMINAL_STATUSES else "status_update"
    db.billing.create_payment_event(
        payment_id=int(payment["id"]),
        event_type=event_type,
        source=source,
        provider_status=normalized_status,
        payload_json=payload,
        current_time=current_time,
    )
    if internal_status == "success" and previous_status != "success" and updated_payment is not None:
        subscription = apply_subscription_purchase_projection(
            db,
            payment=updated_payment,
            current_time=current_time,
        )
        db.billing.create_payment_event(
            payment_id=int(payment["id"]),
            event_type="subscription_activated",
            source=source,
            provider_status=normalized_status,
            payload_json={"subscription": subscription},
            current_time=current_time,
        )
        maybe_queue_post_upgrade_google_doc_rescan(
            db,
            payment=updated_payment,
            subscription=subscription,
            current_time=current_time,
            source=source,
            provider_status=normalized_status,
            post_upgrade_rescan=post_upgrade_rescan,
        )
    if (
        previous_status == "success"
        and internal_status in {"failure", "reversed", "expired"}
        and updated_payment is not None
    ):
        revoked_subscription = reverse_subscription_purchase_projection(
            db,
            payment=payment,
            provider_status=normalized_status,
            current_time=current_time,
        )
        if revoked_subscription is not None:
            db.billing.create_payment_event(
                payment_id=int(payment["id"]),
                event_type="subscription_revoked",
                source=source,
                provider_status=normalized_status,
                payload_json={"subscription": revoked_subscription},
                current_time=current_time,
            )
    if internal_status in BILLING_TERMINAL_STATUSES and previous_status != internal_status and hasattr(
        db.billing,
        "create_terminal_bot_notification",
    ):
        terminal_notification_billing = cast(BillingPaymentStatusTerminalNotificationBillingPort, db.billing)
        terminal_notification_billing.create_terminal_bot_notification(
            payment_id=int(payment["id"]),
            status_snapshot=internal_status,
            current_time=current_time,
        )
    return updated_payment


def apply_subscription_purchase_projection(
    db: BillingPaymentStatusDatabasePort,
    *,
    payment: dict[str, Any],
    current_time,
) -> dict[str, Any]:
    result = db.billing.apply_subscription_purchase_for_payment(payment, current_time=current_time)
    subscription = result.get("subscription") if isinstance(result, dict) else None
    if subscription is not None:
        return subscription
    return result


def maybe_queue_post_upgrade_google_doc_rescan(
    db: BillingPaymentStatusDatabasePort,
    *,
    payment: dict[str, Any],
    subscription: Any | None,
    current_time: Any,
    source: str,
    provider_status: str,
    post_upgrade_rescan: PostUpgradeRescanCallback | None,
) -> None:
    if post_upgrade_rescan is None or not subscription_has_ai_import_mode(
        db,
        subscription=subscription,
        current_time=current_time,
    ):
        return
    try:
        result = post_upgrade_rescan(
            telegram_user_id=int(payment["telegram_user_id"]),
            user_uuid=str(payment["user_uuid"]),
            current_time=current_time,
        )
    except Exception as error:
        db.billing.create_payment_event(
            payment_id=int(payment["id"]),
            event_type="post_upgrade_google_doc_rescan_queue_failed",
            source=source,
            provider_status=provider_status,
            payload_json={
                "error_type": type(error).__name__,
                "error_text": str(error)[:1000],
            },
            current_time=current_time,
        )
        return
    if result is None:
        return
    db.billing.create_payment_event(
        payment_id=int(payment["id"]),
        event_type="post_upgrade_google_doc_rescan_queued",
        source=source,
        provider_status=provider_status,
        payload_json=result,
        current_time=current_time,
    )


def subscription_has_ai_import_mode(
    db: BillingPaymentStatusDatabasePort,
    *,
    subscription: Any | None,
    current_time: Any,
) -> bool:
    paywall = PaywallService(plan_limits=read_plan_limit_settings(db))
    return paywall.resolve(subscription, current_time=current_time).import_mode == "ai_new_words"


def reverse_subscription_purchase_projection(
    db: BillingPaymentStatusDatabasePort,
    *,
    payment: dict[str, Any],
    provider_status: str,
    current_time,
) -> dict[str, Any] | None:
    result = db.billing.reverse_subscription_purchase_projection_for_payment(
        int(payment["id"]),
        current_time=current_time,
    )
    if result is None:
        db.billing.create_payment_event(
            payment_id=int(payment["id"]),
            event_type="subscription_revocation_skipped",
            source="subscription_purchase_projection",
            provider_status=provider_status,
            payload_json={"reason": "missing_subscription_purchase"},
            current_time=current_time,
        )
        return None
    subscription = result.get("subscription") if isinstance(result, dict) else None
    return subscription or result


def should_ignore_provider_status(previous_status: str, internal_status: str) -> bool:
    if previous_status == "success" and internal_status in {"invoice_created", "processing"}:
        return True
    if previous_status in {"failure", "reversed", "expired"} and internal_status != previous_status:
        return True
    return False
