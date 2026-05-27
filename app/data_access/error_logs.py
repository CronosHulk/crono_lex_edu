from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import func, select

from app.data_access.filtering import normalize_filter_values
from app.models import ErrorLog
from app.orm import SessionManager


def error_log_to_dict(row: ErrorLog) -> dict[str, Any]:
    return {
        "id": row.id,
        "level": row.level,
        "text": row.text,
        "context_json": row.context_json or {},
        "created": row.created,
    }


class ErrorLogRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def create(
        self,
        level: str,
        text: str | Iterable[str],
        *,
        context_json: dict[str, Any] | None = None,
    ) -> None:
        normalized_level = level.lower()
        if normalized_level not in {"warn", "debug", "fatal"}:
            raise ValueError(f"Unsupported error level: {level}")
        error_text = text if isinstance(text, str) else "\n".join(text)
        with self.session_manager.session() as session:
            session.add(ErrorLog(level=normalized_level, text=error_text, context_json=context_json or {}))

    def list_admin(
        self,
        *,
        page: int,
        page_size: int,
        level: str | list[str] | None = None,
        search: str = "",
    ) -> dict[str, Any]:
        offset = (max(page, 1) - 1) * page_size
        with self.session_manager.session() as session:
            filters = []
            level_values = normalize_filter_values(level)
            if level_values:
                filters.append(ErrorLog.level.in_(level_values))
            normalized_search = search.strip().lower()
            if normalized_search:
                filters.append(func.lower(ErrorLog.text).like(f"%{normalized_search}%"))

            query = select(ErrorLog).where(*filters)
            count_query = select(func.count(ErrorLog.id)).where(*filters)
            total = int(session.scalar(count_query) or 0)
            rows = session.scalars(
                query.order_by(ErrorLog.created.desc(), ErrorLog.id.desc()).offset(offset).limit(page_size)
            ).all()
            return {
                "items": [error_log_to_dict(row) for row in rows],
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            }

    def get_filter_metadata(self) -> dict[str, Any]:
        with self.session_manager.session() as session:
            levels = session.scalars(select(ErrorLog.level).distinct().order_by(ErrorLog.level.asc())).all()
            return {
                "entity": "error_log",
                "page_sizes": [50, 100],
                "filters": [
                    {"name": "search", "type": "text", "label": "Пошук"},
                    {
                        "name": "level",
                        "type": "multi_select",
                        "label": "Level",
                        "options": [{"value": value, "label": value} for value in levels if value],
                    },
                ],
            }
