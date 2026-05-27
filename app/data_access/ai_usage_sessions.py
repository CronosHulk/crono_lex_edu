from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, or_, select

from app.data_access.filtering import normalize_filter_values
from app.models import AIUsageSession
from app.orm import SessionManager


def ai_usage_session_to_dict(row: AIUsageSession) -> dict[str, Any]:
    return {
        "id": row.id,
        "task_key": row.task_key,
        "task_scope": row.task_scope,
        "provider_key": row.provider_key,
        "model": row.model,
        "actor_type": row.actor_type,
        "actor_user_id": str(row.actor_user_uuid) if row.actor_user_uuid else None,
        "actor_user_uuid": str(row.actor_user_uuid) if row.actor_user_uuid else None,
        "actor_group_title": row.actor_group_title,
        "source_type": row.source_type,
        "source_identifier": row.source_identifier,
        "import_job_id": row.import_job_id,
        "task_log_id": row.task_log_id,
        "batch_key": row.batch_key,
        "request_count": row.request_count,
        "input_tokens": row.input_tokens,
        "output_tokens": row.output_tokens,
        "total_tokens": row.total_tokens,
        "estimated_cost_usd": str(row.estimated_cost_usd or Decimal("0")),
        "pricing_source": row.pricing_source,
        "status": row.status,
        "summary": row.summary,
        "metadata_json": row.metadata_json or {},
        "started": row.started,
        "finished": row.finished,
        "created": row.created,
        "updated": row.updated,
    }


class AIUsageSessionRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def create(self, **kwargs: Any) -> dict[str, Any]:
        with self.session_manager.session() as session:
            self._normalize_actor_kwargs(session, kwargs)
            row = AIUsageSession(**kwargs)
            session.add(row)
            session.flush()
            return ai_usage_session_to_dict(row)

    def delete_all(self) -> dict[str, int]:
        with self.session_manager.session() as session:
            session_count = int(session.scalar(select(func.count(AIUsageSession.id))) or 0)
            session.execute(delete(AIUsageSession))
            return {"deleted_ai_usage_sessions": session_count}

    def accumulate(self, **kwargs: Any) -> dict[str, Any]:
        batch_key = kwargs.get("batch_key")
        with self.session_manager.session() as session:
            self._normalize_actor_kwargs(session, kwargs)
            row = None
            if batch_key:
                row = session.scalar(
                    select(AIUsageSession).where(
                        AIUsageSession.batch_key == batch_key,
                        AIUsageSession.task_key == kwargs["task_key"],
                        AIUsageSession.provider_key == kwargs["provider_key"],
                        AIUsageSession.model == kwargs["model"],
                    ).limit(1)
                )
            if row is None:
                row = AIUsageSession(**kwargs)
                session.add(row)
            else:
                row.request_count += int(kwargs.get("request_count") or 0)
                row.input_tokens += int(kwargs.get("input_tokens") or 0)
                row.output_tokens += int(kwargs.get("output_tokens") or 0)
                row.total_tokens += int(kwargs.get("total_tokens") or 0)
                row.estimated_cost_usd += Decimal(str(kwargs.get("estimated_cost_usd") or "0"))
                row.finished = kwargs.get("finished") or row.finished
                row.updated = kwargs.get("updated") or row.updated
                if kwargs.get("status") != "success":
                    row.status = kwargs.get("status") or row.status
            session.flush()
            return ai_usage_session_to_dict(row)

    def list_admin(
        self,
        *,
        page: int,
        page_size: int,
        created_from: datetime | None = None,
        task_scope: str | list[str] | None = None,
        task_key: str | list[str] | None = None,
        provider_key: str | list[str] | None = None,
        model: str | list[str] | None = None,
        actor_user_id: str | None = None,
        search: str = "",
    ) -> dict[str, Any]:
        offset = (max(page, 1) - 1) * page_size
        with self.session_manager.session() as session:
            filters = self._filters(
                created_from=created_from,
                task_scope=task_scope,
                task_key=task_key,
                provider_key=provider_key,
                model=model,
                actor_user_id=actor_user_id,
                search=search,
            )
            query = select(AIUsageSession).where(*filters)
            count_query = select(func.count(AIUsageSession.id)).where(*filters)
            total = int(session.scalar(count_query) or 0)
            rows = session.scalars(
                query.order_by(AIUsageSession.created.desc(), AIUsageSession.id.desc()).offset(offset).limit(page_size)
            ).all()
            return {
                "items": [ai_usage_session_to_dict(row) for row in rows],
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            }

    def summarize_admin(self, *, created_from: datetime | None = None) -> dict[str, Any]:
        with self.session_manager.session() as session:
            filters = []
            if created_from is not None:
                filters.append(AIUsageSession.created >= created_from)
            rows = session.execute(
                select(
                    AIUsageSession.task_scope,
                    AIUsageSession.task_key,
                    AIUsageSession.provider_key,
                    AIUsageSession.model,
                    func.count(AIUsageSession.id),
                    func.coalesce(func.sum(AIUsageSession.request_count), 0),
                    func.coalesce(func.sum(AIUsageSession.input_tokens), 0),
                    func.coalesce(func.sum(AIUsageSession.output_tokens), 0),
                    func.coalesce(func.sum(AIUsageSession.total_tokens), 0),
                    func.coalesce(func.sum(AIUsageSession.estimated_cost_usd), 0),
                ).where(*filters).group_by(
                    AIUsageSession.task_scope,
                    AIUsageSession.task_key,
                    AIUsageSession.provider_key,
                    AIUsageSession.model,
                )
            ).all()
            return {
                "items": [
                    {
                        "task_scope": row[0],
                        "task_key": row[1],
                        "provider_key": row[2],
                        "model": row[3],
                        "session_count": int(row[4] or 0),
                        "request_count": int(row[5] or 0),
                        "input_tokens": int(row[6] or 0),
                        "output_tokens": int(row[7] or 0),
                        "total_tokens": int(row[8] or 0),
                        "estimated_cost_usd": str(row[9] or Decimal("0")),
                    }
                    for row in rows
                ]
            }

    def summarize_totals(self, *, created_from: datetime | None = None) -> dict[str, Any]:
        with self.session_manager.session() as session:
            filters = []
            if created_from is not None:
                filters.append(AIUsageSession.created >= created_from)
            row = session.execute(
                select(
                    func.count(AIUsageSession.id),
                    func.coalesce(func.sum(AIUsageSession.request_count), 0),
                    func.coalesce(func.sum(AIUsageSession.total_tokens), 0),
                    func.coalesce(func.sum(AIUsageSession.estimated_cost_usd), 0),
                    func.count(func.distinct(AIUsageSession.actor_user_uuid)),
                ).where(*filters)
            ).first()
            return {
                "session_count": int(row[0] or 0),
                "request_count": int(row[1] or 0),
                "total_tokens": int(row[2] or 0),
                "estimated_cost_usd": str(row[3] or Decimal("0")),
                "ai_active_user_count": int(row[4] or 0),
            }

    def summarize_by_actor_user_ids(self, user_ids: list[str], *, created_from: datetime | None = None) -> dict[str, dict[str, Any]]:
        normalized_user_ids = [_coerce_uuid(user_id) for user_id in user_ids if user_id]
        if not normalized_user_ids:
            return {}
        with self.session_manager.session() as session:
            filters = [AIUsageSession.actor_user_uuid.in_(normalized_user_ids)]
            if created_from is not None:
                filters.append(AIUsageSession.created >= created_from)
            rows = session.execute(
                select(
                    AIUsageSession.actor_user_uuid,
                    func.count(AIUsageSession.id),
                    func.coalesce(func.sum(AIUsageSession.request_count), 0),
                    func.coalesce(func.sum(AIUsageSession.total_tokens), 0),
                    func.coalesce(func.sum(AIUsageSession.estimated_cost_usd), 0),
                ).where(*filters).group_by(AIUsageSession.actor_user_uuid)
            ).all()
            return {
                str(row[0]): {
                    "session_count": int(row[1] or 0),
                    "request_count": int(row[2] or 0),
                    "total_tokens": int(row[3] or 0),
                    "estimated_cost_usd": str(row[4] or Decimal("0")),
                }
                for row in rows
            }

    def _filters(self, **kwargs: Any) -> list[Any]:
        filters = []
        if kwargs.get("created_from") is not None:
            filters.append(AIUsageSession.created >= kwargs["created_from"])
        for field_name in ("task_scope", "task_key", "provider_key", "model"):
            values = normalize_filter_values(kwargs.get(field_name))
            if values:
                filters.append(getattr(AIUsageSession, field_name).in_(values))
        if kwargs.get("actor_user_id"):
            filters.append(AIUsageSession.actor_user_uuid == kwargs["actor_user_id"])
        normalized_search = str(kwargs.get("search") or "").strip().lower()
        if normalized_search:
            like_value = f"%{normalized_search}%"
            filters.append(
                or_(
                    func.lower(AIUsageSession.task_key).like(like_value),
                    func.lower(AIUsageSession.task_scope).like(like_value),
                    func.lower(AIUsageSession.provider_key).like(like_value),
                    func.lower(AIUsageSession.model).like(like_value),
                    func.lower(AIUsageSession.summary).like(like_value),
                )
            )
        return filters

    @staticmethod
    def _normalize_actor_kwargs(session, kwargs: dict[str, Any]) -> None:
        _ = session


def _coerce_uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))
