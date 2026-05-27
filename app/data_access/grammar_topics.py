from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.models import GrammarTopic
from app.orm import SessionManager


def grammar_topic_to_dict(row: GrammarTopic) -> dict[str, Any]:
    return {
        "id": row.id,
        "code": row.code,
        "title": row.title,
        "level": row.level,
        "min_level": row.min_level,
        "description": row.description,
        "is_active": row.is_active,
    }


class GrammarTopicRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def list_active(self) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(GrammarTopic)
                .where(GrammarTopic.is_active.is_(True))
                .order_by(GrammarTopic.level.asc(), GrammarTopic.title.asc(), GrammarTopic.id.asc())
            ).all()
            return [grammar_topic_to_dict(row) for row in rows]

    def get_active_by_code(self, code: str) -> dict[str, Any] | None:
        normalized_code = str(code or "").strip()
        if not normalized_code:
            return None
        with self.session_manager.session() as session:
            row = session.scalar(
                select(GrammarTopic)
                .where(GrammarTopic.code == normalized_code, GrammarTopic.is_active.is_(True))
                .limit(1)
            )
            return grammar_topic_to_dict(row) if row is not None else None
