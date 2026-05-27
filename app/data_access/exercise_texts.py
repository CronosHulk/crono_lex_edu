from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Text, case, delete, func, or_, select, text
from sqlalchemy.orm import selectinload

from app.domain.exercise_texts.errors import (
    ExerciseTextVersionConflictError as _ExerciseTextVersionConflictError,
)
from app.models import ExerciseText, ExerciseTextTopic, TTSVoice
from app.orm import SessionManager


def _uuid_to_str(value: UUID | str | None) -> str | None:
    return str(value) if value is not None else None


def exercise_text_to_dict(row: ExerciseText, *, topic_ids: list[int] | None = None) -> dict[str, Any]:
    resolved_topic_ids = topic_ids
    if resolved_topic_ids is None:
        resolved_topic_ids = [link.grammar_topic_id for link in getattr(row, "topic_links", [])]
    return {
        "id": row.id,
        "uuid": str(row.uuid),
        "title": row.title,
        "status": row.status,
        "difficulty_band": row.difficulty_band,
        "text_types": list(row.text_types or []),
        "content_jsonb": dict(row.content_jsonb or {}),
        "version": row.version,
        "topic_ids": resolved_topic_ids,
        "created_by_user_uuid": _uuid_to_str(row.created_by_user_uuid),
        "updated_by_user_uuid": _uuid_to_str(row.updated_by_user_uuid),
        "published_at": row.published_at,
        "archived_at": row.archived_at,
        "created": row.created,
        "updated": row.updated,
    }


def tts_voice_to_dict(row: TTSVoice) -> dict[str, Any]:
    return {
        "id": row.id,
        "provider": row.provider,
        "code": row.code,
        "display_name": row.display_name,
        "language_code": row.language_code,
        "gender": row.gender,
        "is_active": row.is_active,
        "sort_order": row.sort_order,
    }


class ExerciseTextRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def create(
        self,
        *,
        title: str | None = None,
        status: str = "draft",
        difficulty_band: str | None = None,
        text_types: list[str] | None = None,
        content_jsonb: dict[str, Any] | None = None,
        topic_ids: list[int] | None = None,
        actor_user_uuid: UUID | str | None = None,
        current_time: datetime | None = None,
    ) -> dict[str, Any]:
        actor_uuid = UUID(str(actor_user_uuid)) if actor_user_uuid else None
        with self.session_manager.session() as session:
            row = ExerciseText(
                title=title,
                status=status,
                difficulty_band=difficulty_band,
                text_types=list(text_types or []),
                content_jsonb=dict(content_jsonb or {}),
                created_by_user_uuid=actor_uuid,
                updated_by_user_uuid=actor_uuid,
            )
            if current_time is not None:
                row.created = current_time
                row.updated = current_time
            session.add(row)
            session.flush()
            resolved_topic_ids = self._replace_topics(session, row.id, topic_ids or [])
            return exercise_text_to_dict(row, topic_ids=resolved_topic_ids)

    def get(self, exercise_text_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.scalar(
                select(ExerciseText)
                .options(selectinload(ExerciseText.topic_links))
                .where(ExerciseText.id == exercise_text_id)
                .limit(1)
            )
            return exercise_text_to_dict(row) if row is not None else None

    def list_page(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        archived: bool = False,
        search: str = "",
        status: list[str] | None = None,
        difficulty_band: list[str] | None = None,
        text_type: list[str] | None = None,
        topic_id: list[int] | None = None,
        has_quiz: bool | None = None,
        has_tts: bool | None = None,
        sort: str = "updated_desc",
    ) -> dict[str, Any]:
        normalized_page = max(int(page), 1)
        normalized_page_size = max(min(int(page_size), 100), 1)
        offset = (normalized_page - 1) * normalized_page_size
        with self.session_manager.session() as session:
            statement = select(ExerciseText).options(selectinload(ExerciseText.topic_links))
            count_statement = select(func.count()).select_from(ExerciseText)
            conditions = []
            if archived:
                conditions.append(ExerciseText.status == "archived")
            else:
                conditions.append(ExerciseText.status != "archived")
                conditions.append(ExerciseText.archived_at.is_(None))
            normalized_search = str(search or "").strip()
            if normalized_search:
                pattern = f"%{normalized_search}%"
                conditions.append(or_(ExerciseText.title.ilike(pattern), ExerciseText.uuid.cast(Text).ilike(pattern)))
            if status:
                conditions.append(ExerciseText.status.in_(status))
            if difficulty_band:
                conditions.append(ExerciseText.difficulty_band.in_(difficulty_band))
            if text_type:
                conditions.append(ExerciseText.text_types.overlap(text_type))
            if topic_id:
                conditions.append(ExerciseText.topic_links.any(ExerciseTextTopic.grammar_topic_id.in_(topic_id)))
            if has_quiz is not None:
                conditions.append(_jsonb_array_has_items(ExerciseText.content_jsonb["generated"]["questions"], has_quiz))
            if has_tts is not None:
                conditions.append(_jsonb_array_has_items(ExerciseText.content_jsonb["generated"]["audio"]["files"], has_tts))
            if conditions:
                statement = statement.where(*conditions)
                count_statement = count_statement.where(*conditions)
            total = int(session.scalar(count_statement) or 0)
            rows = session.scalars(statement.order_by(*_exercise_text_order_by(sort)).offset(offset).limit(normalized_page_size)).all()
            pages = (total + normalized_page_size - 1) // normalized_page_size if total else 0
            return {
                "items": [exercise_text_to_dict(row) for row in rows],
                "total": total,
                "page": normalized_page,
                "page_size": normalized_page_size,
                "pages": pages,
            }

    def update(
        self,
        exercise_text_id: int,
        *,
        expected_version: int,
        values: dict[str, Any],
        topic_ids: list[int] | None = None,
        actor_user_uuid: UUID | str | None = None,
        current_time: datetime | None = None,
    ) -> dict[str, Any] | None:
        actor_uuid = UUID(str(actor_user_uuid)) if actor_user_uuid else None
        with self.session_manager.session() as session:
            row = session.get(ExerciseText, exercise_text_id)
            if row is None:
                return None
            if row.version != expected_version:
                raise _ExerciseTextVersionConflictError("exercise_text_version_conflict")
            for field_name in ("title", "status", "difficulty_band", "text_types", "content_jsonb", "published_at", "archived_at"):
                if field_name in values:
                    value = values[field_name]
                    if field_name == "text_types":
                        value = list(value or [])
                    elif field_name == "content_jsonb":
                        value = dict(value or {})
                    setattr(row, field_name, value)
            row.version += 1
            if actor_uuid is not None:
                row.updated_by_user_uuid = actor_uuid
            if current_time is not None:
                row.updated = current_time
            resolved_topic_ids = self._replace_topics(session, row.id, topic_ids) if topic_ids is not None else None
            return exercise_text_to_dict(row, topic_ids=resolved_topic_ids)

    def _replace_topics(self, session, exercise_text_id: int, topic_ids: list[int]) -> list[int]:
        unique_topic_ids = list(dict.fromkeys(int(topic_id) for topic_id in topic_ids))
        session.execute(delete(ExerciseTextTopic).where(ExerciseTextTopic.exercise_text_id == exercise_text_id))
        for topic_id in unique_topic_ids:
            session.add(ExerciseTextTopic(exercise_text_id=exercise_text_id, grammar_topic_id=topic_id))
        return unique_topic_ids


class TTSVoiceRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def list_active(self, *, provider: str | None = None) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            statement = select(TTSVoice).where(TTSVoice.is_active.is_(True))
            if provider:
                statement = statement.where(TTSVoice.provider == provider.strip())
            rows = session.scalars(statement.order_by(TTSVoice.provider.asc(), TTSVoice.sort_order.asc(), TTSVoice.display_name.asc())).all()
            return [tts_voice_to_dict(row) for row in rows]


def _jsonb_array_has_items(path_expression, expected: bool):
    safe_array = case(
        (func.jsonb_typeof(path_expression) == "array", path_expression),
        else_=text("'[]'::jsonb"),
    )
    item_count = func.jsonb_array_length(safe_array)
    return item_count > 0 if expected else item_count == 0


def _exercise_text_order_by(sort: str):
    if sort == "created_desc":
        return (ExerciseText.created.desc(), ExerciseText.id.desc())
    if sort == "title_asc":
        return (ExerciseText.title.asc().nulls_last(), ExerciseText.id.desc())
    if sort == "id_desc":
        return (ExerciseText.id.desc(),)
    return (ExerciseText.updated.desc(), ExerciseText.id.desc())
