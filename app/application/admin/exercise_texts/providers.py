from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.domain.provider_settings import (
    EXERCISE_TEXT_GENERATION_TASK_KEY as EXERCISE_TEXT_GENERATION_TASK_KEY,
)
from app.domain.provider_settings import (
    EXERCISE_TEXT_TTS_TASK_KEY as EXERCISE_TEXT_TTS_TASK_KEY,
)


@dataclass(frozen=True)
class ExerciseTextGenerationRequest:
    stage: str
    exercise_text: dict[str, Any]


@dataclass(frozen=True)
class ExerciseTextGenerationResult:
    raw_json_text: str
    usage: Any | None = None


class ExerciseTextGenerationProvider(Protocol):
    provider_key: str
    model: str

    def generate(self, request: ExerciseTextGenerationRequest) -> ExerciseTextGenerationResult:
        ...


class ExerciseTextGenerationProviderDisabledError(Exception):
    pass


class UnsupportedExerciseTextGenerationProviderError(Exception):
    def __init__(self, provider_key: str) -> None:
        self.provider_key = provider_key
        super().__init__(provider_key)


class ExerciseTextGenerationProviderFactory(Protocol):
    def __call__(
        self,
        *,
        settings: Any,
        configured: dict[str, Any] | None,
    ) -> ExerciseTextGenerationProvider:
        ...


@dataclass(frozen=True)
class ExerciseTextTTSRequest:
    text: str
    language_code: str
    voice_code: str


@dataclass(frozen=True)
class ExerciseTextTTSResult:
    audio_bytes: bytes
    timestamps: list[dict[str, Any]]


class ExerciseTextTTSProvider(Protocol):
    provider_key: str

    def synthesize(self, request: ExerciseTextTTSRequest) -> ExerciseTextTTSResult:
        ...


class ExerciseTextTTSProviderDisabledError(Exception):
    pass


class UnsupportedExerciseTextTTSProviderError(Exception):
    def __init__(self, provider_key: str) -> None:
        self.provider_key = provider_key
        super().__init__(provider_key)


class ExerciseTextTTSProviderFactory(Protocol):
    def __call__(self, *, configured: dict[str, Any] | None) -> ExerciseTextTTSProvider:
        ...
