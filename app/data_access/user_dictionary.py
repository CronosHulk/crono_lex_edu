from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.data_access.serialization import normalize_examples_json
from app.data_access.user_dictionary_admin_reads import (
    get_admin_entry_detail as get_user_dictionary_admin_entry_detail,
)
from app.data_access.user_dictionary_admin_reads import (
    get_admin_filter_metadata as get_user_dictionary_admin_filter_metadata,
)
from app.data_access.user_dictionary_admin_reads import (
    list_admin_entries as list_user_dictionary_admin_entries,
)
from app.data_access.user_dictionary_assignments import (
    archive_assignments_for_entry as archive_user_dictionary_assignments_for_entry,
)
from app.data_access.user_dictionary_assignments import (
    count_assignments_for_word as count_user_dictionary_assignments_for_word,
)
from app.data_access.user_dictionary_assignments import (
    create_assignment as create_user_dictionary_assignment,
)
from app.data_access.user_dictionary_assignments import (
    list_assignments_for_user as list_user_dictionary_assignments_for_user,
)
from app.data_access.user_dictionary_assignments import (
    mark_assignments_available_for_entry as mark_user_dictionary_assignments_available_for_entry,
)
from app.data_access.user_dictionary_assignments import (
    normalize_user_word_source,
    user_word_assignment_to_dict,
)
from app.data_access.user_dictionary_promotion import promote_user_dictionary_entry_to_core
from app.domain.user_dictionary.constants import (
    USER_DICTIONARY_AUDIO_FAILED,
    USER_DICTIONARY_DETAILS_FAILED,
    USER_DICTIONARY_EMBEDDING_FAILED,
    USER_DICTIONARY_QUEUED_AUDIO,
    USER_DICTIONARY_QUEUED_DETAILS,
    USER_DICTIONARY_QUEUED_EMBEDDING,
    USER_DICTIONARY_READY,
    USER_DICTIONARY_REJECTED,
    USER_DICTIONARY_STATUSES,
    USER_WORD_ASSIGNMENT_AVAILABLE,
    USER_WORD_ASSIGNMENT_WAITING,
    USER_WORD_SOURCE_CORE,
    USER_WORD_SOURCE_USER,
)
from app.helpers.audio_files import delete_audio_file_if_under_roots
from app.models import DictionaryEntry, UserDictionaryEntry, UserWordAssignment
from app.orm import SessionManager
from app.reference.dictionary_entries import (
    dictionary_entry_type_from_part_of_speech,
    normalize_dictionary_entry_type,
    normalize_dictionary_part_of_speech,
)
from app.storage.audio import AudioStorageProvider

__all__ = [
    "USER_DICTIONARY_AUDIO_FAILED",
    "USER_DICTIONARY_DETAILS_FAILED",
    "USER_DICTIONARY_QUEUED_AUDIO",
    "USER_DICTIONARY_QUEUED_DETAILS",
    "USER_DICTIONARY_QUEUED_EMBEDDING",
    "USER_DICTIONARY_EMBEDDING_FAILED",
    "USER_DICTIONARY_READY",
    "USER_DICTIONARY_REJECTED",
    "USER_DICTIONARY_STATUSES",
    "USER_WORD_ASSIGNMENT_AVAILABLE",
    "USER_WORD_ASSIGNMENT_WAITING",
    "USER_WORD_SOURCE_CORE",
    "USER_WORD_SOURCE_USER",
    "UserDictionaryRepository",
    "normalize_user_word_source",
    "user_dictionary_entry_to_dict",
    "user_dictionary_entry_to_lesson_word",
    "user_word_assignment_to_dict",
]


def user_dictionary_entry_to_dict(row: UserDictionaryEntry) -> dict[str, Any]:
    level = getattr(row, "level", None)
    return {
        "id": row.id,
        "word": row.word,
        "normalized_word": row.normalized_word,
        "entry_key": row.entry_key,
        "entry_type": normalize_dictionary_entry_type(row.entry_type or "word"),
        "part_of_speech": row.part_of_speech,
        "level_id": row.level_id,
        "level_title": getattr(level, "title", None),
        "transcription": row.transcription,
        "translation_uk": row.translation_uk,
        "translation_ru": row.translation_ru,
        "translation_pl": row.translation_pl,
        "examples_json": normalize_examples_json(row.examples_json),
        "audio_path": row.audio_path,
        "has_embedding": row.embedding is not None,
        "embedding_model": row.embedding_model,
        "is_embedding_ready": bool(row.is_embedding_ready),
        "status": row.status,
        "promoted_dictionary_entry_id": row.promoted_dictionary_entry_id,
        "created_by_user_uuid": str(row.created_by_user_uuid) if row.created_by_user_uuid else None,
        "source_provider_status_json": dict(row.source_provider_status_json or {}),
        "created": row.created,
        "updated": row.updated,
    }


def user_dictionary_entry_to_lesson_word(
    row: UserDictionaryEntry,
    *,
    review_priority: int = 0,
    is_priority: bool = False,
) -> dict[str, Any]:
    return {
        "id": row.id,
        "word_source": USER_WORD_SOURCE_USER,
        "word_id": row.id,
        "word": row.word,
        "part_of_speech": row.part_of_speech,
        "parts_of_speech": [row.part_of_speech] if row.part_of_speech else [],
        "categories": [],
        "phonetic_us": row.transcription,
        "audio_path": row.audio_path,
        "examples_json": normalize_examples_json(row.examples_json),
        "level_id": row.level_id,
        "level_title": getattr(getattr(row, "level", None), "title", None),
        "has_embedding": row.embedding is not None,
        "translation_uk": row.translation_uk,
        "translation_ru": row.translation_ru,
        "translation_pl": row.translation_pl,
        "entry_type": normalize_dictionary_entry_type(row.entry_type or "word"),
        "is_archived": row.status == "archived",
        "is_teacher_verified": False,
        "teacher_verified_by_user_uuid": None,
        "teacher_verified_at": None,
        "review_priority": review_priority,
        "is_priority": is_priority,
    }


class UserDictionaryRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def find_entry_by_word(self, word: str) -> dict[str, Any] | None:
        normalized_word = _normalize_lookup_word(word)
        with self.session_manager.session() as session:
            row = session.scalar(
                select(UserDictionaryEntry)
                .options(selectinload(UserDictionaryEntry.level))
                .where(func.lower(UserDictionaryEntry.normalized_word) == normalized_word)
                .order_by(UserDictionaryEntry.id.asc())
                .limit(1)
            )
            return user_dictionary_entry_to_dict(row) if row is not None else None

    def find_entry_by_word_and_part_of_speech(self, word: str, part_of_speech: str) -> dict[str, Any] | None:
        normalized_word = _normalize_lookup_word(word)
        normalized_part_of_speech = normalize_dictionary_part_of_speech(part_of_speech)
        with self.session_manager.session() as session:
            row = session.scalar(
                select(UserDictionaryEntry)
                .options(selectinload(UserDictionaryEntry.level))
                .where(
                    func.lower(UserDictionaryEntry.normalized_word) == normalized_word,
                    UserDictionaryEntry.part_of_speech == normalized_part_of_speech,
                )
                .limit(1)
            )
            return user_dictionary_entry_to_dict(row) if row is not None else None

    def count_entries_created_by_user_since(self, user_uuid: str | UUID, *, since: datetime) -> int:
        with self.session_manager.session() as session:
            return int(
                session.scalar(
                    select(func.count())
                    .select_from(UserDictionaryEntry)
                    .where(
                        UserDictionaryEntry.created_by_user_uuid == _coerce_uuid(user_uuid),
                        UserDictionaryEntry.created >= since,
                    )
                )
                or 0
            )

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(UserDictionaryEntry, entry_id)
            return user_dictionary_entry_to_dict(row) if row is not None else None

    def get_admin_entry_detail(self, entry_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            return get_user_dictionary_admin_entry_detail(session, entry_id=entry_id)

    def get_entry_audio(self, entry_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(UserDictionaryEntry, entry_id)
            if row is None or not row.audio_path:
                return None
            return {"id": row.id, "audio_path": row.audio_path}

    def create_entry(
        self,
        *,
        word: str,
        part_of_speech: str,
        current_time: datetime,
        created_by_user_uuid: UUID | None = None,
        entry_type: str | None = None,
        level_id: int | None = None,
        transcription: str | None = None,
        translation_uk: str | None = None,
        translation_ru: str | None = None,
        translation_pl: str | None = None,
        examples_json: list[str] | None = None,
        audio_path: str | None = None,
        embedding: list[float] | None = None,
        embedding_model: str | None = None,
        is_embedding_ready: bool = False,
        status: str = "queued_for_details",
        source_provider_status_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_part_of_speech = normalize_dictionary_part_of_speech(part_of_speech)
        normalized_word = _normalize_lookup_word(word)
        resolved_entry_type = normalize_dictionary_entry_type(
            entry_type or dictionary_entry_type_from_part_of_speech(normalized_part_of_speech)
        )
        with self.session_manager.session() as session:
            row = UserDictionaryEntry(
                word=str(word).strip(),
                normalized_word=normalized_word,
                entry_key=_build_user_entry_key(normalized_word, normalized_part_of_speech),
                entry_type=resolved_entry_type,
                part_of_speech=normalized_part_of_speech,
                level_id=level_id,
                transcription=transcription,
                translation_uk=translation_uk,
                translation_ru=translation_ru,
                translation_pl=translation_pl,
                examples_json=examples_json or [],
                audio_path=audio_path,
                embedding=embedding,
                embedding_model=embedding_model,
                is_embedding_ready=is_embedding_ready,
                status=status,
                created_by_user_uuid=created_by_user_uuid,
                source_provider_status_json=source_provider_status_json or {},
                created=current_time,
                updated=current_time,
            )
            session.add(row)
            session.flush()
            return user_dictionary_entry_to_dict(row)

    def update_entry_status(
        self,
        entry_id: int,
        *,
        status: str,
        current_time: datetime,
        source_provider_status_json: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(UserDictionaryEntry, entry_id)
            if row is None:
                return None
            row.status = status
            if source_provider_status_json is not None:
                row.source_provider_status_json = source_provider_status_json
            row.updated = current_time
            return user_dictionary_entry_to_dict(row)

    def update_entry_details(
        self,
        entry_id: int,
        *,
        audio_storage_provider: AudioStorageProvider,
        word: str,
        entry_type: str | None,
        part_of_speech: str,
        level_id: int | None,
        transcription: str | None,
        translation_uk: str | None,
        translation_ru: str | None,
        translation_pl: str | None,
        examples_json: list[str],
        source_provider_status_json: dict[str, Any],
        status: str,
        audio_roots: list[Path | str] | None = None,
        queue_audio_on_spelling_change: bool = True,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(UserDictionaryEntry, entry_id)
            if row is None:
                return None
            normalized_part_of_speech = normalize_dictionary_part_of_speech(part_of_speech)
            normalized_word = _normalize_lookup_word(word)
            spelling_changed = row.normalized_word != normalized_word or row.word != str(word).strip()
            embedding_sensitive_changed = spelling_changed
            if translation_uk != row.translation_uk:
                embedding_sensitive_changed = True
            if translation_ru != row.translation_ru:
                embedding_sensitive_changed = True
            if translation_pl != row.translation_pl:
                embedding_sensitive_changed = True
            normalized_examples = normalize_examples_json(examples_json)
            if normalize_examples_json(row.examples_json) != normalized_examples:
                embedding_sensitive_changed = True
            if spelling_changed and row.audio_path:
                delete_audio_file_if_under_roots(
                    row.audio_path,
                    audio_roots or [],
                    storage_provider=audio_storage_provider,
                )
                row.audio_path = None
            row.word = str(word).strip()
            row.normalized_word = normalized_word
            row.entry_key = _build_user_entry_key(normalized_word, normalized_part_of_speech)
            row.entry_type = normalize_dictionary_entry_type(
                entry_type or dictionary_entry_type_from_part_of_speech(normalized_part_of_speech)
            )
            row.part_of_speech = normalized_part_of_speech
            row.level_id = level_id
            row.transcription = transcription
            row.translation_uk = translation_uk
            row.translation_ru = translation_ru
            row.translation_pl = translation_pl
            row.examples_json = normalized_examples
            if embedding_sensitive_changed:
                row.embedding = None
                row.embedding_model = None
                row.is_embedding_ready = False
            row.source_provider_status_json = source_provider_status_json
            row.status = USER_DICTIONARY_QUEUED_AUDIO if spelling_changed and queue_audio_on_spelling_change else status
            row.updated = current_time
            return user_dictionary_entry_to_dict(row)

    def update_entry_audio(
        self,
        entry_id: int,
        *,
        audio_path: str | None,
        source_provider_status_json: dict[str, Any],
        status: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(UserDictionaryEntry, entry_id)
            if row is None:
                return None
            row.audio_path = audio_path
            row.source_provider_status_json = source_provider_status_json
            row.status = status
            row.updated = current_time
            return user_dictionary_entry_to_dict(row)

    def update_entry_embedding(
        self,
        entry_id: int,
        *,
        embedding: list[float] | None,
        embedding_model: str | None,
        is_embedding_ready: bool,
        source_provider_status_json: dict[str, Any],
        status: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(UserDictionaryEntry, entry_id)
            if row is None:
                return None
            row.embedding = embedding
            row.embedding_model = embedding_model
            row.is_embedding_ready = is_embedding_ready
            row.source_provider_status_json = source_provider_status_json
            row.status = status
            row.updated = current_time
            return user_dictionary_entry_to_dict(row)

    def requeue_entry_details_build(
        self,
        entry_id: int,
        *,
        actor_label: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(UserDictionaryEntry, entry_id)
            if row is None:
                return None
            provider_status = dict(row.source_provider_status_json or {})
            provider_status["admin_requeue"] = {
                "phase": "details",
                "actor": actor_label,
                "queued_at": current_time.isoformat(),
            }
            row.source_provider_status_json = provider_status
            row.status = USER_DICTIONARY_QUEUED_DETAILS
            row.updated = current_time
            return user_dictionary_entry_to_dict(row)

    def requeue_entry_embedding_build(
        self,
        entry_id: int,
        *,
        actor_label: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(UserDictionaryEntry, entry_id)
            if row is None:
                return None
            provider_status = dict(row.source_provider_status_json or {})
            provider_status["admin_requeue"] = {
                "phase": "embedding",
                "actor": actor_label,
                "queued_at": current_time.isoformat(),
            }
            row.embedding = None
            row.embedding_model = None
            row.is_embedding_ready = False
            row.source_provider_status_json = provider_status
            row.status = USER_DICTIONARY_QUEUED_EMBEDDING
            row.updated = current_time
            return user_dictionary_entry_to_dict(row)

    def mark_entry_promoted(
        self,
        entry_id: int,
        *,
        dictionary_entry_id: int,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(UserDictionaryEntry, entry_id)
            if row is None:
                return None
            row.promoted_dictionary_entry_id = int(dictionary_entry_id)
            row.updated = current_time
            return user_dictionary_entry_to_dict(row)

    def promote_entry_to_core(
        self,
        entry_id: int,
        *,
        audio_path: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            return promote_user_dictionary_entry_to_core(
                session,
                entry_id,
                audio_path=audio_path,
                current_time=current_time,
            )

    def count_assignments_for_word(self, *, word_source: str, word_id: int) -> int:
        with self.session_manager.session() as session:
            return count_user_dictionary_assignments_for_word(session, word_source=word_source, word_id=word_id)

    def list_entries_by_status(self, status: str, *, limit: int) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(UserDictionaryEntry)
                .options(selectinload(UserDictionaryEntry.level))
                .where(UserDictionaryEntry.status == status)
                .order_by(UserDictionaryEntry.updated.asc(), UserDictionaryEntry.id.asc())
                .limit(limit)
            ).all()
            return [user_dictionary_entry_to_dict(row) for row in rows]

    def list_admin_entries(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        status: str | list[str] | None = None,
        part_of_speech: str | list[str] | None = None,
        level_id: int | list[int] | None = None,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            return list_user_dictionary_admin_entries(
                session,
                page=page,
                page_size=page_size,
                search=search,
                status=status,
                part_of_speech=part_of_speech,
                level_id=level_id,
                user_dictionary_statuses=USER_DICTIONARY_STATUSES,
            )

    def get_admin_filter_metadata(self) -> dict[str, Any]:
        with self.session_manager.session() as session:
            return get_user_dictionary_admin_filter_metadata(
                session,
                user_dictionary_statuses=USER_DICTIONARY_STATUSES,
            )

    def mark_assignments_available_for_entry(self, entry_id: int, *, current_time: datetime) -> int:
        with self.session_manager.session() as session:
            return mark_user_dictionary_assignments_available_for_entry(session, entry_id, current_time=current_time)

    def archive_assignments_for_entry(self, entry_id: int, *, current_time: datetime) -> int:
        with self.session_manager.session() as session:
            return archive_user_dictionary_assignments_for_entry(session, entry_id, current_time=current_time)

    def create_assignment(
        self,
        *,
        user_uuid: UUID,
        word_source: str,
        word_id: int,
        current_time: datetime,
        status: str = USER_WORD_ASSIGNMENT_AVAILABLE,
        import_job_id: int | None = None,
        import_item_id: int | None = None,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            return create_user_dictionary_assignment(
                session,
                user_uuid=user_uuid,
                word_source=word_source,
                word_id=word_id,
                current_time=current_time,
                status=status,
                import_job_id=import_job_id,
                import_item_id=import_item_id,
            )

    def list_assignments_for_user(
        self,
        user_uuid: UUID,
        *,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            return list_user_dictionary_assignments_for_user(session, user_uuid, status=status)

    def list_assigned_lookup_words_for_user(self, user_uuid: str | UUID) -> set[str]:
        resolved_uuid = _coerce_uuid(user_uuid)
        with self.session_manager.session() as session:
            core_rows = session.execute(
                select(DictionaryEntry.normalized_word, DictionaryEntry.word)
                .join(
                    UserWordAssignment,
                    (UserWordAssignment.word_source == USER_WORD_SOURCE_CORE)
                    & (UserWordAssignment.word_id == DictionaryEntry.id),
                )
                .where(UserWordAssignment.user_uuid == resolved_uuid)
            ).all()
            user_rows = session.execute(
                select(UserDictionaryEntry.normalized_word, UserDictionaryEntry.word)
                .join(
                    UserWordAssignment,
                    (UserWordAssignment.word_source == USER_WORD_SOURCE_USER)
                    & (UserWordAssignment.word_id == UserDictionaryEntry.id),
                )
                .where(UserWordAssignment.user_uuid == resolved_uuid)
            ).all()
            return {
                normalized
                for normalized in (
                    _normalize_lookup_word(normalized_word or word)
                    for normalized_word, word in [*core_rows, *user_rows]
                )
                if normalized
            }


def _normalize_lookup_word(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _coerce_uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _build_user_entry_key(normalized_word: str, part_of_speech: str) -> str:
    return f"user__{slugify(normalized_word)}__{slugify(part_of_speech)}"


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "entry"
