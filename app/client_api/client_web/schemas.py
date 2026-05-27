from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.billing.runtime_settings import BILLING_PERIOD_OPTIONS
from app.domain.user_dictionary.constants import USER_WORD_SOURCE_CORE, USER_WORD_SOURCE_USER
from app.helpers.locale import SUPPORTED_INTERFACE_LOCALES
from app.reference.learning_flow import READY_STAGES
from app.reference.reminder_schedules import (
    REMINDER_HOURS,
    REMINDER_MINUTES,
    REMINDER_STATUSES,
    REMINDER_WEEKDAYS,
)
from app.subscriptions.plan_limits import CUSTOMER_PLAN_KEYS


class ClientWebRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClientWebAuthStartRequest(ClientWebRequest):
    username: str = Field(min_length=1, max_length=64)


class ClientWebAuthPasswordRequest(ClientWebRequest):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=512)


class ClientWebAuthOtpRequest(ClientWebRequest):
    challenge_id: int = Field(gt=0)
    otp: str = Field(min_length=6, max_length=16)


class ClientWebAuthPasswordUpdateRequest(ClientWebRequest):
    current_password: str | None = Field(default=None, min_length=1, max_length=512)
    password: str = Field(min_length=8, max_length=256)
    confirm_password: str = Field(min_length=8, max_length=256)

    @field_validator("confirm_password")
    @classmethod
    def validate_confirmation(cls, value: str, info) -> str:
        if info.data.get("password") != value:
            raise ValueError("Password confirmation does not match")
        return value


class ClientWebMagicRequest(ClientWebRequest):
    token: str = Field(min_length=32, max_length=256)


class ClientWebLearningAnswerRequest(ClientWebRequest):
    session_word_id: int = Field(gt=0)
    option_index: int = Field(ge=0, le=3)


class ClientWebLearningCardActionRequest(ClientWebRequest):
    session_word_id: int = Field(gt=0)
    action: str = Field(min_length=1, max_length=16)

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        if value not in {"next", "known", "back", "quiz"}:
            raise ValueError("Unsupported card action")
        return value


class ClientWebLearningReadyActionRequest(ClientWebRequest):
    expected_stage: str = Field(min_length=1, max_length=32)
    decision: str = Field(min_length=1, max_length=8)

    @field_validator("expected_stage")
    @classmethod
    def validate_expected_stage(cls, value: str) -> str:
        if value not in READY_STAGES:
            raise ValueError("Unsupported ready stage")
        return value

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: str) -> str:
        if value not in {"yes", "no"}:
            raise ValueError("Unsupported ready decision")
        return value


class ClientWebLearningWordPriorityRequest(ClientWebRequest):
    word_source: str = Field(min_length=1, max_length=16)
    word_id: int = Field(gt=0)

    @field_validator("word_source")
    @classmethod
    def validate_word_source(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {USER_WORD_SOURCE_CORE, USER_WORD_SOURCE_USER}:
            raise ValueError("Unsupported word source")
        return normalized


class ClientWebDictionarySearchLearnRequest(ClientWebLearningWordPriorityRequest):
    pass


class ClientWebImportSubmitRequest(ClientWebRequest):
    source_url: str | None = Field(default=None, max_length=2048)
    text_content: str | None = Field(default=None, max_length=512_000)
    file_name: str | None = Field(default=None, max_length=160)


class ClientWebPlanSelectRequest(ClientWebRequest):
    plan_key: str = Field(min_length=1, max_length=32)

    @field_validator("plan_key")
    @classmethod
    def validate_plan_key(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in CUSTOMER_PLAN_KEYS:
            raise ValueError("Unsupported plan_key")
        return normalized


class ClientWebBillingCheckoutRequest(ClientWebRequest):
    plan_key: str = Field(min_length=1, max_length=32)
    period_months: int = Field(ge=1, le=12)
    offer_accepted: bool
    offer_text_hash: str = Field(min_length=64, max_length=64)
    source_path: str | None = Field(default=None, max_length=512)

    @field_validator("plan_key")
    @classmethod
    def validate_plan_key(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in CUSTOMER_PLAN_KEYS:
            raise ValueError("Unsupported plan_key")
        return normalized

    @field_validator("period_months")
    @classmethod
    def validate_period_months(cls, value: int) -> int:
        if value not in BILLING_PERIOD_OPTIONS:
            raise ValueError("Unsupported billing period")
        return value


class ClientWebReminderScheduleRow(ClientWebRequest):
    title: str | None = Field(default=None, max_length=80)
    weekday: int = Field(ge=0, le=6)
    hour: int = Field(ge=7, le=22)
    minute: int = Field(default=0, ge=0, le=59)
    status: str = Field(default="enabled", min_length=1, max_length=16)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("weekday")
    @classmethod
    def validate_weekday(cls, value: int) -> int:
        if value not in REMINDER_WEEKDAYS:
            raise ValueError("weekday must be from 0 to 6")
        return value

    @field_validator("hour")
    @classmethod
    def validate_hour(cls, value: int) -> int:
        if value not in REMINDER_HOURS:
            raise ValueError("hour must be from 7 to 22")
        return value

    @field_validator("minute")
    @classmethod
    def validate_minute(cls, value: int) -> int:
        if value not in REMINDER_MINUTES:
            raise ValueError("minute must be 0 or 30")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in REMINDER_STATUSES:
            raise ValueError("status must be enabled or disabled")
        return value


class ClientWebSettingsUpdateRequest(ClientWebRequest):
    interface_locale: str | None = Field(default=None, min_length=2, max_length=2)
    language_level: str | None = Field(default=None, min_length=1, max_length=16)
    words_per_session: int | None = Field(default=None, ge=1, le=100)
    daily_reminder_hour: int | None = Field(default=None, ge=0, le=23)
    reminder_weekdays: list[int] | None = Field(default=None, max_length=7)
    reminder_schedule: list[ClientWebReminderScheduleRow] | None = Field(default=None, max_length=28)

    @field_validator("interface_locale")
    @classmethod
    def validate_interface_locale(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_INTERFACE_LOCALES:
            raise ValueError("Unsupported interface locale")
        return normalized


    @field_validator("reminder_weekdays")
    @classmethod
    def validate_weekdays(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        normalized = sorted(set(value))
        if any(weekday < 0 or weekday > 6 for weekday in normalized):
            raise ValueError("reminder_weekdays must contain values from 0 to 6")
        return normalized


class ClientWebTeacherStudentAliasRequest(ClientWebRequest):
    teacher_alias: str | None = Field(default=None, max_length=80)


class ClientWebTeacherStudentLevelRequest(ClientWebRequest):
    language_level: str = Field(min_length=1, max_length=16)


class ClientWebTeacherStudentGroupRequest(ClientWebRequest):
    group_id: int | None = Field(default=None, ge=1)


class ClientWebTeacherStudentGroupSaveRequest(ClientWebRequest):
    title: str = Field(min_length=1, max_length=80)
