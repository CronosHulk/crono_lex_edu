from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, not_, or_, select
from sqlalchemy.exc import IntegrityError

from app.billing.helpers.amounts import amount_minor_to_uah
from app.billing.helpers.client_payments import build_public_payment_failure_message
from app.billing.helpers.receipt_notifications import (
    build_public_receipt_url,
    receipt_file_base64_is_valid,
)
from app.data_access.filtering import normalize_filter_values
from app.data_access.subscriptions import (
    MONTHLY_PLAN_KEYS,
    SubscriptionRepository,
    subscription_to_dict,
)
from app.domain.billing.constants import BILLING_PROVIDER_MONOBANK
from app.domain.billing.constants import BILLING_TERMINAL_STATUSES as _BILLING_TERMINAL_STATUSES
from app.models import (
    BillingBotNotification,
    BillingOfferAcceptance,
    BillingPayment,
    BillingPaymentEvent,
    BillingSubscriptionPurchase,
    MonobankAuditLog,
    UserSubscription,
)
from app.models.billing import BillingReceipt
from app.orm import SessionManager
from app.subscriptions.periods import add_months


def billing_payment_to_dict(row: BillingPayment) -> dict[str, Any]:
    return {
        "id": row.id,
        "user_uuid": str(row.user_uuid),
        "telegram_user_id": row.telegram_user_id,
        "plan_key": row.plan_key,
        "period_months": row.period_months,
        "amount_minor": row.amount_minor,
        "currency": row.currency,
        "status": row.status,
        "provider": row.provider,
        "provider_mode": row.provider_mode,
        "provider_invoice_id": row.provider_invoice_id,
        "provider_reference": row.provider_reference,
        "checkout_url": row.checkout_url,
        "return_url": row.return_url,
        "source_path": row.source_path,
        "failure_code": row.failure_code,
        "failure_reason": row.failure_reason,
        "provider_status_json": row.provider_status_json or {},
        "expires_at": row.expires_at,
        "paid_at": row.paid_at,
        "success_rechecked_at": row.success_rechecked_at,
        "created": row.created,
        "updated": row.updated,
    }


def billing_offer_acceptance_to_dict(row: BillingOfferAcceptance) -> dict[str, Any]:
    return {
        "id": row.id,
        "payment_id": row.payment_id,
        "user_uuid": str(row.user_uuid),
        "offer_text_hash": row.offer_text_hash,
        "offer_version": row.offer_version,
        "accepted_ip": row.accepted_ip,
        "accepted_user_agent": row.accepted_user_agent,
        "created": row.created,
    }


def billing_payment_event_to_dict(row: BillingPaymentEvent) -> dict[str, Any]:
    return {
        "id": row.id,
        "payment_id": row.payment_id,
        "event_type": row.event_type,
        "source": row.source,
        "provider_status": row.provider_status,
        "payload_json": row.payload_json or {},
        "created": row.created,
    }


def jsonb_safe_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): jsonb_safe_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [jsonb_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return [jsonb_safe_value(item) for item in value]
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def billing_receipt_to_dict(row: BillingReceipt) -> dict[str, Any]:
    return {
        "id": row.id,
        "payment_id": row.payment_id,
        "receipt_type": row.receipt_type,
        "status": row.status,
        "provider_check_id": row.provider_check_id,
        "fiscalization_source": row.fiscalization_source,
        "tax_url": row.tax_url,
        "file_base64": row.file_base64,
        "payload_json": row.payload_json or {},
        "bot_delivery_status": row.bot_delivery_status,
        "bot_delivery_error": row.bot_delivery_error,
        "retry_count": row.retry_count,
        "next_retry_at": row.next_retry_at,
        "admin_alerted_at": row.admin_alerted_at,
        "admin_alert_status": row.admin_alert_status,
        "admin_alert_error": row.admin_alert_error,
        "admin_alert_claimed_at": row.admin_alert_claimed_at,
        "created": row.created,
        "updated": row.updated,
    }


def sanitize_client_receipt(row: dict[str, Any]) -> dict[str, Any]:
    status = str(row.get("status") or "")
    file_base64 = str(row.get("file_base64") or "").strip()
    is_done = status == "done"
    public_tax_url = build_public_receipt_url(row)
    has_file = bool(is_done and file_base64 and receipt_file_base64_is_valid(file_base64))
    return {
        "id": row["id"],
        "receipt_type": row["receipt_type"],
        "status": status,
        "tax_url": public_tax_url,
        "has_file": has_file,
        "created": row["created"],
        "updated": row["updated"],
    }


def sanitize_client_payment(row: BillingPayment, receipts: list[dict[str, Any]]) -> dict[str, Any]:
    checkout_quote = checkout_quote_from_provider_status(row.provider_status_json)
    return {
        "id": row.id,
        "plan_key": row.plan_key,
        "period_months": row.period_months,
        "granted_period_months": checkout_quote_granted_period_months(
            checkout_quote, row.period_months
        ),
        "amount_minor": row.amount_minor,
        "amount_uah": amount_minor_to_uah(row.amount_minor),
        "currency": row.currency,
        "status": row.status,
        "promotion_label": checkout_quote_promotion_label(checkout_quote),
        "failure_message": build_public_payment_failure_message(
            str(row.status),
            row.failure_reason,
        ),
        "paid_at": row.paid_at,
        "created": row.created,
        "receipts": receipts,
    }


def billing_bot_notification_to_dict(row: BillingBotNotification) -> dict[str, Any]:
    return {
        "id": row.id,
        "payment_id": row.payment_id,
        "notification_type": row.notification_type,
        "status_snapshot": row.status_snapshot,
        "receipt_ids": normalize_receipt_ids(row.receipt_ids_json),
        "status": row.status,
        "error_text": row.error_text,
        "claimed_at": row.claimed_at,
        "sent_at": row.sent_at,
        "created": row.created,
        "updated": row.updated,
    }


def billing_receipt_has_deliverable_artifact(row: BillingReceipt) -> bool:
    tax_url = str(row.tax_url or "").strip()
    file_base64 = str(row.file_base64 or "").strip()
    return bool(tax_url or (file_base64 and receipt_file_base64_is_valid(file_base64)))


def normalize_receipt_ids(values: Any) -> list[int]:
    if not isinstance(values, (list, tuple, set)):
        return []
    receipt_ids: set[int] = set()
    for value in values:
        try:
            receipt_id = int(value)
        except (TypeError, ValueError):
            continue
        if receipt_id > 0:
            receipt_ids.add(receipt_id)
    return sorted(receipt_ids)


def billing_subscription_purchase_to_dict(row: BillingSubscriptionPurchase) -> dict[str, Any]:
    return {
        "id": row.id,
        "payment_id": row.payment_id,
        "user_uuid": str(row.user_uuid),
        "product_type": row.product_type,
        "product_key": row.product_key,
        "period_months": row.period_months,
        "amount_minor": row.amount_minor,
        "currency": row.currency,
        "period_start": row.period_start,
        "period_end": row.period_end,
        "status": row.status,
        "reversed_at": row.reversed_at,
        "metadata_json": row.metadata_json or {},
        "created": row.created,
        "updated": row.updated,
    }


def checkout_quote_from_payment(payment: dict[str, Any]) -> dict[str, Any]:
    return checkout_quote_from_provider_status(payment.get("provider_status_json"))


def checkout_quote_from_provider_status(provider_payload: Any) -> dict[str, Any]:
    if not isinstance(provider_payload, dict):
        return {}
    quote = provider_payload.get("checkout_quote")
    return quote if isinstance(quote, dict) else {}


def checkout_quote_granted_period_months(quote: dict[str, Any], fallback_period_months: int) -> int:
    try:
        months = int(quote.get("granted_period_months"))
    except (TypeError, ValueError):
        return int(fallback_period_months)
    return months if months > 0 else int(fallback_period_months)


def checkout_quote_promotion_label(quote: dict[str, Any]) -> str | None:
    promotion = quote.get("promotion")
    if not isinstance(promotion, dict):
        return None
    label = str(promotion.get("label") or "").strip()
    return label or None


def parse_checkout_quote_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def merge_provider_status_with_checkout_quote(
    current_payload: dict[str, Any] | None,
    next_payload: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(current_payload, dict):
        return next_payload
    quote = current_payload.get("checkout_quote")
    if not isinstance(quote, dict):
        return next_payload
    return {
        "provider_payload": next_payload,
        "checkout_quote": quote,
    }


def monobank_audit_log_to_dict(row: MonobankAuditLog) -> dict[str, Any]:
    return {
        "id": row.id,
        "direction": row.direction,
        "provider_mode": row.provider_mode,
        "source_place": row.source_place,
        "actor_user_uuid": str(row.actor_user_uuid) if row.actor_user_uuid else None,
        "telegram_user_id": row.telegram_user_id,
        "payment_id": row.payment_id,
        "order_reference": row.order_reference,
        "invoice_id": row.invoice_id,
        "request_method": row.request_method,
        "request_url": row.request_url,
        "request_ip": row.request_ip,
        "request_headers_json": row.request_headers_json or {},
        "request_body_json": row.request_body_json,
        "request_raw_body": row.request_raw_body,
        "response_status_code": row.response_status_code,
        "response_headers_json": row.response_headers_json or {},
        "response_body_json": row.response_body_json,
        "response_raw_body": row.response_raw_body,
        "signature_valid": row.signature_valid,
        "processing_result": row.processing_result,
        "error_text": row.error_text,
        "started": row.started,
        "finished": row.finished,
        "duration_ms": row.duration_ms,
        "created": row.created,
    }


class BillingRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def create_payment(
        self,
        *,
        user_uuid: str | UUID,
        telegram_user_id: int,
        plan_key: str,
        period_months: int,
        amount_minor: int,
        provider: str = BILLING_PROVIDER_MONOBANK,
        provider_mode: str,
        provider_reference: str,
        return_url: str,
        source_path: str | None,
        expires_at: datetime | None,
        current_time: datetime,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            row = BillingPayment(
                user_uuid=UUID(str(user_uuid)),
                telegram_user_id=telegram_user_id,
                plan_key=plan_key,
                period_months=period_months,
                amount_minor=amount_minor,
                status="created",
                provider=provider,
                provider_mode=provider_mode,
                provider_reference=provider_reference,
                return_url=return_url,
                source_path=source_path,
                expires_at=expires_at,
                provider_status_json={},
                created=current_time,
                updated=current_time,
            )
            session.add(row)
            session.flush()
            return billing_payment_to_dict(row)

    def mark_payment_invoice_created(
        self,
        payment_id: int,
        *,
        provider_invoice_id: str,
        checkout_url: str,
        provider_status_json: dict[str, Any],
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(BillingPayment, payment_id)
            if row is None:
                return None
            row.provider_invoice_id = provider_invoice_id
            row.checkout_url = checkout_url
            row.provider_status_json = provider_status_json
            row.status = "invoice_created"
            row.updated = current_time
            return billing_payment_to_dict(row)

    def update_payment_return_url(
        self,
        payment_id: int,
        *,
        return_url: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(BillingPayment, payment_id)
            if row is None:
                return None
            row.return_url = return_url
            row.updated = current_time
            return billing_payment_to_dict(row)

    def create_offer_acceptance(
        self,
        *,
        payment_id: int,
        user_uuid: str | UUID,
        offer_text_hash: str,
        offer_version: str | None,
        accepted_ip: str | None,
        accepted_user_agent: str | None,
        current_time: datetime,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            row = BillingOfferAcceptance(
                payment_id=payment_id,
                user_uuid=UUID(str(user_uuid)),
                offer_text_hash=offer_text_hash,
                offer_version=offer_version,
                accepted_ip=accepted_ip,
                accepted_user_agent=accepted_user_agent,
                created=current_time,
            )
            session.add(row)
            session.flush()
            return billing_offer_acceptance_to_dict(row)

    def get_payment_by_provider_invoice_id(self, provider_invoice_id: str) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.scalar(
                select(BillingPayment).where(
                    BillingPayment.provider_invoice_id == provider_invoice_id
                )
            )
            return billing_payment_to_dict(row) if row is not None else None

    def get_payment_by_id(self, payment_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(BillingPayment, payment_id)
            return billing_payment_to_dict(row) if row is not None else None

    def list_non_terminal_payments(self, *, limit: int = 100) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(BillingPayment)
                .where(
                    BillingPayment.status.not_in(_BILLING_TERMINAL_STATUSES),
                    BillingPayment.provider_invoice_id.is_not(None),
                )
                .order_by(BillingPayment.updated.asc(), BillingPayment.id.asc())
                .limit(max(int(limit), 1))
            ).all()
            return [billing_payment_to_dict(row) for row in rows]

    def list_success_payments_missing_subscription_purchase_today(
        self,
        *,
        current_time: datetime,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return self.list_success_payments_requiring_subscription_recovery_today(
            current_time=current_time,
            limit=limit,
        )

    def list_success_payments_requiring_subscription_recovery_today(
        self,
        *,
        current_time: datetime,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        day_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(BillingPayment)
                .outerjoin(
                    BillingSubscriptionPurchase,
                    BillingSubscriptionPurchase.payment_id == BillingPayment.id,
                )
                .outerjoin(UserSubscription, UserSubscription.user_uuid == BillingPayment.user_uuid)
                .where(
                    BillingPayment.status == "success",
                    BillingPayment.paid_at.is_not(None),
                    BillingPayment.paid_at >= day_start,
                    BillingPayment.paid_at < day_end,
                    or_(
                        BillingSubscriptionPurchase.id.is_(None),
                        and_(
                            BillingSubscriptionPurchase.status == "active",
                            BillingSubscriptionPurchase.period_start <= current_time,
                            BillingSubscriptionPurchase.period_end > current_time,
                            or_(
                                UserSubscription.user_uuid.is_(None),
                                UserSubscription.plan_key
                                != BillingSubscriptionPurchase.product_key,
                                UserSubscription.start != BillingSubscriptionPurchase.period_start,
                                UserSubscription.end != BillingSubscriptionPurchase.period_end,
                            ),
                        ),
                    ),
                )
                .order_by(BillingPayment.paid_at.asc(), BillingPayment.id.asc())
                .limit(max(int(limit), 1))
            ).all()
            return [billing_payment_to_dict(row) for row in rows]

    def list_active_subscription_purchase_payments_requiring_projection(
        self,
        *,
        current_time: datetime,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(BillingPayment)
                .join(
                    BillingSubscriptionPurchase,
                    BillingSubscriptionPurchase.payment_id == BillingPayment.id,
                )
                .outerjoin(
                    UserSubscription,
                    UserSubscription.user_uuid == BillingSubscriptionPurchase.user_uuid,
                )
                .where(
                    BillingPayment.status == "success",
                    BillingSubscriptionPurchase.product_type == "subscription",
                    BillingSubscriptionPurchase.status == "active",
                    BillingSubscriptionPurchase.period_start <= current_time,
                    BillingSubscriptionPurchase.period_end > current_time,
                    or_(
                        UserSubscription.user_uuid.is_(None),
                        UserSubscription.plan_key != BillingSubscriptionPurchase.product_key,
                        UserSubscription.start != BillingSubscriptionPurchase.period_start,
                        UserSubscription.end != BillingSubscriptionPurchase.period_end,
                    ),
                )
                .order_by(
                    BillingSubscriptionPurchase.period_start.asc(),
                    BillingSubscriptionPurchase.id.asc(),
                )
                .limit(max(int(limit), 1))
            ).all()
            return [billing_payment_to_dict(row) for row in rows]

    def list_success_payments_due_for_recheck(
        self,
        *,
        current_time: datetime,
        window_days: int,
        interval_days: int,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        paid_after = current_time - timedelta(days=max(int(window_days), 1))
        recheck_before = current_time - timedelta(days=max(int(interval_days), 1))
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(BillingPayment)
                .where(
                    BillingPayment.status == "success",
                    BillingPayment.provider_invoice_id.is_not(None),
                    BillingPayment.paid_at.is_not(None),
                    BillingPayment.paid_at >= paid_after,
                    or_(
                        BillingPayment.success_rechecked_at.is_(None),
                        BillingPayment.success_rechecked_at <= recheck_before,
                    ),
                )
                .order_by(
                    BillingPayment.success_rechecked_at.asc().nullsfirst(),
                    BillingPayment.paid_at.asc(),
                )
                .limit(max(int(limit), 1))
            ).all()
            return [billing_payment_to_dict(row) for row in rows]

    def mark_payment_success_rechecked(self, payment_id: int, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(BillingPayment, payment_id)
            if row is None:
                return
            row.success_rechecked_at = current_time
            row.updated = current_time

    def get_subscription_purchase_by_payment_id(self, payment_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.scalar(
                select(BillingSubscriptionPurchase).where(
                    BillingSubscriptionPurchase.payment_id == payment_id
                )
            )
            return billing_subscription_purchase_to_dict(row) if row is not None else None

    def apply_subscription_purchase_for_payment(
        self,
        payment: dict[str, Any],
        *,
        current_time: datetime,
    ) -> dict[str, Any]:
        payment_id = int(payment["id"])
        user_uuid = UUID(str(payment["user_uuid"]))
        period_months = int(payment["period_months"])
        with self.session_manager.session() as session:
            row = session.scalar(
                select(BillingSubscriptionPurchase).where(
                    BillingSubscriptionPurchase.payment_id == payment_id
                )
            )
            if row is None:
                latest_end = session.scalar(
                    select(func.max(BillingSubscriptionPurchase.period_end)).where(
                        BillingSubscriptionPurchase.user_uuid == user_uuid,
                        BillingSubscriptionPurchase.product_type == "subscription",
                        BillingSubscriptionPurchase.status == "active",
                        BillingSubscriptionPurchase.period_end > current_time,
                    )
                )
                activation_time = payment.get("paid_at") or current_time
                checkout_quote = checkout_quote_from_payment(payment)
                granted_period_months = checkout_quote_granted_period_months(
                    checkout_quote, period_months
                )
                if checkout_quote.get("kind") == "upgrade":
                    period_start = (
                        parse_checkout_quote_datetime(checkout_quote.get("period_start"))
                        or activation_time
                    )
                    period_end = parse_checkout_quote_datetime(
                        checkout_quote.get("period_end")
                    ) or add_months(period_start, granted_period_months)
                elif checkout_quote.get("kind") == "renewal":
                    period_start = parse_checkout_quote_datetime(checkout_quote.get("period_start"))
                    if period_start is None:
                        period_start = (
                            latest_end
                            if latest_end is not None and latest_end > activation_time
                            else activation_time
                        )
                    period_end = parse_checkout_quote_datetime(
                        checkout_quote.get("period_end")
                    ) or add_months(period_start, granted_period_months)
                else:
                    period_start = (
                        latest_end
                        if latest_end is not None and latest_end > activation_time
                        else activation_time
                    )
                    period_end = add_months(period_start, granted_period_months)
                row = BillingSubscriptionPurchase(
                    payment_id=payment_id,
                    user_uuid=user_uuid,
                    product_type="subscription",
                    product_key=str(payment["plan_key"]),
                    period_months=period_months,
                    amount_minor=int(payment["amount_minor"]),
                    currency=int(payment["currency"]),
                    period_start=period_start,
                    period_end=period_end,
                    status="active",
                    metadata_json={
                        "provider_reference": payment.get("provider_reference"),
                        "provider_invoice_id": payment.get("provider_invoice_id"),
                        "checkout_quote": checkout_quote,
                        "granted_period_months": granted_period_months,
                    },
                    created=current_time,
                    updated=current_time,
                )
                session.add(row)
                try:
                    session.flush()
                except IntegrityError:
                    session.rollback()
                    row = session.scalar(
                        select(BillingSubscriptionPurchase).where(
                            BillingSubscriptionPurchase.payment_id == payment_id
                        )
                    )
                    if row is None:
                        raise
            subscription = self._project_subscription_for_user_in_session(
                session,
                user_uuid,
                current_time=current_time,
            )
            return {
                "purchase": billing_subscription_purchase_to_dict(row),
                "subscription": subscription_to_dict(subscription)
                if subscription is not None
                else None,
            }

    def reverse_subscription_purchase_projection_for_payment(
        self,
        payment_id: int,
        *,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.scalar(
                select(BillingSubscriptionPurchase).where(
                    BillingSubscriptionPurchase.payment_id == payment_id
                )
            )
            if row is None:
                return None
            if row.status != "reversed":
                row.status = "reversed"
                row.reversed_at = current_time
                row.updated = current_time
            subscription = self._project_subscription_for_user_in_session(
                session,
                row.user_uuid,
                current_time=current_time,
            )
            return {
                "purchase": billing_subscription_purchase_to_dict(row),
                "subscription": subscription_to_dict(subscription)
                if subscription is not None
                else None,
            }

    def _project_subscription_for_user_in_session(
        self,
        session: Any,
        user_uuid: UUID,
        *,
        current_time: datetime,
    ) -> UserSubscription | None:
        active_purchase = session.scalar(
            select(BillingSubscriptionPurchase)
            .where(
                BillingSubscriptionPurchase.user_uuid == user_uuid,
                BillingSubscriptionPurchase.product_type == "subscription",
                BillingSubscriptionPurchase.status == "active",
                BillingSubscriptionPurchase.period_start <= current_time,
                BillingSubscriptionPurchase.period_end > current_time,
            )
            .order_by(
                BillingSubscriptionPurchase.period_start.desc(),
                BillingSubscriptionPurchase.id.desc(),
            )
            .limit(1)
        )
        subscription_repository = SubscriptionRepository(self.session_manager)
        if active_purchase is not None:
            return subscription_repository.apply_paid_subscription_projection_for_user_in_session(
                session,
                user_uuid,
                plan_key=active_purchase.product_key,
                period_start=active_purchase.period_start,
                period_end=active_purchase.period_end,
                current_time=current_time,
            )
        current_subscription = session.get(UserSubscription, user_uuid)
        if current_subscription is not None and current_subscription.plan_key in MONTHLY_PLAN_KEYS:
            return subscription_repository.downgrade_to_free_for_user_in_session(
                session,
                user_uuid,
                current_time=current_time,
            )
        return current_subscription

    def get_subscription_projection_for_user(
        self,
        user_uuid: str | UUID,
        *,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        resolved_uuid = UUID(str(user_uuid))
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(BillingSubscriptionPurchase)
                .where(
                    BillingSubscriptionPurchase.user_uuid == resolved_uuid,
                    BillingSubscriptionPurchase.product_type == "subscription",
                    BillingSubscriptionPurchase.status == "active",
                    BillingSubscriptionPurchase.period_end > current_time,
                )
                .order_by(
                    BillingSubscriptionPurchase.period_start.asc(),
                    BillingSubscriptionPurchase.id.asc(),
                )
            ).all()
            if not rows:
                return None
            latest = max(rows, key=lambda row: (row.period_end, row.id))
            return {
                "user_uuid": str(resolved_uuid),
                "plan_key": latest.product_key,
                "start": min(row.period_start for row in rows),
                "end": max(row.period_end for row in rows),
                "purchase_ids": [row.id for row in rows],
            }

    def list_client_payments_for_user(
        self,
        user_uuid: str | UUID,
        *,
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
        resolved_uuid = UUID(str(user_uuid))
        offset = (max(page, 1) - 1) * page_size
        with self.session_manager.session() as session:
            filters = [BillingPayment.user_uuid == resolved_uuid]
            total = int(session.scalar(select(func.count(BillingPayment.id)).where(*filters)) or 0)
            payments = session.scalars(
                select(BillingPayment)
                .where(*filters)
                .order_by(BillingPayment.created.desc(), BillingPayment.id.desc())
                .offset(offset)
                .limit(page_size)
            ).all()
            payment_ids = [row.id for row in payments]
            receipts_by_payment: dict[int, list[dict[str, Any]]] = {
                payment_id: [] for payment_id in payment_ids
            }
            if payment_ids:
                receipts = session.scalars(
                    select(BillingReceipt)
                    .where(BillingReceipt.payment_id.in_(payment_ids))
                    .order_by(BillingReceipt.created.desc(), BillingReceipt.id.desc())
                ).all()
                for receipt in receipts:
                    receipts_by_payment.setdefault(int(receipt.payment_id), []).append(
                        sanitize_client_receipt(billing_receipt_to_dict(receipt))
                    )
            return {
                "items": [
                    sanitize_client_payment(payment, receipts_by_payment.get(int(payment.id), []))
                    for payment in payments
                ],
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            }

    def list_admin_payments(
        self,
        *,
        page: int,
        page_size: int,
        status: str | list[str] | None = None,
        provider_mode: str | list[str] | None = None,
        user_id: str | None = None,
        search: str = "",
    ) -> dict[str, Any]:
        offset = (max(page, 1) - 1) * page_size
        with self.session_manager.session() as session:
            filters = []
            status_values = normalize_filter_values(status)
            if status_values:
                filters.append(BillingPayment.status.in_(status_values))
            mode_values = normalize_filter_values(provider_mode)
            if mode_values:
                filters.append(BillingPayment.provider_mode.in_(mode_values))
            if user_id:
                filters.append(BillingPayment.user_uuid == user_id)
            normalized_search = search.strip().lower()
            if normalized_search:
                like_value = f"%{normalized_search}%"
                filters.append(
                    or_(
                        func.lower(BillingPayment.plan_key).like(like_value),
                        func.lower(BillingPayment.provider_reference).like(like_value),
                        func.lower(BillingPayment.provider_invoice_id).like(like_value),
                        func.lower(BillingPayment.failure_code).like(like_value),
                        func.lower(BillingPayment.failure_reason).like(like_value),
                    )
                )

            query = select(BillingPayment).where(*filters)
            count_query = select(func.count(BillingPayment.id)).where(*filters)
            total = int(session.scalar(count_query) or 0)
            rows = session.scalars(
                query.order_by(BillingPayment.created.desc(), BillingPayment.id.desc())
                .offset(offset)
                .limit(page_size)
            ).all()
            return {
                "items": [billing_payment_to_dict(row) for row in rows],
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            }

    def get_admin_payment_detail(self, payment_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(BillingPayment, payment_id)
            if row is None:
                return None
            events = session.scalars(
                select(BillingPaymentEvent)
                .where(BillingPaymentEvent.payment_id == payment_id)
                .order_by(BillingPaymentEvent.created.desc(), BillingPaymentEvent.id.desc())
            ).all()
            receipts = session.scalars(
                select(BillingReceipt)
                .where(BillingReceipt.payment_id == payment_id)
                .order_by(BillingReceipt.created.desc(), BillingReceipt.id.desc())
            ).all()
            offer_acceptances = session.scalars(
                select(BillingOfferAcceptance)
                .where(BillingOfferAcceptance.payment_id == payment_id)
                .order_by(BillingOfferAcceptance.created.desc(), BillingOfferAcceptance.id.desc())
            ).all()
            audit_logs = session.scalars(
                select(MonobankAuditLog)
                .where(MonobankAuditLog.payment_id == payment_id)
                .order_by(MonobankAuditLog.created.desc(), MonobankAuditLog.id.desc())
                .limit(50)
            ).all()
            bot_notifications = session.scalars(
                select(BillingBotNotification)
                .where(BillingBotNotification.payment_id == payment_id)
                .order_by(BillingBotNotification.created.desc(), BillingBotNotification.id.desc())
            ).all()
            return {
                "payment": billing_payment_to_dict(row),
                "events": [billing_payment_event_to_dict(item) for item in events],
                "receipts": [billing_receipt_to_dict(item) for item in receipts],
                "offer_acceptances": [
                    billing_offer_acceptance_to_dict(item) for item in offer_acceptances
                ],
                "monobank_audit_logs": [monobank_audit_log_to_dict(item) for item in audit_logs],
                "bot_notifications": [
                    billing_bot_notification_to_dict(item) for item in bot_notifications
                ],
            }

    def list_payment_receipts(self, payment_id: int) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(BillingReceipt)
                .where(BillingReceipt.payment_id == payment_id)
                .order_by(BillingReceipt.created.desc(), BillingReceipt.id.desc())
            ).all()
            return [billing_receipt_to_dict(row) for row in rows]

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
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            row = BillingReceipt(
                payment_id=payment_id,
                receipt_type=receipt_type,
                status=status,
                provider_check_id=provider_check_id,
                fiscalization_source=fiscalization_source,
                tax_url=tax_url,
                file_base64=file_base64,
                payload_json=payload_json or {},
                bot_delivery_status=bot_delivery_status,
                retry_count=max(int(retry_count), 0),
                next_retry_at=next_retry_at,
                created=current_time,
                updated=current_time,
            )
            session.add(row)
            session.flush()
            return billing_receipt_to_dict(row)

    def list_success_payments_requiring_receipt_retry(
        self,
        *,
        current_time: datetime,
        limit: int = 100,
        max_attempts: int | None = None,
    ) -> list[dict[str, Any]]:
        fiscal_check_exists = (
            select(BillingReceipt.id)
            .where(
                BillingReceipt.payment_id == BillingPayment.id,
                BillingReceipt.receipt_type == "fiscal_check",
            )
            .exists()
        )
        retryable_receipt_filters = [
            BillingReceipt.payment_id == BillingPayment.id,
            not_(
                and_(
                    BillingReceipt.receipt_type == "fiscal_check",
                    func.lower(func.coalesce(BillingReceipt.fiscalization_source, ""))
                    == "checkbox",
                    BillingReceipt.provider_check_id.is_not(None),
                    BillingReceipt.provider_check_id != "",
                )
            ),
            or_(
                BillingReceipt.status.in_(("new", "process", "failed", "unavailable")),
                and_(
                    BillingReceipt.status == "done",
                    BillingReceipt.tax_url.is_(None),
                    BillingReceipt.file_base64.is_(None),
                ),
            ),
            or_(
                BillingReceipt.next_retry_at.is_(None), BillingReceipt.next_retry_at <= current_time
            ),
        ]
        if max_attempts is not None:
            retryable_receipt_filters.append(BillingReceipt.retry_count < max(int(max_attempts), 1))
        retryable_fiscal_check_exists = (
            select(BillingReceipt.id)
            .where(
                BillingReceipt.receipt_type == "fiscal_check",
                *retryable_receipt_filters,
            )
            .exists()
        )
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(BillingPayment)
                .where(
                    BillingPayment.status == "success",
                    BillingPayment.provider_mode != "test",
                    BillingPayment.provider_invoice_id.is_not(None),
                    or_(
                        ~fiscal_check_exists,
                        retryable_fiscal_check_exists,
                    ),
                )
                .order_by(BillingPayment.paid_at.asc().nullsfirst(), BillingPayment.id.asc())
                .limit(max(int(limit), 1))
                .with_for_update(skip_locked=True)
            ).all()
            return [billing_payment_to_dict(row) for row in rows]

    def claim_due_receipt_delivery_notifications(
        self,
        *,
        current_time: datetime,
        limit: int = 50,
        claim_timeout_minutes: int = 10,
        exclude_receipt_ids: set[int] | None = None,
    ) -> list[dict[str, Any]]:
        stale_claimed_before = current_time - timedelta(minutes=max(int(claim_timeout_minutes), 1))
        excluded_ids = {int(value) for value in (exclude_receipt_ids or set())}
        with self.session_manager.session() as session:
            statement = (
                select(BillingReceipt)
                .where(
                    BillingReceipt.status == "done",
                    BillingReceipt.file_base64.is_not(None),
                    or_(
                        BillingReceipt.bot_delivery_status.is_(None),
                        BillingReceipt.bot_delivery_status == "queued",
                        BillingReceipt.bot_delivery_status == "failed",
                        (
                            (BillingReceipt.bot_delivery_status == "claimed")
                            & (BillingReceipt.updated <= stale_claimed_before)
                        ),
                    ),
                )
                .order_by(BillingReceipt.created.asc(), BillingReceipt.id.asc())
                .limit(max(int(limit), 1))
                .with_for_update(skip_locked=True)
            )
            if excluded_ids:
                statement = statement.where(BillingReceipt.id.not_in(excluded_ids))
            rows = session.scalars(statement).all()
            deliverable_rows = []
            for row in rows:
                if not billing_receipt_has_deliverable_artifact(row):
                    row.status = "unavailable"
                    row.bot_delivery_status = None
                    row.bot_delivery_error = "Receipt artifact is not deliverable"
                    row.updated = current_time
                    continue
                row.bot_delivery_status = "claimed"
                row.bot_delivery_error = None
                row.updated = current_time
                deliverable_rows.append(row)
            return [billing_receipt_to_dict(row) for row in deliverable_rows]

    def mark_receipt_delivery_sent(self, receipt_id: int, *, current_time: datetime) -> None:
        self._mark_receipt_delivery(receipt_id, status="sent", current_time=current_time)

    def mark_receipt_delivery_failed(
        self, receipt_id: int, *, error_text: str, current_time: datetime
    ) -> None:
        self._mark_receipt_delivery(
            receipt_id, status="failed", error_text=error_text, current_time=current_time
        )

    def _mark_receipt_delivery(
        self,
        receipt_id: int,
        *,
        status: str,
        current_time: datetime,
        error_text: str | None = None,
    ) -> None:
        with self.session_manager.session() as session:
            row = session.get(BillingReceipt, receipt_id)
            if row is None:
                return
            if row.bot_delivery_status == "sent" and status == "failed":
                return
            if status == "sent" and not billing_receipt_has_deliverable_artifact(row):
                row.status = "unavailable"
                row.bot_delivery_status = None
                row.bot_delivery_error = "Receipt artifact is not deliverable"
                row.updated = current_time
                return
            row.bot_delivery_status = status
            row.bot_delivery_error = error_text
            row.updated = current_time

    def mark_payment_receipt_deliveries_sent(
        self, payment_id: int, *, current_time: datetime
    ) -> None:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(BillingReceipt).where(
                    BillingReceipt.payment_id == payment_id,
                    BillingReceipt.status == "done",
                    or_(
                        BillingReceipt.tax_url.is_not(None), BillingReceipt.file_base64.is_not(None)
                    ),
                    or_(
                        BillingReceipt.bot_delivery_status.is_(None),
                        BillingReceipt.bot_delivery_status.in_(("queued", "claimed", "failed")),
                    ),
                )
            ).all()
            for row in rows:
                if not billing_receipt_has_deliverable_artifact(row):
                    row.status = "unavailable"
                    row.bot_delivery_status = None
                    row.bot_delivery_error = "Receipt artifact is not deliverable"
                    row.updated = current_time
                    continue
                row.bot_delivery_status = "sent"
                row.bot_delivery_error = None
                row.updated = current_time

    def mark_receipt_deliveries_sent_by_ids(
        self, receipt_ids: list[int], *, current_time: datetime
    ) -> None:
        normalized_ids = normalize_receipt_ids(receipt_ids)
        if not normalized_ids:
            return
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(BillingReceipt).where(
                    BillingReceipt.id.in_(normalized_ids),
                    BillingReceipt.status == "done",
                    or_(
                        BillingReceipt.tax_url.is_not(None), BillingReceipt.file_base64.is_not(None)
                    ),
                    or_(
                        BillingReceipt.bot_delivery_status.is_(None),
                        BillingReceipt.bot_delivery_status.in_(("queued", "claimed", "failed")),
                    ),
                )
            ).all()
            for row in rows:
                if not billing_receipt_has_deliverable_artifact(row):
                    row.status = "unavailable"
                    row.bot_delivery_status = None
                    row.bot_delivery_error = "Receipt artifact is not deliverable"
                    row.updated = current_time
                    continue
                row.bot_delivery_status = "sent"
                row.bot_delivery_error = None
                row.updated = current_time

    def get_bot_notification_by_id(self, notification_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(BillingBotNotification, notification_id)
            return billing_bot_notification_to_dict(row) if row is not None else None

    def set_bot_notification_receipt_ids(
        self,
        notification_id: int,
        receipt_ids: list[int],
        *,
        current_time: datetime,
    ) -> None:
        normalized_ids = normalize_receipt_ids(receipt_ids)
        with self.session_manager.session() as session:
            row = session.get(BillingBotNotification, notification_id)
            if row is None:
                return
            row.receipt_ids_json = normalized_ids
            row.updated = current_time

    def claim_receipts_requiring_admin_alert(
        self,
        *,
        current_time: datetime,
        max_retry_count: int,
        limit: int = 50,
        claim_timeout_minutes: int = 10,
    ) -> list[dict[str, Any]]:
        stale_claimed_before = current_time - timedelta(minutes=max(int(claim_timeout_minutes), 1))
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(BillingReceipt)
                .join(BillingPayment, BillingPayment.id == BillingReceipt.payment_id)
                .where(
                    BillingPayment.status == "success",
                    BillingPayment.provider_mode != "test",
                    BillingReceipt.receipt_type.in_(("receipt", "fiscal_check")),
                    BillingReceipt.status.in_(("failed", "unavailable")),
                    BillingReceipt.retry_count >= max(int(max_retry_count), 1),
                    BillingReceipt.admin_alerted_at.is_(None),
                    or_(
                        BillingReceipt.admin_alert_status.is_(None),
                        BillingReceipt.admin_alert_status == "queued",
                        BillingReceipt.admin_alert_status == "failed",
                        (
                            (BillingReceipt.admin_alert_status == "claimed")
                            & (BillingReceipt.admin_alert_claimed_at <= stale_claimed_before)
                        ),
                    ),
                )
                .order_by(BillingReceipt.updated.asc(), BillingReceipt.id.asc())
                .limit(max(int(limit), 1))
                .with_for_update(skip_locked=True)
            ).all()
            for row in rows:
                row.admin_alert_status = "claimed"
                row.admin_alert_error = None
                row.admin_alert_claimed_at = current_time
                row.updated = current_time
            return [billing_receipt_to_dict(row) for row in rows]

    def mark_receipt_admin_alerted(self, receipt_id: int, *, current_time: datetime) -> None:
        self.mark_receipt_admin_alert_sent(receipt_id, current_time=current_time)

    def mark_receipt_admin_alert_sent(self, receipt_id: int, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(BillingReceipt, receipt_id)
            if row is None:
                return
            row.admin_alert_status = "sent"
            row.admin_alert_error = None
            row.admin_alerted_at = current_time
            row.updated = current_time

    def mark_receipt_admin_alert_failed(
        self, receipt_id: int, *, error_text: str, current_time: datetime
    ) -> None:
        with self.session_manager.session() as session:
            row = session.get(BillingReceipt, receipt_id)
            if row is None:
                return
            if row.admin_alerted_at is not None or row.admin_alert_status == "sent":
                return
            row.admin_alert_status = "failed"
            row.admin_alert_error = error_text
            row.updated = current_time

    def create_terminal_bot_notification(
        self,
        *,
        payment_id: int,
        status_snapshot: str,
        current_time: datetime,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            row = session.scalar(
                select(BillingBotNotification).where(
                    BillingBotNotification.payment_id == payment_id,
                    BillingBotNotification.notification_type == "terminal_status",
                    BillingBotNotification.status_snapshot == status_snapshot,
                )
            )
            if row is None:
                row = BillingBotNotification(
                    payment_id=payment_id,
                    notification_type="terminal_status",
                    status_snapshot=status_snapshot,
                    status="queued",
                    created=current_time,
                    updated=current_time,
                )
                session.add(row)
                try:
                    session.flush()
                except IntegrityError:
                    session.rollback()
                    row = session.scalar(
                        select(BillingBotNotification).where(
                            BillingBotNotification.payment_id == payment_id,
                            BillingBotNotification.notification_type == "terminal_status",
                            BillingBotNotification.status_snapshot == status_snapshot,
                        )
                    )
                    if row is None:
                        raise
            return billing_bot_notification_to_dict(row)

    def claim_due_bot_notifications(
        self,
        *,
        current_time: datetime,
        limit: int = 50,
        claim_timeout_minutes: int = 10,
    ) -> list[dict[str, Any]]:
        stale_claimed_before = current_time - timedelta(minutes=max(int(claim_timeout_minutes), 1))
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(BillingBotNotification)
                .where(
                    or_(
                        BillingBotNotification.status == "queued",
                        (
                            (BillingBotNotification.status == "claimed")
                            & (BillingBotNotification.claimed_at <= stale_claimed_before)
                        ),
                    )
                )
                .order_by(BillingBotNotification.created.asc(), BillingBotNotification.id.asc())
                .limit(max(int(limit), 1))
                .with_for_update(skip_locked=True)
            ).all()
            for row in rows:
                row.status = "claimed"
                row.claimed_at = current_time
                row.updated = current_time
            return [billing_bot_notification_to_dict(row) for row in rows]

    def mark_bot_notification_sent(self, notification_id: int, *, current_time: datetime) -> None:
        self._mark_bot_notification(notification_id, status="sent", current_time=current_time)

    def mark_bot_notification_skipped(
        self, notification_id: int, *, error_text: str, current_time: datetime
    ) -> None:
        self._mark_bot_notification(
            notification_id, status="skipped", error_text=error_text, current_time=current_time
        )

    def mark_bot_notification_failed(
        self, notification_id: int, *, error_text: str, current_time: datetime
    ) -> None:
        self._mark_bot_notification(
            notification_id, status="failed", error_text=error_text, current_time=current_time
        )

    def _mark_bot_notification(
        self,
        notification_id: int,
        *,
        status: str,
        current_time: datetime,
        error_text: str | None = None,
    ) -> None:
        with self.session_manager.session() as session:
            row = session.get(BillingBotNotification, notification_id)
            if row is None:
                return
            row.status = status
            row.error_text = error_text
            row.updated = current_time
            if status == "sent":
                row.sent_at = current_time

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
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(BillingPayment, payment_id)
            if row is None:
                return None
            row.status = status
            row.provider_status_json = jsonb_safe_value(
                merge_provider_status_with_checkout_quote(
                    row.provider_status_json,
                    provider_status_json,
                )
            )
            row.failure_code = failure_code
            row.failure_reason = failure_reason
            if paid_at is not None:
                row.paid_at = paid_at
            row.updated = current_time
            return billing_payment_to_dict(row)

    def create_payment_event(
        self,
        *,
        payment_id: int | None,
        event_type: str,
        source: str,
        provider_status: str | None,
        payload_json: dict[str, Any],
        current_time: datetime,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            row = BillingPaymentEvent(
                payment_id=payment_id,
                event_type=event_type,
                source=source,
                provider_status=provider_status,
                payload_json=jsonb_safe_value(payload_json),
                created=current_time,
            )
            session.add(row)
            session.flush()
            return billing_payment_event_to_dict(row)

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
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            row = MonobankAuditLog(
                direction=direction,
                provider_mode=provider_mode,
                source_place=source_place,
                actor_user_uuid=UUID(str(actor_user_uuid)) if actor_user_uuid else None,
                telegram_user_id=telegram_user_id,
                payment_id=payment_id,
                order_reference=order_reference,
                invoice_id=invoice_id,
                request_method=request_method,
                request_url=request_url,
                request_ip=request_ip,
                request_headers_json=request_headers_json or {},
                request_body_json=request_body_json,
                request_raw_body=request_raw_body,
                response_status_code=response_status_code,
                response_headers_json=response_headers_json or {},
                response_body_json=response_body_json,
                response_raw_body=response_raw_body,
                signature_valid=signature_valid,
                processing_result=processing_result,
                error_text=error_text,
                started=started,
                finished=finished,
                duration_ms=duration_ms,
            )
            session.add(row)
            session.flush()
            return monobank_audit_log_to_dict(row)

    def list_admin_monobank_audit_logs(
        self,
        *,
        page: int,
        page_size: int,
        direction: str | list[str] | None = None,
        provider_mode: str | list[str] | None = None,
        payment_id: int | None = None,
        invoice_id: str | None = None,
        search: str = "",
    ) -> dict[str, Any]:
        offset = (max(page, 1) - 1) * page_size
        with self.session_manager.session() as session:
            filters = []
            direction_values = normalize_filter_values(direction)
            if direction_values:
                filters.append(MonobankAuditLog.direction.in_(direction_values))
            mode_values = normalize_filter_values(provider_mode)
            if mode_values:
                filters.append(MonobankAuditLog.provider_mode.in_(mode_values))
            if payment_id is not None:
                filters.append(MonobankAuditLog.payment_id == payment_id)
            if invoice_id:
                filters.append(MonobankAuditLog.invoice_id == invoice_id)
            normalized_search = search.strip().lower()
            if normalized_search:
                like_value = f"%{normalized_search}%"
                filters.append(
                    or_(
                        func.lower(MonobankAuditLog.source_place).like(like_value),
                        func.lower(MonobankAuditLog.order_reference).like(like_value),
                        func.lower(MonobankAuditLog.invoice_id).like(like_value),
                        func.lower(MonobankAuditLog.request_method).like(like_value),
                        func.lower(MonobankAuditLog.request_url).like(like_value),
                        func.lower(MonobankAuditLog.request_ip).like(like_value),
                        func.lower(MonobankAuditLog.processing_result).like(like_value),
                        func.lower(MonobankAuditLog.error_text).like(like_value),
                    )
                )

            query = select(MonobankAuditLog).where(*filters)
            count_query = select(func.count(MonobankAuditLog.id)).where(*filters)
            total = int(session.scalar(count_query) or 0)
            rows = session.scalars(
                query.order_by(MonobankAuditLog.created.desc(), MonobankAuditLog.id.desc())
                .offset(offset)
                .limit(page_size)
            ).all()
            return {
                "items": [monobank_audit_log_to_dict(row) for row in rows],
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            }

    def get_admin_monobank_audit_log_detail(self, audit_log_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(MonobankAuditLog, audit_log_id)
            return monobank_audit_log_to_dict(row) if row is not None else None
