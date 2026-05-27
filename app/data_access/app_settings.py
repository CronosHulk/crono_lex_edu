from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models import AppSetting
from app.orm import SessionManager


def app_setting_to_dict(row: AppSetting) -> dict[str, Any]:
    return {
        "key": row.key,
        "value_json": dict(row.value_json or {}),
        "created": row.created,
        "updated": row.updated,
    }


class AppSettingRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def get_value(self, key: str) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(AppSetting, key)
            if row is None:
                return None
            return dict(row.value_json or {})

    def upsert_value(self, key: str, value_json: dict[str, Any], current_time: datetime) -> dict[str, Any]:
        with self.session_manager.session() as session:
            row = session.get(AppSetting, key)
            if row is None:
                row = AppSetting(
                    key=key,
                    value_json=value_json,
                    created=current_time,
                    updated=current_time,
                )
                session.add(row)
            else:
                row.value_json = value_json
                row.updated = current_time
            session.flush()
            return app_setting_to_dict(row)
