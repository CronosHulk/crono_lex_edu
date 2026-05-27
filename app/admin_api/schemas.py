from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.admin_api.schema_validators import model_allowed_value, model_positive_id_list
from app.application.admin.user_dictionary.bulk import USER_DICTIONARY_BULK_ACTIONS
from app.billing.runtime_settings import MONOBANK_MODES
from app.domain.billing.constants import BILLING_PAYMENT_PROVIDERS
from app.reference.admin_actions import ADMIN_DESTRUCTIVE_ACTION_KEYS
from app.reference.dictionary_entries import DICTIONARY_ENTRY_TYPES
from app.subscriptions.plans import list_subscription_plans


class AdminApiRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AdminAuthStartRequest(AdminApiRequest):
    username: str = Field(min_length=1, max_length=64)
    password: str | None = Field(default=None, max_length=512)


class AdminAuthVerifyRequest(AdminApiRequest):
    challenge_id: int = Field(gt=0)
    otp: str = Field(min_length=6, max_length=16)


class AdminAuthMagicRequest(AdminApiRequest):
    token: str = Field(min_length=32, max_length=256)


class AdminActionOtpStartRequest(AdminApiRequest):
    action_key: str = Field(min_length=1, max_length=64)

    @field_validator("action_key")
    @classmethod
    def validate_action_key(cls, value: str) -> str:
        return model_allowed_value(value.strip(), ADMIN_DESTRUCTIVE_ACTION_KEYS, "action_key")


class AdminActionOtpConfirmRequest(AdminApiRequest):
    challenge_id: int = Field(gt=0)
    otp: str = Field(min_length=6, max_length=16)


class AdminBillingMonobankModeUpdateRequest(AdminActionOtpConfirmRequest):
    monobank_mode: str = Field(min_length=1, max_length=16)

    @field_validator("monobank_mode")
    @classmethod
    def validate_monobank_mode(cls, value: str) -> str:
        return model_allowed_value(value.strip(), MONOBANK_MODES, "monobank_mode")


class AdminBillingProviderSettingsUpdateRequest(AdminApiRequest):
    billing_provider: str | None = Field(default=None, min_length=1, max_length=16)
    monobank_mode: str | None = Field(default=None, min_length=1, max_length=16)
    challenge_id: int | None = Field(default=None, gt=0)
    otp: str | None = Field(default=None, min_length=6, max_length=16)

    @field_validator("billing_provider")
    @classmethod
    def validate_billing_provider(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return model_allowed_value(value.strip(), BILLING_PAYMENT_PROVIDERS, "billing_provider")

    @field_validator("monobank_mode")
    @classmethod
    def validate_monobank_mode(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return model_allowed_value(value.strip(), MONOBANK_MODES, "monobank_mode")

    @model_validator(mode="after")
    def validate_payload(self) -> AdminBillingProviderSettingsUpdateRequest:
        if self.billing_provider is None and self.monobank_mode is None:
            raise ValueError("Either billing_provider or monobank_mode is required")
        if (self.billing_provider is not None or self.monobank_mode is not None) and (
            self.challenge_id is None or self.otp is None
        ):
            raise ValueError("billing_provider or monobank_mode requires challenge_id and otp")
        return self


class AdminSetPasswordRequest(AdminApiRequest):
    password: str = Field(min_length=8, max_length=256)
    confirm_password: str = Field(min_length=8, max_length=256)

    @field_validator("confirm_password")
    @classmethod
    def validate_confirmation(cls, value: str, info) -> str:
        if info.data.get("password") != value:
            raise ValueError("Password confirmation does not match")
        return value


class AdminPasswordUpdateRequest(AdminApiRequest):
    current_password: str | None = Field(default=None, max_length=512)
    password: str = Field(min_length=8, max_length=256)
    confirm_password: str = Field(min_length=8, max_length=256)

    @field_validator("confirm_password")
    @classmethod
    def validate_confirmation(cls, value: str, info) -> str:
        if info.data.get("password") != value:
            raise ValueError("Password confirmation does not match")
        return value


class AdminSettingsUpdateRequest(AdminApiRequest):
    interface_locale: str | None = Field(default=None, min_length=2, max_length=8)
    app_version: str | None = Field(default=None, min_length=1, max_length=32)
    billing_settings: dict[str, Any] | None = None
    import_settings: dict[str, Any] | None = None
    subscription_settings: dict[str, Any] | None = None
    support_settings: dict[str, Any] | None = None
    analytics_settings: dict[str, Any] | None = None
    plan_limits: dict[str, Any] | None = None


class AdminProviderTaskUpdateRequest(AdminApiRequest):
    task_key: str = Field(min_length=1, max_length=128)
    provider_key: str = Field(min_length=1, max_length=128)
    is_enabled: bool = True
    config: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class AdminProviderSettingsUpdateRequest(AdminApiRequest):
    tasks: list[AdminProviderTaskUpdateRequest] = Field(min_length=1, max_length=20)


class AdminSetRoleRequest(AdminApiRequest):
    role: str = Field(min_length=1, max_length=64)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        return model_allowed_value(value.strip(), {"student", "admin", "admin_editor"}, "role")


class AdminSetLearningRoleRequest(AdminApiRequest):
    learning_role: str = Field(min_length=1, max_length=32)

    @field_validator("learning_role")
    @classmethod
    def validate_learning_role(cls, value: str) -> str:
        return model_allowed_value(value.strip(), {"student", "teacher"}, "learning_role")


class AdminSetSubscriptionRequest(AdminApiRequest):
    plan_key: str = Field(min_length=1, max_length=64)

    @field_validator("plan_key")
    @classmethod
    def validate_plan_key(cls, value: str) -> str:
        return model_allowed_value(value.strip(), {plan.key for plan in list_subscription_plans()}, "plan_key")


class AdminSetSubscriptionTrialRequest(AdminApiRequest):
    is_trial_enabled: bool


class AdminTeacherAssignmentRequest(AdminApiRequest):
    teacher_user_id: UUID
    student_user_id: UUID


class AdminDictionaryVerifyRequest(AdminApiRequest):
    entry_ids: list[int] = Field(min_length=1, max_length=500)

    @field_validator("entry_ids")
    @classmethod
    def validate_entry_ids(cls, value: list[int]) -> list[int]:
        return model_positive_id_list(value, "entry_ids")


class AdminUserDictionaryPromoteRequest(AdminApiRequest):
    entry_ids: list[int] = Field(min_length=1, max_length=500)

    @field_validator("entry_ids")
    @classmethod
    def validate_entry_ids(cls, value: list[int]) -> list[int]:
        return model_positive_id_list(value, "entry_ids")


class AdminUserDictionaryBulkActionRequest(AdminApiRequest):
    action: str = Field(min_length=1, max_length=64)
    entry_ids: list[int] = Field(min_length=1, max_length=500)

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        return model_allowed_value(value.strip(), USER_DICTIONARY_BULK_ACTIONS, "action")

    @field_validator("entry_ids")
    @classmethod
    def validate_entry_ids(cls, value: list[int]) -> list[int]:
        return model_positive_id_list(value, "entry_ids")


class AdminDictionaryEntryUpdateRequest(AdminApiRequest):
    word: str | None = Field(default=None, max_length=120)
    transcription: str | None = Field(default=None, max_length=500)
    phonetic_us: str | None = Field(default=None, max_length=500)
    translation_uk: str | None = Field(default=None, max_length=500)
    translation_ru: str | None = Field(default=None, max_length=500)
    translation_pl: str | None = Field(default=None, max_length=500)
    examples_json: list[str] | str | None = None
    entry_type: str | None = Field(default=None, min_length=1, max_length=32)

    @field_validator("entry_type")
    @classmethod
    def validate_entry_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return model_allowed_value(value.strip(), set(DICTIONARY_ENTRY_TYPES), "entry_type")
