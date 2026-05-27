from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_, select

from app.models import BotMessageLog
from app.orm import SessionManager


def bot_message_log_to_dict(row: BotMessageLog) -> dict[str, Any]:
    return {
        "id": row.id,
        "telegram_user_id": row.telegram_user_id,
        "chat_id": row.chat_id,
        "message_id": row.message_id,
        "screen_id": row.screen_id,
        "status": row.status,
        "error_text": row.error_text,
        "delete_after": row.delete_after,
        "created": row.created,
        "updated": row.updated,
        "deleted": row.deleted,
    }


class BotMessageLogRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def create(
        self,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
        screen_id: str,
        delete_after: datetime,
        current_time: datetime,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            row = BotMessageLog(
                telegram_user_id=telegram_user_id,
                chat_id=chat_id,
                message_id=message_id,
                screen_id=screen_id,
                status="active",
                delete_after=delete_after,
                created=current_time,
                updated=current_time,
            )
            session.add(row)
            session.flush()
            return bot_message_log_to_dict(row)

    def get_latest_for_message(
        self,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.scalar(
                select(BotMessageLog)
                .where(
                    BotMessageLog.telegram_user_id == telegram_user_id,
                    BotMessageLog.chat_id == chat_id,
                    BotMessageLog.message_id == message_id,
                )
                .order_by(BotMessageLog.id.desc())
                .limit(1)
            )
            return bot_message_log_to_dict(row) if row is not None else None

    def get_latest_active_screen(self, telegram_user_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.scalar(
                select(BotMessageLog)
                .where(
                    BotMessageLog.telegram_user_id == telegram_user_id,
                    BotMessageLog.status == "active",
                    BotMessageLog.deleted.is_(None),
                )
                .order_by(BotMessageLog.created.desc(), BotMessageLog.id.desc())
                .limit(1)
            )
            return bot_message_log_to_dict(row) if row is not None else None

    def list_active(self, telegram_user_id: int, chat_id: int) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(BotMessageLog)
                .where(
                    BotMessageLog.telegram_user_id == telegram_user_id,
                    BotMessageLog.chat_id == chat_id,
                    BotMessageLog.deleted.is_(None),
                    BotMessageLog.status != "deleted",
                )
                .order_by(BotMessageLog.id.asc())
            ).all()
            return [bot_message_log_to_dict(row) for row in rows]

    def claim_due_cleanup(self, current_time: datetime, retry_before: datetime) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(BotMessageLog).where(
                    BotMessageLog.delete_after <= current_time,
                    BotMessageLog.deleted.is_(None),
                    or_(
                        BotMessageLog.status == "active",
                        and_(
                            BotMessageLog.status == "cleanup_failed",
                            BotMessageLog.updated <= retry_before,
                        ),
                        and_(
                            BotMessageLog.status == "cleanup_in_progress",
                            BotMessageLog.updated <= retry_before,
                        ),
                    ),
                )
                .order_by(BotMessageLog.delete_after.asc(), BotMessageLog.id.asc())
            ).all()
            payload: list[dict[str, Any]] = []
            for row in rows:
                row.status = "cleanup_in_progress"
                row.updated = current_time
                row.error_text = None
                payload.append(bot_message_log_to_dict(row))
            return payload

    def save_cleanup_result(
        self,
        message_log_id: int,
        *,
        is_deleted: bool,
        current_time: datetime,
        error_text: str | None = None,
    ) -> None:
        with self.session_manager.session() as session:
            row = session.get(BotMessageLog, message_log_id)
            if row is None:
                return
            if row.deleted is not None and not is_deleted:
                return
            row.updated = current_time
            if is_deleted:
                row.status = "deleted"
                row.deleted = current_time
                row.error_text = None
                return
            row.status = "cleanup_failed"
            row.error_text = error_text
