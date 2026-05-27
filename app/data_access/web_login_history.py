from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from app.data_access.filtering import normalize_filter_values
from app.data_access.user_identity import get_user_uuid_by_telegram_id
from app.models import WebLoginHistory
from app.orm import SessionManager


def web_login_history_to_dict(row: WebLoginHistory) -> dict[str, Any]:
    return {
        "id": row.id,
        "user_id": str(row.user_uuid) if row.user_uuid else None,
        "user_uuid": str(row.user_uuid) if row.user_uuid else None,
        "username_attempted": row.username_attempted,
        "interface_context": row.interface_context,
        "event_type": row.event_type,
        "result": row.result,
        "api_origin": row.api_origin,
        "api_path": row.api_path,
        "client_ip": row.client_ip,
        "user_agent": row.user_agent,
        "device_fingerprint_hash": row.device_fingerprint_hash,
        "details_json": row.details_json or {},
        "created": row.created,
    }


class WebLoginHistoryRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def create(
        self,
        *,
        telegram_user_id: int | None,
        username_attempted: str | None,
        interface_context: str,
        event_type: str,
        result: str,
        api_origin: str | None,
        api_path: str | None,
        client_ip: str | None,
        user_agent: str | None,
        device_fingerprint_hash: str | None,
        details_json: dict[str, Any] | None = None,
        current_time: datetime | None = None,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id) if telegram_user_id is not None else None
            row = WebLoginHistory(
                user_uuid=user_uuid,
                username_attempted=username_attempted,
                interface_context=interface_context,
                event_type=event_type,
                result=result,
                api_origin=api_origin,
                api_path=api_path,
                client_ip=client_ip,
                user_agent=user_agent,
                device_fingerprint_hash=device_fingerprint_hash,
                details_json=details_json or {},
                created=current_time or datetime.now().astimezone(),
            )
            session.add(row)
            session.flush()
            return web_login_history_to_dict(row)

    def list_admin(
        self,
        *,
        page: int,
        page_size: int,
        user_id: str | None = None,
        interface_context: str | list[str] | None = None,
        result: str | list[str] | None = None,
        api_origin: str | None = None,
    ) -> dict[str, Any]:
        offset = (max(page, 1) - 1) * page_size
        with self.session_manager.session() as session:
            filters = []
            if user_id:
                filters.append(WebLoginHistory.user_uuid == user_id)
            context_values = normalize_filter_values(interface_context)
            if context_values:
                filters.append(WebLoginHistory.interface_context.in_(context_values))
            result_values = normalize_filter_values(result)
            if result_values:
                filters.append(WebLoginHistory.result.in_(result_values))
            normalized_origin = (api_origin or "").strip().lower()
            if normalized_origin:
                filters.append(func.lower(WebLoginHistory.api_origin).like(f"%{normalized_origin}%"))
            total = int(session.scalar(select(func.count(WebLoginHistory.id)).where(*filters)) or 0)
            rows = session.scalars(
                select(WebLoginHistory)
                .where(*filters)
                .order_by(WebLoginHistory.created.desc(), WebLoginHistory.id.desc())
                .offset(offset)
                .limit(page_size)
            ).all()
            return {
                "items": [web_login_history_to_dict(row) for row in rows],
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            }

    def list_latest_for_user(self, user_id: str, *, limit: int = 10) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(WebLoginHistory)
                .where(WebLoginHistory.user_uuid == user_id)
                .order_by(WebLoginHistory.created.desc(), WebLoginHistory.id.desc())
                .limit(max(min(limit, 100), 1))
            ).all()
            return [web_login_history_to_dict(row) for row in rows]
