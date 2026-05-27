from __future__ import annotations

from dataclasses import dataclass
from typing import Any

WORD_VALIDATION_TASK_KEY = "user_import.word_validation"
WORD_DETAILS_TASK_KEY = "user_import.word_details"
WORD_AUDIO_TASK_KEY = "user_import.word_audio"
WORD_EMBEDDINGS_TASK_KEY = "user_import.embeddings"
EXERCISE_TEXT_GENERATION_TASK_KEY = "exercise_texts.content_generation"
EXERCISE_TEXT_TTS_TASK_KEY = "exercise_texts.tts"
DEFAULT_OPENAI_API_URL = "https://api.openai.com/v1/responses"
DEFAULT_USER_IMPORT_OPENAI_MODEL = "gpt-5.4-mini"
DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@dataclass(frozen=True)
class ProviderTask:
    task_key: str
    title: str
    description: str
    default_provider_key: str
    allowed_provider_keys: tuple[str, ...]
    default_config: dict[str, Any]


@dataclass(frozen=True)
class ProviderTaskSetting:
    task_key: str
    provider_key: str
    is_enabled: bool
    config: dict[str, Any]


def normalize_provider_key(value: str | None) -> str:
    return str(value or "").strip().lower().replace("-", "_")


PROVIDER_TASKS: tuple[ProviderTask, ...] = (
    ProviderTask(
        task_key=WORD_VALIDATION_TASK_KEY,
        title="Import word validation",
        description="Optional AI validation for imported words and short idioms.",
        default_provider_key="disabled",
        allowed_provider_keys=("disabled", "openai"),
        default_config={},
    ),
    ProviderTask(
        task_key=WORD_DETAILS_TASK_KEY,
        title="User import word details",
        description="Structured JSON enrichment for part of speech, translations, IPA and examples.",
        default_provider_key="openai",
        allowed_provider_keys=("disabled", "openai"),
        default_config={},
    ),
    ProviderTask(
        task_key=WORD_AUDIO_TASK_KEY,
        title="User import word audio",
        description="Audio synthesis for imported and approved dictionary words.",
        default_provider_key="google_tts",
        allowed_provider_keys=("google_tts",),
        default_config={},
    ),
    ProviderTask(
        task_key=WORD_EMBEDDINGS_TASK_KEY,
        title="User import embeddings",
        description="Vector embedding build for imported dictionary entries.",
        default_provider_key="local_sentence_transformers",
        allowed_provider_keys=("disabled", "local_sentence_transformers"),
        default_config={},
    ),
    ProviderTask(
        task_key=EXERCISE_TEXT_GENERATION_TASK_KEY,
        title="Exercise text generation",
        description="Structured JSON generation for exercise text content, translations and quiz stages.",
        default_provider_key="openai",
        allowed_provider_keys=("disabled", "openai"),
        default_config={},
    ),
    ProviderTask(
        task_key=EXERCISE_TEXT_TTS_TASK_KEY,
        title="Exercise text TTS",
        description="Audio synthesis for exercise text full and paragraph-level English audio.",
        default_provider_key="google_tts",
        allowed_provider_keys=("disabled", "google_tts"),
        default_config={},
    ),
)

_TASKS_BY_KEY = {task.task_key: task for task in PROVIDER_TASKS}


def list_provider_tasks() -> list[ProviderTask]:
    return list(PROVIDER_TASKS)


def get_provider_task(task_key: str) -> ProviderTask:
    try:
        return _TASKS_BY_KEY[task_key]
    except KeyError as error:
        raise ValueError(f"Unsupported external provider task: {task_key}") from error


def resolve_provider_task_setting(
    task: ProviderTask,
    *,
    configured: dict[str, Any] | None,
    fallback_provider_key: str | None = None,
    fallback_config: dict[str, Any] | None = None,
) -> ProviderTaskSetting:
    configured = configured or {}
    provider_key = normalize_provider_key(
        configured.get("provider_key") or fallback_provider_key or task.default_provider_key
    )
    if provider_key not in task.allowed_provider_keys:
        provider_key = normalize_provider_key(fallback_provider_key or task.default_provider_key)
    config = {
        **task.default_config,
        **(fallback_config or {}),
        **dict(configured.get("config_json") or configured.get("config") or {}),
    }
    is_enabled = bool(configured.get("is_enabled", True)) and provider_key not in {"", "none", "disabled"}
    return ProviderTaskSetting(
        task_key=task.task_key,
        provider_key=provider_key or "disabled",
        is_enabled=is_enabled,
        config=config,
    )
