from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ExerciseText(Base):
    __tablename__ = "exercise_texts"
    __table_args__ = (
        Index("idx_exercise_texts_status_updated", "status", "updated"),
        Index("idx_exercise_texts_difficulty_updated", "difficulty_band", "updated"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uuid: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    title: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    difficulty_band: Mapped[str | None] = mapped_column(Text)
    text_types: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list, server_default=text("'{}'::text[]"))
    content_jsonb: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_by_user_uuid: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("user.uuid", ondelete="SET NULL"))
    updated_by_user_uuid: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("user.uuid", ondelete="SET NULL"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    topic_links: Mapped[list[ExerciseTextTopic]] = relationship(
        back_populates="exercise_text",
        cascade="all, delete-orphan",
    )


class ExerciseTextTopic(Base):
    __tablename__ = "exercise_text_topics"

    exercise_text_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("exercise_texts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    grammar_topic_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("grammar_topics.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    exercise_text: Mapped[ExerciseText] = relationship(back_populates="topic_links")


class TTSVoice(Base):
    __tablename__ = "tts_voices"
    __table_args__ = (
        UniqueConstraint("provider", "code", name="uq_tts_voices_provider_code"),
        Index("idx_tts_voices_provider_active_order", "provider", "is_active", "sort_order", "display_name"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    language_code: Mapped[str] = mapped_column(Text, nullable=False)
    gender: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
