from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import distinct, func, or_, select

from app.models import (
    DictionaryEntry,
    DictionaryEntryPartOfSpeech,
    DictionaryPartOfSpeech,
    LanguageLevel,
    TeacherStudentLink,
    User,
    UserDictionaryEntry,
    UserEvent,
    WebLoginHistory,
)
from app.orm import SessionManager


class AdminDashboardRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def count_active_users(self, *, active_since: datetime | None = None) -> int:
        with self.session_manager.session() as session:
            if active_since is not None:
                event_user_uuids = set(
                    session.scalars(
                        select(distinct(User.uuid))
                        .join(UserEvent, UserEvent.telegram_user_id == User.telegram_user_id)
                        .where(
                            User.status == "active",
                            UserEvent.created >= active_since,
                        )
                    ).all()
                )
                event_user_uuids.update(
                    session.scalars(
                        select(distinct(WebLoginHistory.user_uuid))
                        .join(User, User.uuid == WebLoginHistory.user_uuid)
                        .where(
                            User.status == "active",
                            WebLoginHistory.created >= active_since,
                            WebLoginHistory.result == "success",
                            WebLoginHistory.user_uuid.is_not(None),
                        )
                    ).all()
                )
                return len(event_user_uuids)
            return int(session.scalar(select(func.count(User.uuid)).where(User.status == "active")) or 0)

    def summarize(self, *, active_since: datetime) -> dict[str, Any]:
        with self.session_manager.session() as session:
            role_counts = _rows_to_counts(
                session.execute(select(User.learning_role, func.count(User.uuid)).group_by(User.learning_role)).all()
            )
            status_counts = _rows_to_counts(
                session.execute(select(User.status, func.count(User.uuid)).group_by(User.status)).all()
            )
            active_free_user_uuids = set(
                session.scalars(
                    select(distinct(User.uuid))
                    .join(UserEvent, UserEvent.telegram_user_id == User.telegram_user_id)
                    .where(
                        User.status == "active",
                        UserEvent.created >= active_since,
                        or_(User.is_premium.is_(False), User.is_premium.is_(None)),
                    )
                ).all()
            )
            active_free_user_uuids.update(
                session.scalars(
                    select(distinct(WebLoginHistory.user_uuid))
                    .join(User, User.uuid == WebLoginHistory.user_uuid)
                    .where(
                        User.status == "active",
                        WebLoginHistory.created >= active_since,
                        WebLoginHistory.result == "success",
                        WebLoginHistory.user_uuid.is_not(None),
                        or_(User.is_premium.is_(False), User.is_premium.is_(None)),
                    )
                ).all()
            )

            active_teacher_links = int(
                session.scalar(
                    select(func.count(TeacherStudentLink.id)).where(TeacherStudentLink.status == "active")
                )
                or 0
            )
            students_with_teacher = set(
                session.scalars(
                    select(distinct(TeacherStudentLink.student_user_uuid)).where(TeacherStudentLink.status == "active")
                ).all()
            )
            active_student_uuids = set(
                session.scalars(
                    select(User.uuid).where(User.status == "active", User.learning_role == "student")
                ).all()
            )

            core_pos_counts = _rows_to_counts(
                session.execute(
                    select(DictionaryPartOfSpeech.code, func.count(DictionaryEntry.id))
                    .select_from(DictionaryEntryPartOfSpeech)
                    .join(DictionaryPartOfSpeech, DictionaryPartOfSpeech.id == DictionaryEntryPartOfSpeech.part_of_speech_id)
                    .join(DictionaryEntry, DictionaryEntry.id == DictionaryEntryPartOfSpeech.entry_id)
                    .where(DictionaryEntry.is_archived.is_(False))
                    .group_by(DictionaryPartOfSpeech.code)
                    .order_by(DictionaryPartOfSpeech.code.asc())
                ).all()
            )
            user_pos_counts = _rows_to_counts(
                session.execute(
                    select(UserDictionaryEntry.part_of_speech, func.count(UserDictionaryEntry.id))
                    .where(UserDictionaryEntry.status != "archived")
                    .group_by(UserDictionaryEntry.part_of_speech)
                    .order_by(UserDictionaryEntry.part_of_speech.asc())
                ).all()
            )
            user_word_status_counts = _rows_to_counts(
                session.execute(
                    select(UserDictionaryEntry.status, func.count(UserDictionaryEntry.id))
                    .group_by(UserDictionaryEntry.status)
                    .order_by(UserDictionaryEntry.status.asc())
                ).all()
            )
            level_counts = _rows_to_counts(
                session.execute(
                    select(LanguageLevel.title, func.count(User.uuid))
                    .select_from(User)
                    .join(LanguageLevel, LanguageLevel.id == User.language_level_id, isouter=True)
                    .where(User.status == "active")
                    .group_by(LanguageLevel.title)
                    .order_by(LanguageLevel.title.asc().nullslast())
                ).all(),
                none_key="unknown",
            )

            core_total = int(
                session.scalar(select(func.count(DictionaryEntry.id)).where(DictionaryEntry.is_archived.is_(False))) or 0
            )
            user_total = int(
                session.scalar(select(func.count(UserDictionaryEntry.id)).where(UserDictionaryEntry.status != "archived")) or 0
            )

        return {
            "users": {
                "total": sum(role_counts.values()),
                "by_learning_role": role_counts,
                "by_status": status_counts,
                "active_free_weekly": len(active_free_user_uuids),
            },
            "teacher_assignments": {
                "active_links": active_teacher_links,
                "unassigned_active_students": len(active_student_uuids - students_with_teacher),
            },
            "dictionary": {
                "core_total": core_total,
                "core_by_part_of_speech": core_pos_counts,
                "user_total": user_total,
                "user_by_part_of_speech": user_pos_counts,
                "user_by_status": user_word_status_counts,
            },
            "levels": level_counts,
            "subscriptions": {
                "implemented": False,
                "tiers": [],
            },
        }


def _rows_to_counts(rows: Iterable[tuple[Any, Any]], *, none_key: str = "unknown") -> dict[str, int]:
    return {str(key if key is not None else none_key): int(value or 0) for key, value in rows}
