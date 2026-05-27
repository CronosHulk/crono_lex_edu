from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select

from app.data_access.dictionary_publish import dictionary_entry_to_dict
from app.models import DictionaryEntry
from app.orm import SessionManager


class DictionaryAudioRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def list_without_audio(self, *, limit: int) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(DictionaryEntry)
                .where(or_(DictionaryEntry.audio_path.is_(None), DictionaryEntry.audio_path == ""))
                .order_by(DictionaryEntry.id.asc())
                .limit(limit)
            ).all()
            return [dictionary_entry_to_dict(row) for row in rows]

    def count_without_audio(self) -> int:
        with self.session_manager.session() as session:
            return int(
                session.scalar(
                    select(func.count())
                    .select_from(DictionaryEntry)
                    .where(or_(DictionaryEntry.audio_path.is_(None), DictionaryEntry.audio_path == ""))
                )
                or 0
            )

    def update_entry_audio(
        self,
        entry_id: int,
        *,
        audio_path: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(DictionaryEntry, entry_id)
            if row is None:
                return None
            row.audio_path = audio_path
            row.updated = current_time
            return dictionary_entry_to_dict(row)
