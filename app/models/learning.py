from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from app.models.base import Base
from app.models.dictionary import DictionaryEntry
from app.models.shared import LanguageLevel


class UserLevelRun(Base):
    __tablename__ = "user_level_run"
    __table_args__ = (
        UniqueConstraint("user_uuid", "level_id", "run_no", name="uq_user_level_run_user_level_run_no"),
        Index(
            "idx_user_level_run_active_unique",
            "user_uuid",
            "level_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("user.uuid", ondelete="CASCADE"), nullable=False)
    level_id: Mapped[int] = mapped_column(ForeignKey("language_level.id"), nullable=False)
    run_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    level: Mapped[LanguageLevel] = relationship()


class LearningSyllabusDomain(Base):
    __tablename__ = "learning_syllabus_domain"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    items: Mapped[list[LearningSyllabusItem]] = relationship(back_populates="domain")


class LearningSyllabusItem(Base):
    __tablename__ = "learning_syllabus_item"
    __table_args__ = (
        UniqueConstraint("level_id", "domain_id", "normalized_title", name="uq_learning_syllabus_item_level_domain_title"),
        Index("idx_learning_syllabus_item_level_domain_order", "level_id", "domain_id", "sort_order"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    level_id: Mapped[int] = mapped_column(ForeignKey("language_level.id", ondelete="CASCADE"), nullable=False)
    domain_id: Mapped[int] = mapped_column(ForeignKey("learning_syllabus_domain.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_title: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    level: Mapped[LanguageLevel] = relationship()
    domain: Mapped[LearningSyllabusDomain] = relationship(back_populates="items")


class GrammarTopic(Base):
    __tablename__ = "grammar_topics"
    __table_args__ = (Index("idx_grammar_topics_active_level_title", "is_active", "level", "title"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(Text, nullable=False)
    min_level: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LearningSession(Base):
    __tablename__ = "learning_session"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("user.uuid", ondelete="CASCADE"), nullable=False)
    language_level_id: Mapped[int] = mapped_column(ForeignKey("language_level.id"), nullable=False)
    level_run_id: Mapped[int | None] = mapped_column(ForeignKey("user_level_run.id", ondelete="SET NULL"))
    source_session_id: Mapped[int | None] = mapped_column(ForeignKey("learning_session.id", ondelete="SET NULL"))
    session_type: Mapped[str] = mapped_column(Text, nullable=False, server_default="regular")
    words_target_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    current_stage: Mapped[str] = mapped_column(Text, nullable=False)
    stage_queue_json: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    stage_position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    active_interface: Mapped[str] = mapped_column(Text, nullable=False, server_default="telegram_user")
    interface_revision: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    language_level: Mapped[LanguageLevel] = relationship()
    words: Mapped[list[LearningSessionWord]] = relationship(back_populates="session")


class LearningSessionWord(Base):
    __tablename__ = "learning_session_word"
    __table_args__ = (
        CheckConstraint("word_source IN ('core', 'user')", name="ck_learning_session_word_source"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("learning_session.id", ondelete="CASCADE"), nullable=False)
    word_source: Mapped[str] = mapped_column(Text, nullable=False, server_default="core")
    word_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    item_order: Mapped[int] = mapped_column(Integer, nullable=False)
    card_status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    en_uk_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    en_uk_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    uk_en_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    uk_en_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    gap_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    gap_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    session: Mapped[LearningSession] = relationship(back_populates="words")
    word: Mapped[DictionaryEntry] = relationship(
        primaryjoin=lambda: (DictionaryEntry.id == foreign(LearningSessionWord.word_id))
        & (LearningSessionWord.word_source == "core"),
        viewonly=True,
    )


class LearningAnswer(Base):
    __tablename__ = "learning_answer"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("learning_session.id", ondelete="CASCADE"), nullable=False)
    session_word_id: Mapped[int] = mapped_column(ForeignKey("learning_session_word.id", ondelete="CASCADE"), nullable=False)
    exercise_type: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    user_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TrainingSchedule(Base):
    __tablename__ = "training_schedule"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("user.uuid", ondelete="CASCADE"), nullable=False)
    schedule_type: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    schedule_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_code: Mapped[str | None] = mapped_column(Text)
    source_session_id: Mapped[int | None] = mapped_column(ForeignKey("learning_session.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    notified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
