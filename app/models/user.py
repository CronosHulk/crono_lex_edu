from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.shared import AclGroup, LanguageLevel


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    is_bot: Mapped[bool | None] = mapped_column(Boolean)
    first_name: Mapped[str | None] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text)
    username: Mapped[str | None] = mapped_column(Text)
    language_code: Mapped[str | None] = mapped_column(Text)
    interface_locale: Mapped[str] = mapped_column(Text, nullable=False, server_default="uk")
    client_web_password_prompted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    admin_web_password_prompted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_video_learner: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_premium: Mapped[bool | None] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    learning_role: Mapped[str] = mapped_column(Text, nullable=False, server_default="student")
    acl_group_id: Mapped[int] = mapped_column(ForeignKey("acl_group.id"), nullable=False)
    language_level_id: Mapped[int | None] = mapped_column(ForeignKey("language_level.id"))
    chat_id: Mapped[int | None] = mapped_column(BigInteger)
    chat_type: Mapped[str | None] = mapped_column(Text)
    chat_username: Mapped[str | None] = mapped_column(Text)
    chat_title: Mapped[str | None] = mapped_column(Text)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    raw_telegram_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    acl_group: Mapped[AclGroup] = relationship()
    language_level: Mapped[LanguageLevel | None] = relationship()
    learning_settings: Mapped[UserLearningSettings | None] = relationship(back_populates="user", uselist=False)


class UserEvent(Base):
    __tablename__ = "user_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(ForeignKey("user.telegram_user_id"), nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    message_text: Mapped[str | None] = mapped_column(Text)
    callback_data: Mapped[str | None] = mapped_column(Text)
    raw_update_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UserLearningSettings(Base):
    __tablename__ = "user_learning_settings"

    user_uuid: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("user.uuid", ondelete="CASCADE"), primary_key=True)
    words_per_session: Mapped[int] = mapped_column(Integer, nullable=False, server_default="10")
    daily_reminder_hour: Mapped[int | None] = mapped_column(Integer)
    preferred_gender: Mapped[str | None] = mapped_column(Text)
    import_google_doc_id: Mapped[str | None] = mapped_column(Text)
    is_import_google_doc_auto_sync_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    import_google_doc_last_synced: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    import_google_doc_last_error: Mapped[str | None] = mapped_column(Text)
    import_google_doc_retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    import_google_doc_next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    import_google_doc_claimed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="learning_settings")


class UserSubscription(Base):
    __tablename__ = "user_subscription"
    __table_args__ = (
        CheckConstraint(
            "plan_key IN ('free', 'premium', 'premium_plus', 'permanent_premium', 'teacher_free', 'teacher_premium')",
            name="ck_user_subscription_plan_key",
        ),
        CheckConstraint("status IN ('active', 'expired', 'canceled')", name="ck_user_subscription_status"),
    )

    user_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        primary_key=True,
    )
    plan_key: Mapped[str] = mapped_column(Text, nullable=False)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trial_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    payment_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped[User] = relationship()


class UserImportGoogleDocProgress(Base):
    __tablename__ = "user_import_google_doc_progress"

    user_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        primary_key=True,
    )
    google_doc_id: Mapped[str] = mapped_column(Text, primary_key=True)
    last_processed_line: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_processed_line_hash: Mapped[str | None] = mapped_column(Text)
    last_processed_lookup_word: Mapped[str | None] = mapped_column(Text)
    last_synced: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UserReminderWeekday(Base):
    __tablename__ = "user_reminder_weekday"

    user_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        primary_key=True,
    )
    weekday: Mapped[int] = mapped_column(Integer, primary_key=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UserReminderSchedule(Base):
    __tablename__ = "user_reminder_schedule"
    __table_args__ = (
        CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_user_reminder_schedule_weekday"),
        CheckConstraint("hour >= 7 AND hour <= 22", name="ck_user_reminder_schedule_hour"),
        CheckConstraint("minute IN (0, 30)", name="ck_user_reminder_schedule_minute"),
        CheckConstraint("status IN ('enabled', 'disabled')", name="ck_user_reminder_schedule_status"),
        UniqueConstraint("user_uuid", "weekday", "hour", "minute", name="uq_user_reminder_schedule_user_weekday_time"),
        Index("idx_user_reminder_schedule_lookup", "user_uuid", "weekday", "status", "hour", "minute"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    hour: Mapped[int] = mapped_column(Integer, nullable=False)
    minute: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    title: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="enabled")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TeacherStudentLink(Base):
    __tablename__ = "teacher_student_link"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    teacher_user_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    student_user_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    group_id: Mapped[int | None] = mapped_column(ForeignKey("teacher_student_group.id", ondelete="SET NULL"))
    teacher_alias: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TeacherStudentGroup(Base):
    __tablename__ = "teacher_student_group"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="ck_teacher_student_group_status"),
        UniqueConstraint("teacher_user_uuid", "title", name="uq_teacher_student_group_teacher_title"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    teacher_user_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TeacherGoogleOAuthConnection(Base):
    __tablename__ = "teacher_google_oauth_connection"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'revoked')", name="ck_teacher_google_oauth_connection_status"),
        UniqueConstraint("teacher_user_uuid", "provider", name="uq_teacher_google_oauth_connection_teacher_provider"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    teacher_user_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False, server_default="google")
    refresh_token_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    access_token_ciphertext: Mapped[str | None] = mapped_column(Text)
    access_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scope: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TeacherStudentMeetSession(Base):
    __tablename__ = "teacher_student_meet_session"
    __table_args__ = (
        CheckConstraint("provider IN ('google_meet')", name="ck_teacher_student_meet_session_provider"),
        CheckConstraint("status IN ('active', 'failed', 'archived')", name="ck_teacher_student_meet_session_status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    teacher_user_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    student_user_uuid: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False, server_default="google_meet")
    calendar_event_id: Mapped[str | None] = mapped_column(Text)
    join_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    error_text: Mapped[str | None] = mapped_column(Text)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
