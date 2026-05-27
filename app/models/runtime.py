from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, BigInteger, CheckConstraint, DateTime, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ErrorLog(Base):
    __tablename__ = "error_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    level: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AppRuntimeState(Base):
    __tablename__ = "app_runtime_state"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TaskLog(Base):
    __tablename__ = "task_log"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'processing', 'success', 'error', 'fatal')",
            name="task_log_status_check",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    task_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="processing")
    user_uuid: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("user.uuid", ondelete="SET NULL"))
    source_type: Mapped[str | None] = mapped_column(Text)
    source_identifier: Mapped[str | None] = mapped_column(Text)
    import_job_id: Mapped[int | None] = mapped_column(BigInteger)
    description: Mapped[str | None] = mapped_column(Text)
    error_text: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    started: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class BotMessageLog(Base):
    __tablename__ = "bot_message_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(ForeignKey("user.telegram_user_id", ondelete="CASCADE"), nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    screen_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    error_text: Mapped[str | None] = mapped_column(Text)
    delete_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
