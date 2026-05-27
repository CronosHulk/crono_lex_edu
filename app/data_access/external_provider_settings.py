from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.models import ExternalProviderTaskSetting
from app.orm import SessionManager


def provider_task_setting_to_dict(row: ExternalProviderTaskSetting) -> dict[str, Any]:
    return {
        "task_key": row.task_key,
        "provider_key": row.provider_key,
        "is_enabled": row.is_enabled,
        "config_json": dict(row.config_json or {}),
        "last_status_json": dict(row.last_status_json or {}),
        "created": row.created,
        "updated": row.updated,
    }


class ExternalProviderSettingsRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def list_all(self) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.execute(select(ExternalProviderTaskSetting).order_by(ExternalProviderTaskSetting.task_key)).scalars().all()
            return [provider_task_setting_to_dict(row) for row in rows]

    def get_map(self) -> dict[str, dict[str, Any]]:
        return {row["task_key"]: row for row in self.list_all()}

    def upsert(
        self,
        *,
        task_key: str,
        provider_key: str,
        is_enabled: bool,
        config_json: dict[str, Any],
        current_time: datetime,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            row = session.get(ExternalProviderTaskSetting, task_key)
            if row is None:
                row = ExternalProviderTaskSetting(
                    task_key=task_key,
                    provider_key=provider_key,
                    is_enabled=is_enabled,
                    config_json=config_json,
                    last_status_json={},
                    created=current_time,
                    updated=current_time,
                )
                session.add(row)
            else:
                row.provider_key = provider_key
                row.is_enabled = is_enabled
                row.config_json = config_json
                row.updated = current_time
            session.flush()
            return provider_task_setting_to_dict(row)
