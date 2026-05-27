from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select

from app.data_access.teacher_student_meet import (
    TeacherStudentMeetRepositoryMixin,
    meet_session_to_dict,
)
from app.data_access.user_identity import get_user_by_uuid, get_user_uuid_by_telegram_id
from app.domain.user_dictionary.constants import USER_WORD_ASSIGNMENT_AVAILABLE
from app.models import (
    LanguageLevel,
    TeacherStudentGroup,
    TeacherStudentLink,
    TeacherStudentMeetSession,
    User,
    UserWordAssignment,
)
from app.orm import SessionManager


def teacher_group_to_dict(row: TeacherStudentGroup) -> dict[str, Any]:
    return {
        "id": row.id,
        "teacher_user_id": str(row.teacher_user_uuid),
        "teacher_user_uuid": str(row.teacher_user_uuid),
        "title": row.title,
        "status": row.status,
        "created": row.created,
        "updated": row.updated,
    }


class TeacherStudentLinkRepository(TeacherStudentMeetRepositoryMixin):
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def has_active_teacher(self, student_telegram_user_id: int) -> bool:
        with self.session_manager.session() as session:
            student_user_uuid = get_user_uuid_by_telegram_id(session, student_telegram_user_id)
            if student_user_uuid is None:
                return False
            row_id = session.scalar(
                select(TeacherStudentLink.id)
                .where(
                    TeacherStudentLink.student_user_uuid == student_user_uuid,
                    TeacherStudentLink.status == "active",
                )
                .limit(1)
            )
            return row_id is not None

    def list_students_for_teacher(
        self,
        *,
        teacher_telegram_user_id: int,
        page: int,
        page_size: int,
        name: str = "",
        login: str = "",
        level: str = "",
        group_id: int | None = None,
    ) -> dict[str, Any]:
        offset = (max(page, 1) - 1) * page_size
        with self.session_manager.session() as session:
            teacher_user_uuid = get_user_uuid_by_telegram_id(session, teacher_telegram_user_id)
            if teacher_user_uuid is None:
                return {"items": [], "page": page, "page_size": page_size, "total": 0, "pages": 0}

            assignment_summary = (
                select(
                    UserWordAssignment.user_uuid.label("user_uuid"),
                    func.count(UserWordAssignment.id)
                    .filter(UserWordAssignment.learning_state == "learned")
                    .label("learned_count"),
                    func.count(UserWordAssignment.id).label("total_count"),
                )
                .where(UserWordAssignment.status == USER_WORD_ASSIGNMENT_AVAILABLE)
                .group_by(UserWordAssignment.user_uuid)
                .subquery()
            )
            active_meet = (
                select(
                    TeacherStudentMeetSession.student_user_uuid.label("student_user_uuid"),
                    func.max(TeacherStudentMeetSession.id).label("meet_session_id"),
                )
                .where(
                    TeacherStudentMeetSession.teacher_user_uuid == teacher_user_uuid,
                    TeacherStudentMeetSession.status == "active",
                )
                .group_by(TeacherStudentMeetSession.student_user_uuid)
                .subquery()
            )
            filters = [
                TeacherStudentLink.teacher_user_uuid == teacher_user_uuid,
                TeacherStudentLink.status == "active",
                User.status == "active",
                User.learning_role == "student",
            ]
            normalized_name = name.strip().lower()
            if normalized_name:
                like_value = f"%{normalized_name}%"
                filters.append(
                    or_(
                        func.lower(User.first_name).like(like_value),
                        func.lower(User.last_name).like(like_value),
                        func.lower(TeacherStudentLink.teacher_alias).like(like_value),
                    )
                )
            normalized_login = login.strip().lower().lstrip("@")
            if normalized_login:
                filters.append(func.lower(User.username).like(f"%{normalized_login}%"))
            if level:
                filters.append(LanguageLevel.title == level)
            if group_id is not None:
                filters.append(TeacherStudentLink.group_id == group_id)

            base_query = (
                select(
                    TeacherStudentLink,
                    User,
                    LanguageLevel,
                    TeacherStudentGroup,
                    assignment_summary.c.learned_count,
                    assignment_summary.c.total_count,
                    TeacherStudentMeetSession,
                )
                .join(User, User.uuid == TeacherStudentLink.student_user_uuid)
                .outerjoin(LanguageLevel, LanguageLevel.id == User.language_level_id)
                .outerjoin(TeacherStudentGroup, TeacherStudentGroup.id == TeacherStudentLink.group_id)
                .outerjoin(assignment_summary, assignment_summary.c.user_uuid == User.uuid)
                .outerjoin(active_meet, active_meet.c.student_user_uuid == User.uuid)
                .outerjoin(TeacherStudentMeetSession, TeacherStudentMeetSession.id == active_meet.c.meet_session_id)
                .where(*filters)
            )
            total = int(session.scalar(select(func.count()).select_from(base_query.subquery())) or 0)
            rows = session.execute(
                base_query.order_by(User.first_name.asc().nullslast(), User.telegram_user_id.asc())
                .offset(offset)
                .limit(page_size)
            ).all()
            return {
                "items": [
                    _teacher_student_row_to_dict(
                        link,
                        student,
                        level_row,
                        group,
                        learned_count=int(learned_count or 0),
                        total_count=int(total_count or 0),
                        active_meet_session=meet_session,
                    )
                    for link, student, level_row, group, learned_count, total_count, meet_session in rows
                ],
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size if total else 0,
            }

    def list_groups_for_teacher(self, *, teacher_telegram_user_id: int) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            teacher_user_uuid = get_user_uuid_by_telegram_id(session, teacher_telegram_user_id)
            if teacher_user_uuid is None:
                return []
            rows = session.scalars(
                select(TeacherStudentGroup)
                .where(
                    TeacherStudentGroup.teacher_user_uuid == teacher_user_uuid,
                    TeacherStudentGroup.status == "active",
                )
                .order_by(TeacherStudentGroup.title.asc())
            ).all()
            return [teacher_group_to_dict(row) for row in rows]

    def create_group_for_teacher(
        self,
        *,
        teacher_telegram_user_id: int,
        title: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            teacher_user_uuid = get_user_uuid_by_telegram_id(session, teacher_telegram_user_id)
            if teacher_user_uuid is None:
                return None
            existing = session.scalar(
                select(TeacherStudentGroup)
                .where(
                    TeacherStudentGroup.teacher_user_uuid == teacher_user_uuid,
                    TeacherStudentGroup.title == title,
                )
                .limit(1)
            )
            if existing is not None:
                existing.status = "active"
                existing.updated = current_time
                session.flush()
                return teacher_group_to_dict(existing)
            row = TeacherStudentGroup(
                teacher_user_uuid=teacher_user_uuid,
                title=title,
                status="active",
                created=current_time,
                updated=current_time,
            )
            session.add(row)
            session.flush()
            return teacher_group_to_dict(row)

    def update_group_for_teacher(
        self,
        *,
        teacher_telegram_user_id: int,
        group_id: int,
        title: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            teacher_user_uuid = get_user_uuid_by_telegram_id(session, teacher_telegram_user_id)
            if teacher_user_uuid is None:
                return None
            row = session.scalar(
                select(TeacherStudentGroup)
                .where(
                    TeacherStudentGroup.id == group_id,
                    TeacherStudentGroup.teacher_user_uuid == teacher_user_uuid,
                    TeacherStudentGroup.status == "active",
                )
                .limit(1)
            )
            if row is None:
                return None
            duplicate = session.scalar(
                select(TeacherStudentGroup.id)
                .where(
                    TeacherStudentGroup.teacher_user_uuid == teacher_user_uuid,
                    TeacherStudentGroup.title == title,
                    TeacherStudentGroup.id != group_id,
                )
                .limit(1)
            )
            if duplicate is not None:
                return {"error": "group_title_exists"}
            row.title = title
            row.updated = current_time
            session.flush()
            return teacher_group_to_dict(row)

    def archive_group_for_teacher(
        self,
        *,
        teacher_telegram_user_id: int,
        group_id: int,
        current_time: datetime,
    ) -> bool:
        with self.session_manager.session() as session:
            teacher_user_uuid = get_user_uuid_by_telegram_id(session, teacher_telegram_user_id)
            if teacher_user_uuid is None:
                return False
            row = session.scalar(
                select(TeacherStudentGroup)
                .where(
                    TeacherStudentGroup.id == group_id,
                    TeacherStudentGroup.teacher_user_uuid == teacher_user_uuid,
                    TeacherStudentGroup.status == "active",
                )
                .limit(1)
            )
            if row is None:
                return False
            row.status = "archived"
            row.updated = current_time
            links = session.scalars(
                select(TeacherStudentLink).where(
                    TeacherStudentLink.teacher_user_uuid == teacher_user_uuid,
                    TeacherStudentLink.group_id == group_id,
                    TeacherStudentLink.status == "active",
                )
            ).all()
            for link in links:
                link.group_id = None
                link.updated = current_time
            return True

    def update_student_alias(
        self,
        *,
        teacher_telegram_user_id: int,
        student_user_id: str,
        teacher_alias: str | None,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            teacher_user_uuid = get_user_uuid_by_telegram_id(session, teacher_telegram_user_id)
            if teacher_user_uuid is None:
                return None
            link = _active_link_for_teacher_student(session, teacher_user_uuid, student_user_id)
            if link is None:
                return None
            link.teacher_alias = teacher_alias
            link.updated = current_time
            session.flush()
            return {"student_user_id": student_user_id, "teacher_alias": link.teacher_alias}

    def update_student_group(
        self,
        *,
        teacher_telegram_user_id: int,
        student_user_id: str,
        group_id: int | None,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            teacher_user_uuid = get_user_uuid_by_telegram_id(session, teacher_telegram_user_id)
            if teacher_user_uuid is None:
                return None
            if group_id is not None:
                group = session.scalar(
                    select(TeacherStudentGroup)
                    .where(
                        TeacherStudentGroup.id == group_id,
                        TeacherStudentGroup.teacher_user_uuid == teacher_user_uuid,
                        TeacherStudentGroup.status == "active",
                    )
                    .limit(1)
                )
                if group is None:
                    return None
            link = _active_link_for_teacher_student(session, teacher_user_uuid, student_user_id)
            if link is None:
                return None
            link.group_id = group_id
            link.updated = current_time
            session.flush()
            return {"student_user_id": student_user_id, "group_id": group_id}

    def update_student_level(
        self,
        *,
        teacher_telegram_user_id: int,
        student_user_id: str,
        level_title: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            teacher_user_uuid = get_user_uuid_by_telegram_id(session, teacher_telegram_user_id)
            if teacher_user_uuid is None:
                return None
            link = _active_link_for_teacher_student(session, teacher_user_uuid, student_user_id)
            level = session.scalar(select(LanguageLevel).where(LanguageLevel.title == level_title).limit(1))
            if link is None or level is None:
                return None
            student = get_user_by_uuid(session, student_user_id)
            if student is None:
                return None
            student.language_level_id = level.id
            student.updated = current_time
            session.flush()
            return {"student_user_id": student_user_id, "language_level_id": level.id, "language_level_title": level.title}

    def get_student_for_teacher(self, *, teacher_telegram_user_id: int, student_user_id: str) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            teacher_user_uuid = get_user_uuid_by_telegram_id(session, teacher_telegram_user_id)
            if teacher_user_uuid is None:
                return None
            link = _active_link_for_teacher_student(session, teacher_user_uuid, student_user_id)
            student = get_user_by_uuid(session, student_user_id)
            if link is None or student is None:
                return None
            return {
                "teacher_user_id": str(teacher_user_uuid),
                "teacher_user_uuid": str(teacher_user_uuid),
                "student_user_id": str(student.uuid),
                "student_user_uuid": str(student.uuid),
                "telegram_user_id": student.telegram_user_id,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "username": student.username,
                "chat_id": student.chat_id,
                "teacher_alias": link.teacher_alias,
            }

    def assign_student_to_teacher(
        self,
        *,
        teacher_user_id: str,
        student_user_id: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            teacher = get_user_by_uuid(session, teacher_user_id)
            student = get_user_by_uuid(session, student_user_id)
            if teacher is None or student is None:
                return None

            active_links = session.scalars(
                select(TeacherStudentLink).where(
                    TeacherStudentLink.student_user_uuid == student.uuid,
                    TeacherStudentLink.status == "active",
                )
            ).all()
            target_link = None
            for link in active_links:
                if link.teacher_user_uuid == teacher.uuid:
                    target_link = link
                    continue
                link.status = "archived"
                link.updated = current_time

            if target_link is None:
                target_link = TeacherStudentLink(
                    teacher_user_uuid=teacher.uuid,
                    student_user_uuid=student.uuid,
                    status="active",
                    created=current_time,
                    updated=current_time,
                )
                session.add(target_link)
            else:
                target_link.status = "active"
                target_link.updated = current_time
            session.flush()
            return {
                "id": target_link.id,
                "status": target_link.status,
                "teacher_user_id": str(target_link.teacher_user_uuid),
                "teacher_user_uuid": str(target_link.teacher_user_uuid),
                "student_user_id": str(target_link.student_user_uuid),
                "student_user_uuid": str(target_link.student_user_uuid),
                "created": target_link.created,
                "updated": target_link.updated,
            }

    def unassign_student(self, *, student_user_id: str, current_time: datetime) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            student = get_user_by_uuid(session, student_user_id)
            if student is None:
                return None
            link = session.scalar(
                select(TeacherStudentLink)
                .where(
                    TeacherStudentLink.student_user_uuid == student.uuid,
                    TeacherStudentLink.status == "active",
                )
                .limit(1)
            )
            if link is None:
                return None
            link.status = "archived"
            link.updated = current_time
            session.flush()
            return {
                "id": link.id,
                "status": link.status,
                "teacher_user_id": str(link.teacher_user_uuid),
                "teacher_user_uuid": str(link.teacher_user_uuid),
                "student_user_id": str(link.student_user_uuid),
                "student_user_uuid": str(link.student_user_uuid),
                "created": link.created,
                "updated": link.updated,
            }


def _teacher_student_row_to_dict(
    link: TeacherStudentLink,
    student: User,
    level: LanguageLevel | None,
    group: TeacherStudentGroup | None,
    *,
    learned_count: int,
    total_count: int,
    active_meet_session: TeacherStudentMeetSession | None,
) -> dict[str, Any]:
    return {
        "link_id": link.id,
        "student_user_id": str(student.uuid),
        "student_user_uuid": str(student.uuid),
        "telegram_user_id": student.telegram_user_id,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "username": student.username,
        "teacher_alias": link.teacher_alias,
        "language_level_id": level.id if level is not None else None,
        "language_level_title": level.title if level is not None else None,
        "group": teacher_group_to_dict(group) if group is not None else None,
        "dictionary_stats": {
            "learned_count": learned_count,
            "total_count": total_count,
        },
        "active_meet_session": meet_session_to_dict(active_meet_session) if active_meet_session is not None else None,
    }


def _active_link_for_teacher_student(session, teacher_user_uuid: UUID, student_user_id: str) -> TeacherStudentLink | None:
    try:
        student_uuid = UUID(str(student_user_id))
    except (TypeError, ValueError):
        return None
    return session.scalar(
        select(TeacherStudentLink)
        .where(
            TeacherStudentLink.teacher_user_uuid == teacher_user_uuid,
            TeacherStudentLink.student_user_uuid == student_uuid,
            TeacherStudentLink.status == "active",
        )
        .limit(1)
    )
