from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.admin_api.schema_validators import model_positive_id_list
from app.application.admin.exercise_texts.content_jsonb import DIFFICULTY_BANDS, TEXT_TYPES


class ExerciseTextAdminRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExerciseTextForceMetadata(ExerciseTextAdminRequest):
    reason: str = Field(min_length=1, max_length=500)


class ExerciseTextCreateRequest(ExerciseTextAdminRequest):
    title: str | None = Field(default=None, max_length=240)
    difficulty_band: str | None = None
    text_types: list[str] = Field(default_factory=list, max_length=12)
    topic_ids: list[int] = Field(default_factory=list, max_length=50)
    content_jsonb: dict[str, Any] = Field(default_factory=lambda: {"schema_version": 1})
    force_topic_difficulty: ExerciseTextForceMetadata | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        normalized = value.strip() if value is not None else None
        return normalized or None

    @field_validator("difficulty_band")
    @classmethod
    def validate_difficulty_band(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if normalized not in DIFFICULTY_BANDS:
            raise ValueError(f"difficulty_band must be one of: {', '.join(DIFFICULTY_BANDS)}")
        return normalized

    @field_validator("text_types")
    @classmethod
    def validate_text_types(cls, value: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(item.strip() for item in value if item.strip()))
        unsupported = [item for item in normalized if item not in TEXT_TYPES]
        if unsupported:
            raise ValueError(f"text_types contains unsupported value: {unsupported[0]}")
        return normalized

    @field_validator("topic_ids")
    @classmethod
    def validate_topic_ids(cls, value: list[int]) -> list[int]:
        return model_positive_id_list(value, "topic_ids")


class ExerciseTextUpdateRequest(ExerciseTextCreateRequest):
    version: int = Field(gt=0)
    content_jsonb: dict[str, Any] | None = None


class ExerciseTextVersionedActionRequest(ExerciseTextAdminRequest):
    version: int = Field(gt=0)


class ExerciseTextPublishRequest(ExerciseTextVersionedActionRequest):
    force_topic_difficulty: ExerciseTextForceMetadata | None = None


class ExerciseTextParagraphConfirmRequest(ExerciseTextVersionedActionRequest):
    stage: str = Field(min_length=1, max_length=40)

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, value: str) -> str:
        normalized = value.strip()
        allowed_stages = ("content", "translations", "quiz")
        if normalized not in allowed_stages:
            raise ValueError(f"stage must be one of: {', '.join(allowed_stages)}")
        return normalized


class ExerciseTextTTSGenerationRequest(ExerciseTextAdminRequest):
    voice_code: str | None = Field(default=None, max_length=120)

    @field_validator("voice_code")
    @classmethod
    def normalize_voice_code(cls, value: str | None) -> str | None:
        normalized = value.strip() if value is not None else None
        return normalized or None
