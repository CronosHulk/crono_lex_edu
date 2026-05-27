from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from app.data_access.user_identity import get_user_by_telegram_id, get_user_uuid_by_telegram_id
from app.models import LanguageLevel, UserLevelRun
from app.orm import SessionManager


def level_run_to_dict(row: UserLevelRun) -> dict[str, Any]:
    return {
        "id": row.id,
        "user_id": str(row.user_uuid),
        "user_uuid": str(row.user_uuid),
        "level_id": row.level_id,
        "run_no": row.run_no,
        "status": row.status,
        "created": row.created,
        "updated": row.updated,
        "completed": row.completed,
    }


def language_level_to_dict(row: LanguageLevel) -> dict[str, Any]:
    return {"id": row.id, "title": row.title, "description": row.description}


def _current_datetime() -> datetime:
    return datetime.now(datetime.now().astimezone().tzinfo)


class LearningLevelRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def save_language_level(self, telegram_user_id: int, level_title: str) -> None:
        with self.session_manager.session() as session:
            level = session.scalar(select(LanguageLevel).where(LanguageLevel.title == level_title).limit(1))
            user = get_user_by_telegram_id(session, telegram_user_id)
            if level is None or user is None:
                raise ValueError(f"Language level not found for title={level_title}")
            user.language_level_id = level.id

    def list_language_levels(self) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            levels = session.scalars(select(LanguageLevel).order_by(LanguageLevel.id)).all()
            return [language_level_to_dict(level) for level in levels]

    def list_levels(self) -> list[dict[str, Any]]:
        return self.list_language_levels()

    def get_active(self, telegram_user_id: int, level_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return None
            row = session.scalar(
                select(UserLevelRun)
                .where(
                    UserLevelRun.user_uuid == user_uuid,
                    UserLevelRun.level_id == level_id,
                    UserLevelRun.status == "active",
                )
                .limit(1)
            )
            return level_run_to_dict(row) if row is not None else None

    def get_latest(self, telegram_user_id: int, level_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return None
            row = session.scalar(
                select(UserLevelRun)
                .where(
                    UserLevelRun.user_uuid == user_uuid,
                    UserLevelRun.level_id == level_id,
                )
                .order_by(UserLevelRun.run_no.desc(), UserLevelRun.id.desc())
                .limit(1)
            )
            return level_run_to_dict(row) if row is not None else None

    def create(self, telegram_user_id: int, level_id: int) -> dict[str, Any]:
        now = _current_datetime()
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                raise ValueError(f"Unknown user for telegram_user_id={telegram_user_id}")
            active_rows = session.scalars(
                select(UserLevelRun).where(
                    UserLevelRun.user_uuid == user_uuid,
                    UserLevelRun.level_id == level_id,
                    UserLevelRun.status == "active",
                )
            ).all()
            for row in active_rows:
                row.status = "abandoned"
                row.completed = now
                row.updated = now
            max_run_no = session.scalar(
                select(func.max(UserLevelRun.run_no)).where(
                    UserLevelRun.user_uuid == user_uuid,
                    UserLevelRun.level_id == level_id,
                )
            )
            row = UserLevelRun(
                user_uuid=user_uuid,
                level_id=level_id,
                run_no=int(max_run_no or 0) + 1,
                status="active",
                updated=now,
            )
            session.add(row)
            session.flush()
            return level_run_to_dict(row)

    def ensure_active(self, telegram_user_id: int, level_id: int) -> dict[str, Any]:
        existing = self.get_active(telegram_user_id, level_id)
        if existing is not None:
            return existing
        return self.create(telegram_user_id, level_id)

    def complete(self, level_run_id: int, current_time: datetime | None = None) -> None:
        now = current_time or _current_datetime()
        with self.session_manager.session() as session:
            row = session.get(UserLevelRun, level_run_id)
            if row is None or row.status == "completed":
                return
            row.status = "completed"
            row.completed = now
            row.updated = now
