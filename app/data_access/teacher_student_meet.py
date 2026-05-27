from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.data_access.user_identity import get_user_by_uuid, get_user_uuid_by_telegram_id
from app.models import TeacherGoogleOAuthConnection, TeacherStudentLink, TeacherStudentMeetSession


def meet_session_to_dict(row: TeacherStudentMeetSession) -> dict[str, Any]:
    return {
        "id": row.id,
        "teacher_user_id": str(row.teacher_user_uuid),
        "teacher_user_uuid": str(row.teacher_user_uuid),
        "student_user_id": str(row.student_user_uuid),
        "student_user_uuid": str(row.student_user_uuid),
        "provider": row.provider,
        "calendar_event_id": row.calendar_event_id,
        "join_url": row.join_url,
        "status": row.status,
        "error_text": row.error_text,
        "created": row.created,
        "updated": row.updated,
    }


def google_connection_to_dict(row: TeacherGoogleOAuthConnection) -> dict[str, Any]:
    return {
        "id": row.id,
        "teacher_user_id": str(row.teacher_user_uuid),
        "teacher_user_uuid": str(row.teacher_user_uuid),
        "provider": row.provider,
        "refresh_token_ciphertext": row.refresh_token_ciphertext,
        "access_token_ciphertext": row.access_token_ciphertext,
        "access_token_expires_at": row.access_token_expires_at,
        "scope": row.scope,
        "status": row.status,
        "created": row.created,
        "updated": row.updated,
    }


class TeacherStudentMeetRepositoryMixin:
    def get_google_connection(self, *, teacher_telegram_user_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            teacher_user_uuid = get_user_uuid_by_telegram_id(session, teacher_telegram_user_id)
            if teacher_user_uuid is None:
                return None
            row = session.scalar(
                select(TeacherGoogleOAuthConnection)
                .where(
                    TeacherGoogleOAuthConnection.teacher_user_uuid == teacher_user_uuid,
                    TeacherGoogleOAuthConnection.provider == "google",
                    TeacherGoogleOAuthConnection.status == "active",
                )
                .limit(1)
            )
            return google_connection_to_dict(row) if row is not None else None

    def save_google_connection(
        self,
        *,
        teacher_telegram_user_id: int,
        refresh_token_ciphertext: str,
        access_token_ciphertext: str | None,
        access_token_expires_at: datetime | None,
        scope: str | None,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            teacher_user_uuid = get_user_uuid_by_telegram_id(session, teacher_telegram_user_id)
            if teacher_user_uuid is None:
                return None
            row = session.scalar(
                select(TeacherGoogleOAuthConnection)
                .where(
                    TeacherGoogleOAuthConnection.teacher_user_uuid == teacher_user_uuid,
                    TeacherGoogleOAuthConnection.provider == "google",
                )
                .limit(1)
            )
            if row is None:
                row = TeacherGoogleOAuthConnection(
                    teacher_user_uuid=teacher_user_uuid,
                    provider="google",
                    refresh_token_ciphertext=refresh_token_ciphertext,
                    access_token_ciphertext=access_token_ciphertext,
                    access_token_expires_at=access_token_expires_at,
                    scope=scope,
                    status="active",
                    created=current_time,
                    updated=current_time,
                )
                session.add(row)
            else:
                row.refresh_token_ciphertext = refresh_token_ciphertext or row.refresh_token_ciphertext
                row.access_token_ciphertext = access_token_ciphertext
                row.access_token_expires_at = access_token_expires_at
                row.scope = scope
                row.status = "active"
                row.updated = current_time
            session.flush()
            return google_connection_to_dict(row)

    def update_google_access_token(
        self,
        *,
        teacher_telegram_user_id: int,
        access_token_ciphertext: str,
        access_token_expires_at: datetime | None,
        current_time: datetime,
    ) -> None:
        with self.session_manager.session() as session:
            teacher_user_uuid = get_user_uuid_by_telegram_id(session, teacher_telegram_user_id)
            if teacher_user_uuid is None:
                return
            row = session.scalar(
                select(TeacherGoogleOAuthConnection)
                .where(
                    TeacherGoogleOAuthConnection.teacher_user_uuid == teacher_user_uuid,
                    TeacherGoogleOAuthConnection.provider == "google",
                    TeacherGoogleOAuthConnection.status == "active",
                )
                .limit(1)
            )
            if row is not None:
                row.access_token_ciphertext = access_token_ciphertext
                row.access_token_expires_at = access_token_expires_at
                row.updated = current_time

    def get_active_meet_session(
        self,
        *,
        teacher_telegram_user_id: int,
        student_user_id: str,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            teacher_user_uuid = get_user_uuid_by_telegram_id(session, teacher_telegram_user_id)
            if teacher_user_uuid is None:
                return None
            student_uuid = _student_uuid(student_user_id)
            if student_uuid is None:
                return None
            row = session.scalar(
                select(TeacherStudentMeetSession)
                .where(
                    TeacherStudentMeetSession.teacher_user_uuid == teacher_user_uuid,
                    TeacherStudentMeetSession.student_user_uuid == student_uuid,
                    TeacherStudentMeetSession.status == "active",
                )
                .order_by(TeacherStudentMeetSession.created.desc(), TeacherStudentMeetSession.id.desc())
                .limit(1)
            )
            return meet_session_to_dict(row) if row is not None else None

    def create_meet_session(
        self,
        *,
        teacher_telegram_user_id: int,
        student_user_id: str,
        calendar_event_id: str | None,
        join_url: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            teacher_user_uuid = get_user_uuid_by_telegram_id(session, teacher_telegram_user_id)
            if teacher_user_uuid is None:
                return None
            link = _active_link_for_teacher_student(session, teacher_user_uuid, student_user_id)
            student = get_user_by_uuid(session, student_user_id)
            if link is None or student is None:
                return None
            row = TeacherStudentMeetSession(
                teacher_user_uuid=teacher_user_uuid,
                student_user_uuid=student.uuid,
                provider="google_meet",
                calendar_event_id=calendar_event_id,
                join_url=join_url,
                status="active",
                created=current_time,
                updated=current_time,
            )
            session.add(row)
            session.flush()
            return meet_session_to_dict(row)


def _active_link_for_teacher_student(session, teacher_user_uuid: UUID, student_user_id: str) -> TeacherStudentLink | None:
    student_uuid = _student_uuid(student_user_id)
    if student_uuid is None:
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


def _student_uuid(student_user_id: str) -> UUID | None:
    try:
        return UUID(str(student_user_id))
    except (TypeError, ValueError):
        return None
