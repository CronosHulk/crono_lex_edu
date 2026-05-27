from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import func, select

from app.data_access.user_identity import get_user_uuid_by_telegram_id
from app.models import TrainingSchedule, User, UserReminderSchedule
from app.orm import SessionManager
from app.time_utils import build_schedule_datetime


def training_schedule_to_dict(
    schedule: TrainingSchedule,
    chat_id: int | None = None,
    telegram_user_id: int | None = None,
) -> dict[str, Any]:
    payload = {
        "id": schedule.id,
        "user_id": str(schedule.user_uuid),
        "user_uuid": str(schedule.user_uuid),
        "schedule_type": schedule.schedule_type,
        "scheduled_for": schedule.scheduled_for,
        "schedule_date": schedule.schedule_date,
        "period_code": schedule.period_code,
        "source_session_id": schedule.source_session_id,
        "status": schedule.status,
        "notified": schedule.notified,
        "created": schedule.created,
        "updated": schedule.updated,
    }
    if chat_id is not None:
        payload["chat_id"] = chat_id
    if telegram_user_id is not None:
        payload["telegram_user_id"] = telegram_user_id
    return payload


class TrainingScheduleRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def get_existing_for_date(
        self,
        telegram_user_id: int,
        target_date: date,
        *,
        schedule_types: tuple[str, ...] | None = None,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return None
            where_clauses = [
                TrainingSchedule.user_uuid == user_uuid,
                TrainingSchedule.schedule_date == target_date,
                TrainingSchedule.status.in_(("pending", "sent")),
            ]
            if schedule_types:
                where_clauses.append(TrainingSchedule.schedule_type.in_(schedule_types))
            row = session.scalar(
                select(TrainingSchedule)
                .where(*where_clauses)
                .order_by(TrainingSchedule.scheduled_for.asc())
                .limit(1)
            )
            return training_schedule_to_dict(row) if row is not None else None

    def get_next(self, telegram_user_id: int, current_time: datetime) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return None
            row = session.scalar(
                select(TrainingSchedule)
                .where(
                    TrainingSchedule.user_uuid == user_uuid,
                    TrainingSchedule.status.in_(("pending", "sent")),
                    TrainingSchedule.scheduled_for >= current_time,
                )
                .order_by(TrainingSchedule.scheduled_for.asc())
                .limit(1)
            )
            return training_schedule_to_dict(row) if row is not None else None

    def create_or_replace(
        self,
        telegram_user_id: int,
        schedule_type: str,
        scheduled_for: datetime,
        period_code: str | None = None,
        source_session_id: int | None = None,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                raise ValueError(f"Unknown user for telegram_user_id={telegram_user_id}")
            rows = session.scalars(
                select(TrainingSchedule).where(
                    TrainingSchedule.user_uuid == user_uuid,
                    TrainingSchedule.schedule_date == scheduled_for.date(),
                    TrainingSchedule.schedule_type == schedule_type,
                    TrainingSchedule.status.in_(("pending", "sent")),
                )
            ).all()
            for row in rows:
                row.status = "cancelled"
            item = TrainingSchedule(
                user_uuid=user_uuid,
                schedule_type=schedule_type,
                scheduled_for=scheduled_for,
                schedule_date=scheduled_for.date(),
                period_code=period_code,
                source_session_id=source_session_id,
                status="pending",
            )
            session.add(item)
            session.flush()
            return training_schedule_to_dict(item)

    def ensure_daily(self, current_time: datetime) -> None:
        current_weekday = current_time.weekday()
        with self.session_manager.session() as session:
            rows = session.execute(
                select(UserReminderSchedule.user_uuid, UserReminderSchedule.hour, UserReminderSchedule.minute)
                .join(User, User.uuid == UserReminderSchedule.user_uuid)
                .where(
                    UserReminderSchedule.weekday == current_weekday,
                    UserReminderSchedule.status == "enabled",
                    User.status == "active",
                )
                .order_by(
                    UserReminderSchedule.user_uuid.asc(),
                    UserReminderSchedule.hour.asc(),
                    UserReminderSchedule.minute.asc(),
                )
            ).all()
            for user_uuid, reminder_hour, reminder_minute in rows:
                scheduled_for = build_schedule_datetime(
                    current_time,
                    current_time.date(),
                    reminder_hour,
                    reminder_minute,
                )
                if scheduled_for < current_time:
                    continue
                exists = session.scalar(
                    select(func.count(TrainingSchedule.id))
                    .where(
                        TrainingSchedule.user_uuid == user_uuid,
                        TrainingSchedule.schedule_type == "daily",
                        TrainingSchedule.scheduled_for == scheduled_for,
                        TrainingSchedule.status.in_(("pending", "sent", "completed", "skipped")),
                    )
                )
                if exists:
                    continue
                session.add(
                    TrainingSchedule(
                        user_uuid=user_uuid,
                        schedule_type="daily",
                        scheduled_for=scheduled_for,
                        schedule_date=current_time.date(),
                        status="pending",
                    )
                )

    def get_due(self, current_time: datetime) -> list[dict[str, Any]]:
        self.ensure_daily(current_time)
        with self.session_manager.session() as session:
            rows = session.execute(
                select(TrainingSchedule, User.chat_id, User.telegram_user_id)
                .join(User, User.uuid == TrainingSchedule.user_uuid)
                .where(
                    TrainingSchedule.status == "pending",
                    TrainingSchedule.scheduled_for <= current_time,
                    User.chat_id.is_not(None),
                )
                .order_by(TrainingSchedule.scheduled_for.asc())
            ).all()
            payload: list[dict[str, Any]] = []
            for schedule, chat_id, telegram_user_id in rows:
                schedule.status = "sent"
                schedule.notified = current_time
                payload.append(training_schedule_to_dict(schedule, chat_id=chat_id, telegram_user_id=telegram_user_id))
            return payload

    def get(self, schedule_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(TrainingSchedule, schedule_id)
            if row is None:
                return None
            telegram_user_id = session.scalar(select(User.telegram_user_id).where(User.uuid == row.user_uuid).limit(1))
            return training_schedule_to_dict(row, telegram_user_id=telegram_user_id)

    def update_status(self, schedule_id: int, status: str) -> None:
        with self.session_manager.session() as session:
            row = session.get(TrainingSchedule, schedule_id)
            if row is not None:
                row.status = status

    def complete_due(
        self,
        telegram_user_id: int,
        current_time: datetime,
        *,
        exclude_schedule_id: int | None = None,
    ) -> None:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return
            where_clauses = [
                TrainingSchedule.user_uuid == user_uuid,
                TrainingSchedule.status.in_(("pending", "sent")),
                TrainingSchedule.scheduled_for <= current_time,
            ]
            if exclude_schedule_id is not None:
                where_clauses.append(TrainingSchedule.id != exclude_schedule_id)
            rows = session.scalars(select(TrainingSchedule).where(*where_clauses)).all()
            for row in rows:
                row.status = "completed"
