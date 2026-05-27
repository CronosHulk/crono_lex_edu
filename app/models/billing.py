from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.billing.constants import (
    BILLING_PAYMENT_PROVIDER_MODE_CHECK_SQL,
    BILLING_PROVIDER_KEY_CHECK_SQL,
)
from app.models.base import Base


class BillingPayment(Base):
    __tablename__ = "billing_payment"
    __table_args__ = (
        CheckConstraint(BILLING_PROVIDER_KEY_CHECK_SQL, name="ck_billing_payment_provider"),
        CheckConstraint(
            BILLING_PAYMENT_PROVIDER_MODE_CHECK_SQL,
            name="ck_billing_payment_provider_mode",
        ),
        CheckConstraint(
            "status IN ('created', 'invoice_created', 'processing', 'success', 'failure', 'expired', 'reversed')",
            name="ck_billing_payment_status",
        ),
        CheckConstraint("period_months IN (1, 3, 6, 12)", name="ck_billing_payment_period_months"),
        CheckConstraint("amount_minor > 0", name="ck_billing_payment_amount_minor"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("user.uuid", ondelete="CASCADE"), nullable=False)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    plan_key: Mapped[str] = mapped_column(Text, nullable=False)
    period_months: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[int] = mapped_column(Integer, nullable=False, server_default="980")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="created")
    provider: Mapped[str] = mapped_column(Text, nullable=False, server_default="monobank")
    provider_mode: Mapped[str] = mapped_column(Text, nullable=False)
    provider_invoice_id: Mapped[str | None] = mapped_column(Text, unique=True)
    provider_reference: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    checkout_url: Mapped[str | None] = mapped_column(Text)
    return_url: Mapped[str | None] = mapped_column(Text)
    source_path: Mapped[str | None] = mapped_column(Text)
    failure_code: Mapped[str | None] = mapped_column(Text)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    provider_status_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    success_rechecked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User")


class BillingPaymentEvent(Base):
    __tablename__ = "billing_payment_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    payment_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("billing_payment.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    provider_status: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    payment = relationship("BillingPayment")


class BillingSubscriptionPurchase(Base):
    __tablename__ = "billing_subscription_purchase"
    __table_args__ = (
        CheckConstraint("product_type IN ('subscription')", name="ck_billing_subscription_purchase_product_type"),
        CheckConstraint("period_months IN (1, 3, 6, 12)", name="ck_billing_subscription_purchase_period_months"),
        CheckConstraint("status IN ('active', 'reversed')", name="ck_billing_subscription_purchase_status"),
        CheckConstraint("amount_minor > 0", name="ck_billing_subscription_purchase_amount_minor"),
        UniqueConstraint("payment_id", name="uq_billing_subscription_purchase_payment"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    payment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("billing_payment.id", ondelete="CASCADE"), nullable=False)
    user_uuid: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("user.uuid", ondelete="CASCADE"), nullable=False)
    product_type: Mapped[str] = mapped_column(Text, nullable=False, server_default="subscription")
    product_key: Mapped[str] = mapped_column(Text, nullable=False)
    period_months: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[int] = mapped_column(Integer, nullable=False, server_default="980")
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    payment = relationship("BillingPayment")
    user = relationship("User")


class BillingReceipt(Base):
    __tablename__ = "billing_receipt"
    __table_args__ = (
        CheckConstraint("receipt_type IN ('receipt', 'fiscal_check')", name="ck_billing_receipt_type"),
        CheckConstraint("status IN ('new', 'process', 'done', 'failed', 'unavailable')", name="ck_billing_receipt_status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    payment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("billing_payment.id", ondelete="CASCADE"), nullable=False)
    receipt_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    provider_check_id: Mapped[str | None] = mapped_column(Text)
    fiscalization_source: Mapped[str | None] = mapped_column(Text)
    tax_url: Mapped[str | None] = mapped_column(Text)
    file_base64: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    bot_delivery_status: Mapped[str | None] = mapped_column(Text)
    bot_delivery_error: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    admin_alerted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    admin_alert_status: Mapped[str | None] = mapped_column(Text)
    admin_alert_error: Mapped[str | None] = mapped_column(Text)
    admin_alert_claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    payment = relationship("BillingPayment")


class BillingBotNotification(Base):
    __tablename__ = "billing_bot_notification"
    __table_args__ = (
        CheckConstraint("notification_type IN ('terminal_status')", name="ck_billing_bot_notification_type"),
        CheckConstraint("status IN ('queued', 'claimed', 'sent', 'skipped', 'failed')", name="ck_billing_bot_notification_status"),
        UniqueConstraint("payment_id", "notification_type", "status_snapshot", name="uq_billing_bot_notification_payment_type_status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    payment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("billing_payment.id", ondelete="CASCADE"), nullable=False)
    notification_type: Mapped[str] = mapped_column(Text, nullable=False)
    status_snapshot: Mapped[str] = mapped_column(Text, nullable=False, server_default="unknown")
    receipt_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="queued")
    error_text: Mapped[str | None] = mapped_column(Text)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    payment = relationship("BillingPayment")


class BillingOfferAcceptance(Base):
    __tablename__ = "billing_offer_acceptance"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    payment_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("billing_payment.id", ondelete="SET NULL"))
    user_uuid: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("user.uuid", ondelete="CASCADE"), nullable=False)
    offer_text_hash: Mapped[str] = mapped_column(Text, nullable=False)
    offer_version: Mapped[str | None] = mapped_column(Text)
    accepted_ip: Mapped[str | None] = mapped_column(Text)
    accepted_user_agent: Mapped[str | None] = mapped_column(Text)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    payment = relationship("BillingPayment")
    user = relationship("User")


class MonobankAuditLog(Base):
    __tablename__ = "monobank_audit_log"
    __table_args__ = (
        CheckConstraint("direction IN ('outgoing', 'incoming')", name="ck_monobank_audit_log_direction"),
        CheckConstraint("provider_mode IN ('test', 'production', 'unknown')", name="ck_monobank_audit_log_provider_mode"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    provider_mode: Mapped[str] = mapped_column(Text, nullable=False)
    source_place: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_uuid: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("user.uuid", ondelete="SET NULL"))
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger)
    payment_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("billing_payment.id", ondelete="SET NULL"))
    order_reference: Mapped[str | None] = mapped_column(Text)
    invoice_id: Mapped[str | None] = mapped_column(Text)
    request_method: Mapped[str | None] = mapped_column(Text)
    request_url: Mapped[str | None] = mapped_column(Text)
    request_ip: Mapped[str | None] = mapped_column(Text)
    request_headers_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    request_body_json: Mapped[dict | list | None] = mapped_column(JSON)
    request_raw_body: Mapped[str | None] = mapped_column(Text)
    response_status_code: Mapped[int | None] = mapped_column(Integer)
    response_headers_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    response_body_json: Mapped[dict | list | None] = mapped_column(JSON)
    response_raw_body: Mapped[str | None] = mapped_column(Text)
    signature_valid: Mapped[bool | None] = mapped_column(Boolean)
    processing_result: Mapped[str | None] = mapped_column(Text)
    error_text: Mapped[str | None] = mapped_column(Text)
    started: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    actor = relationship("User", foreign_keys=[actor_user_uuid])
    payment = relationship("BillingPayment")
