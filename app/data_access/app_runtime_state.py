from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models import AppRuntimeState
from app.orm import SessionManager


def app_runtime_state_to_dict(row: AppRuntimeState) -> dict[str, Any]:
    return {"key": row.key, "value_json": row.value_json or {}, "updated": row.updated}


class AppRuntimeStateRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def get(self, key: str) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(AppRuntimeState, key)
            return app_runtime_state_to_dict(row) if row is not None else None

    def set(self, key: str, value_json: dict[str, Any], current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(AppRuntimeState, key)
            if row is None:
                session.add(AppRuntimeState(key=key, value_json=value_json, updated=current_time))
                return
            row.value_json = value_json
            row.updated = current_time
