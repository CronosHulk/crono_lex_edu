from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.data_access.teacher_student_links import TeacherStudentLinkRepository
from app.domain.user_dictionary.constants import (
    USER_WORD_ASSIGNMENT_AVAILABLE,
    USER_WORD_ASSIGNMENT_HIDDEN,
)
from app.models import (
    AclGroup,
    Base,
    LanguageLevel,
    TeacherStudentGroup,
    TeacherStudentLink,
    TeacherStudentMeetSession,
    User,
    UserWordAssignment,
)

TEACHER_UUID = UUID("11111111-1111-4111-8111-111111111111")
STUDENT_UUID = UUID("22222222-2222-4222-8222-222222222222")
CURRENT_TIME = datetime(2026, 5, 25, 10, 0, 0)


class SQLiteSessionManager:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def build_repository() -> TeacherStudentLinkRepository:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[
            AclGroup.__table__,
            LanguageLevel.__table__,
            User.__table__,
            TeacherStudentGroup.__table__,
            TeacherStudentLink.__table__,
            TeacherStudentMeetSession.__table__,
            UserWordAssignment.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    seed_teacher_student_progress(session_factory)
    return TeacherStudentLinkRepository(SQLiteSessionManager(session_factory))


def seed_teacher_student_progress(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(AclGroup(id=1, title="student"))
        session.add_all(
            [
                make_user(
                    row_id=11,
                    user_uuid=TEACHER_UUID,
                    telegram_user_id=11,
                    first_name="Ada",
                    learning_role="teacher",
                ),
                make_user(
                    row_id=22,
                    user_uuid=STUDENT_UUID,
                    telegram_user_id=22,
                    first_name="Lin",
                    learning_role="student",
                ),
                TeacherStudentLink(
                    id=7,
                    teacher_user_uuid=TEACHER_UUID,
                    student_user_uuid=STUDENT_UUID,
                    status="active",
                    created=CURRENT_TIME,
                    updated=CURRENT_TIME,
                ),
                make_assignment(
                    assignment_id=1,
                    word_id=101,
                    status=USER_WORD_ASSIGNMENT_AVAILABLE,
                    learning_state="learned",
                ),
                make_assignment(
                    assignment_id=2,
                    word_id=102,
                    status=USER_WORD_ASSIGNMENT_AVAILABLE,
                    learning_state="learning",
                ),
                make_assignment(
                    assignment_id=3,
                    word_id=103,
                    status=USER_WORD_ASSIGNMENT_HIDDEN,
                    learning_state="learned",
                ),
            ]
        )
        session.commit()


def make_user(
    *,
    row_id: int,
    user_uuid: UUID,
    telegram_user_id: int,
    first_name: str,
    learning_role: str,
) -> User:
    return User(
        id=row_id,
        uuid=user_uuid,
        telegram_user_id=telegram_user_id,
        first_name=first_name,
        interface_locale="uk",
        status="active",
        learning_role=learning_role,
        acl_group_id=1,
        created=CURRENT_TIME,
        updated=CURRENT_TIME,
    )


def make_assignment(
    *,
    assignment_id: int,
    word_id: int,
    status: str,
    learning_state: str,
) -> UserWordAssignment:
    return UserWordAssignment(
        id=assignment_id,
        user_uuid=STUDENT_UUID,
        word_source="core",
        word_id=word_id,
        status=status,
        priority_rank=0,
        priority_state="none",
        is_known=False,
        learning_state=learning_state,
        control_success_streak=0,
        review_priority=0,
        review_stage=0,
        mistake_count=0,
        created=CURRENT_TIME,
        updated=CURRENT_TIME,
    )


def test_list_students_for_teacher_counts_available_for_rotation_assignments() -> None:
    repository = build_repository()

    payload = repository.list_students_for_teacher(
        teacher_telegram_user_id=11,
        page=1,
        page_size=10,
    )

    assert payload["items"][0]["dictionary_stats"] == {
        "learned_count": 1,
        "total_count": 2,
    }
