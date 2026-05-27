from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.shared import LanguageLevel


class DictionaryEntry(Base):
    __tablename__ = "dictionary_entry"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_legacy_id: Mapped[int | None] = mapped_column(BigInteger)
    source_namespace: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    entry_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    word: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_word: Mapped[str] = mapped_column(Text, nullable=False)
    level_id: Mapped[int | None] = mapped_column(ForeignKey("language_level.id"))
    transcription: Mapped[str | None] = mapped_column(Text)
    translation_uk: Mapped[str] = mapped_column(Text, nullable=False)
    translation_ru: Mapped[str | None] = mapped_column(Text)
    translation_pl: Mapped[str | None] = mapped_column(Text)
    examples_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    entry_type: Mapped[str] = mapped_column(Text, nullable=False, default="word", server_default="word")
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_teacher_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    teacher_verified_by_user_uuid: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="SET NULL"),
    )
    teacher_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    audio_path: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    embedding_model: Mapped[str | None] = mapped_column(Text)
    is_embedding_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    level: Mapped[LanguageLevel | None] = relationship()
    part_of_speech_links: Mapped[list[DictionaryEntryPartOfSpeech]] = relationship(back_populates="entry")
    category_links: Mapped[list[DictionaryEntryCategory]] = relationship(back_populates="entry")


class DictionaryPartOfSpeech(Base):
    __tablename__ = "dictionary_part_of_speech"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DictionaryEntryPartOfSpeech(Base):
    __tablename__ = "dictionary_entry_part_of_speech"

    entry_id: Mapped[int] = mapped_column(ForeignKey("dictionary_entry.id", ondelete="CASCADE"), primary_key=True)
    part_of_speech_id: Mapped[int] = mapped_column(
        ForeignKey("dictionary_part_of_speech.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    entry: Mapped[DictionaryEntry] = relationship(back_populates="part_of_speech_links")
    part_of_speech: Mapped[DictionaryPartOfSpeech] = relationship()


class DictionaryCategory(Base):
    __tablename__ = "dictionary_category"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DictionaryEntryCategory(Base):
    __tablename__ = "dictionary_entry_category"

    entry_id: Mapped[int] = mapped_column(ForeignKey("dictionary_entry.id", ondelete="CASCADE"), primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("dictionary_category.id", ondelete="CASCADE"), primary_key=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    entry: Mapped[DictionaryEntry] = relationship(back_populates="category_links")
    category: Mapped[DictionaryCategory] = relationship()


class UserDictionaryEntry(Base):
    __tablename__ = "user_dictionary_entry"
    __table_args__ = (
        UniqueConstraint(
            "normalized_word",
            "part_of_speech",
            name="uq_user_dictionary_entry_normalized_word_pos",
        ),
        CheckConstraint(
            "status IN ("
            "'queued_for_details', "
            "'details_failed', "
            "'queued_for_audio', "
            "'audio_failed', "
            "'queued_for_embedding', "
            "'embedding_failed', "
            "'ready_for_rotation', "
            "'rejected', "
            "'archived', "
            "'promoted'"
            ")",
            name="ck_user_dictionary_entry_status",
        ),
        Index("idx_user_dictionary_entry_status", "status"),
        Index("idx_user_dictionary_entry_normalized_word", "normalized_word"),
        Index("idx_user_dictionary_entry_created_by_user", "created_by_user_uuid"),
        Index("idx_user_dictionary_entry_promoted", "promoted_dictionary_entry_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    word: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_word: Mapped[str] = mapped_column(Text, nullable=False)
    entry_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    entry_type: Mapped[str] = mapped_column(Text, nullable=False, default="word", server_default="word")
    part_of_speech: Mapped[str] = mapped_column(Text, nullable=False)
    level_id: Mapped[int | None] = mapped_column(ForeignKey("language_level.id"))
    transcription: Mapped[str | None] = mapped_column(Text)
    translation_uk: Mapped[str | None] = mapped_column(Text)
    translation_ru: Mapped[str | None] = mapped_column(Text)
    translation_pl: Mapped[str | None] = mapped_column(Text)
    examples_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    audio_path: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    embedding_model: Mapped[str | None] = mapped_column(Text)
    is_embedding_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="queued_for_details")
    promoted_dictionary_entry_id: Mapped[int | None] = mapped_column(ForeignKey("dictionary_entry.id", ondelete="SET NULL"))
    created_by_user_uuid: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("user.uuid", ondelete="SET NULL"))
    source_provider_status_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    level: Mapped[LanguageLevel | None] = relationship()
    promoted_dictionary_entry: Mapped[DictionaryEntry | None] = relationship()


class UserVocabularyImportJob(Base):
    __tablename__ = "user_vocabulary_import_job"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("user.uuid", ondelete="CASCADE"), nullable=False)
    task_log_id: Mapped[int | None] = mapped_column(ForeignKey("task_log.id", ondelete="SET NULL"))
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_identifier: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="queued")
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    processed_items: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    successful_items: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    failed_items: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    summary_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    publish_summary_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    processing_claimed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    completed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UserVocabularyImportItem(Base):
    __tablename__ = "user_vocabulary_import_item"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    import_job_id: Mapped[int] = mapped_column(ForeignKey("user_vocabulary_import_job.id", ondelete="CASCADE"), nullable=False)
    user_uuid: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("user.uuid", ondelete="CASCADE"), nullable=False)
    task_log_id: Mapped[int | None] = mapped_column(ForeignKey("task_log.id", ondelete="SET NULL"))
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    lookup_word: Mapped[str] = mapped_column(Text, nullable=False)
    translation_hint: Mapped[str | None] = mapped_column(Text)
    validated_lookup_word: Mapped[str | None] = mapped_column(Text)
    validated_part_of_speech: Mapped[str | None] = mapped_column(Text)
    validated_translation_uk: Mapped[str | None] = mapped_column(Text)
    validated_translation_ru: Mapped[str | None] = mapped_column(Text)
    validated_translation_pl: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    error_text: Mapped[str | None] = mapped_column(Text)
    existing_word_id: Mapped[int | None] = mapped_column(ForeignKey("dictionary_entry.id", ondelete="SET NULL"))
    user_dictionary_entry_id: Mapped[int | None] = mapped_column(ForeignKey("user_dictionary_entry.id", ondelete="SET NULL"))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserWordAssignment(Base):
    __tablename__ = "user_word_assignment"
    __table_args__ = (
        UniqueConstraint("user_uuid", "word_source", "word_id", name="uq_user_word_assignment_user_source_word"),
        CheckConstraint("word_source IN ('core', 'user')", name="ck_user_word_assignment_word_source"),
        CheckConstraint(
            "status IN ('waiting_for_entry', 'available_for_rotation', 'hidden', 'archived')",
            name="ck_user_word_assignment_status",
        ),
        CheckConstraint(
            "learning_state IN ('learning', 'needs_work', 'learned')",
            name="ck_user_word_assignment_learning_state",
        ),
        CheckConstraint(
            "priority_state IN ('none', 'pending', 'introduced', 'consumed')",
            name="ck_user_word_assignment_priority_state",
        ),
        Index("idx_user_word_assignment_user_status", "user_uuid", "status"),
        Index("idx_user_word_assignment_user_status_rank", "user_uuid", "status", "priority_rank"),
        Index("idx_user_word_assignment_user_learning", "user_uuid", "status", "learning_state"),
        Index("idx_user_word_assignment_user_review", "user_uuid", "status", "next_review_at", "review_priority"),
        Index("idx_user_word_assignment_user_priority_state", "user_uuid", "status", "priority_state", "priority_rank"),
        Index("idx_user_word_assignment_user_last_seen", "user_uuid", "status", "last_seen_at"),
        Index("idx_user_word_assignment_source_word", "word_source", "word_id"),
        Index("idx_user_word_assignment_import_job", "import_job_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("user.uuid", ondelete="CASCADE"), nullable=False)
    word_source: Mapped[str] = mapped_column(Text, nullable=False)
    word_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="available_for_rotation")
    priority_rank: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    priority_state: Mapped[str] = mapped_column(Text, nullable=False, server_default="none")
    is_known: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    learning_state: Mapped[str] = mapped_column(Text, nullable=False, server_default="learning")
    control_success_streak: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    review_priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_level_run_id: Mapped[int | None] = mapped_column(ForeignKey("user_level_run.id", ondelete="SET NULL"))
    last_completed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_stage: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    mistake_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    import_job_id: Mapped[int | None] = mapped_column(ForeignKey("user_vocabulary_import_job.id", ondelete="SET NULL"))
    import_item_id: Mapped[int | None] = mapped_column(ForeignKey("user_vocabulary_import_item.id", ondelete="SET NULL"))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
