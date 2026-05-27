from __future__ import annotations

from app.models import UserReminderSchedule


def reminder_schedule_to_dict(row: UserReminderSchedule) -> dict[str, object]:
    return {
        "id": row.id,
        "user_id": str(row.user_uuid),
        "user_uuid": str(row.user_uuid),
        "weekday": row.weekday,
        "hour": row.hour,
        "minute": row.minute,
        "title": row.title,
        "status": row.status,
        "created": row.created,
        "updated": row.updated,
    }
