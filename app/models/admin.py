from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AdminCredential(Base):
    __tablename__ = "admin_credential"

    user_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        primary_key=True,
    )
    password_hash: Mapped[str | None] = mapped_column(Text)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user = relationship("User")


class AdminOtpChallenge(Base):
    __tablename__ = "admin_otp_challenge"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    otp_hash: Mapped[str] = mapped_column(Text, nullable=False)
    attempts_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    sent_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    sent_message_id: Mapped[int | None] = mapped_column(BigInteger)
    previous_screen_id: Mapped[str | None] = mapped_column(Text)
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user = relationship("User")


class AdminMagicLink(Base):
    __tablename__ = "admin_magic_link"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    target_path: Mapped[str] = mapped_column(Text, nullable=False)
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user = relationship("User")


class AdminSession(Base):
    __tablename__ = "admin_session"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    session_token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    api_origin: Mapped[str | None] = mapped_column(Text)
    client_ip: Mapped[str | None] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(Text)
    device_fingerprint_hash: Mapped[str | None] = mapped_column(Text)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user = relationship("User")


class AdminBotRestore(Base):
    __tablename__ = "admin_bot_restore"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    previous_screen_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="queued")
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_text: Mapped[str | None] = mapped_column(Text)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user = relationship("User")


class WebLoginHistory(Base):
    __tablename__ = "web_login_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_uuid: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="SET NULL"),
    )
    username_attempted: Mapped[str | None] = mapped_column(Text)
    interface_context: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    api_origin: Mapped[str | None] = mapped_column(Text)
    api_path: Mapped[str | None] = mapped_column(Text)
    client_ip: Mapped[str | None] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(Text)
    device_fingerprint_hash: Mapped[str | None] = mapped_column(Text)
    details_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AppVersion(Base):
    __tablename__ = "app_version"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AppSetting(Base):
    __tablename__ = "app_setting"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ExternalProviderTaskSetting(Base):
    __tablename__ = "external_provider_task_setting"

    task_key: Mapped[str] = mapped_column(Text, primary_key=True)
    provider_key: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    last_status_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AIUsageSession(Base):
    __tablename__ = "ai_usage_session"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    task_key: Mapped[str] = mapped_column(Text, nullable=False)
    task_scope: Mapped[str] = mapped_column(Text, nullable=False)
    provider_key: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    actor_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_uuid: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    actor_group_title: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str | None] = mapped_column(Text)
    source_identifier: Mapped[str | None] = mapped_column(Text)
    import_job_id: Mapped[int | None] = mapped_column(BigInteger)
    task_log_id: Mapped[int | None] = mapped_column(BigInteger)
    batch_key: Mapped[str | None] = mapped_column(Text)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    estimated_cost_usd: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False, server_default="0")
    pricing_source: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="success")
    summary: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    started: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AIProviderPricingSnapshot(Base):
    __tablename__ = "ai_provider_pricing_snapshot"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    provider_key: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False)
    input_usd_per_1m: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    output_usd_per_1m: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
