from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ClientWebCredential(Base):
    __tablename__ = "client_web_credential"

    user_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        primary_key=True,
    )
    password_hash: Mapped[str | None] = mapped_column(Text)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user = relationship("User")


class ClientWebOtpChallenge(Base):
    __tablename__ = "client_web_otp_challenge"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    otp_hash: Mapped[str] = mapped_column(Text, nullable=False)
    attempts_count: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    sent_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    sent_message_id: Mapped[int | None] = mapped_column(BigInteger)
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user = relationship("User")


class ClientWebSession(Base):
    __tablename__ = "client_web_session"

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


class ClientWebMagicLink(Base):
    __tablename__ = "client_web_magic_link"

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
