from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.user_import.services.user_dictionary_build_service import UserDictionaryBuildService

CURRENT_TIME = datetime(2026, 5, 3, 12, 0, 0)


class FakeAudioStorageProvider:
    def delete_if_under_roots(self, audio_path, audio_roots) -> bool:
        return False


class FakeSettings:
    app_user_import_test_mode = True
    app_user_import_google_tts_language_code = "en-US"
    app_user_import_google_tts_voice_name = "en-US-Neural2-F"
    app_user_import_embeddings_model = "demo-model"
    app_user_import_embeddings_device = "cpu"


class FakeUserDictionary:
    def __init__(self) -> None:
        self.entries: dict[int, dict[str, Any]] = {}
        self.available_entries: list[int] = []
        self.list_calls: list[dict[str, Any]] = []

    def list_entries_by_status(self, status: str, *, limit: int) -> list[dict[str, Any]]:
        self.list_calls.append({"status": status, "limit": limit})
        return [dict(row) for row in self.entries.values() if row["status"] == status][:limit]

    def update_entry_details(self, entry_id: int, **kwargs: Any) -> dict[str, Any]:
        self.entries[entry_id].update(kwargs)
        return dict(self.entries[entry_id])

    def update_entry_audio(self, entry_id: int, **kwargs: Any) -> dict[str, Any]:
        self.entries[entry_id].update(kwargs)
        return dict(self.entries[entry_id])

    def update_entry_embedding(self, entry_id: int, **kwargs: Any) -> dict[str, Any]:
        self.entries[entry_id].update(kwargs)
        return dict(self.entries[entry_id])

    def update_entry_status(self, entry_id: int, **kwargs: Any) -> dict[str, Any]:
        self.entries[entry_id].update(kwargs)
        return dict(self.entries[entry_id])

    def mark_assignments_available_for_entry(self, entry_id: int, *, current_time: datetime) -> int:
        self.available_entries.append(entry_id)
        return 1


class FakeImportItems:
    def __init__(self) -> None:
        self.items_by_entry: dict[int, list[dict[str, Any]]] = {}
        self.synced: list[dict[str, Any]] = []

    def list_by_user_dictionary_entry(self, entry_id: int) -> list[dict[str, Any]]:
        return list(self.items_by_entry.get(entry_id, []))

    def sync_for_user_dictionary_entry(self, entry_id: int, **kwargs: Any) -> None:
        self.synced.append({"entry_id": entry_id, **kwargs})


class FakeAppSettings:
    def __init__(self) -> None:
        self.values = {"user_import.runtime_settings": {"embedding_build_enabled": True}}

    def get_value(self, key: str) -> dict[str, Any] | None:
        return self.values.get(key)


class FakeExternalProviderSettings:
    def __init__(self) -> None:
        self.values: dict[str, dict[str, Any]] = {}

    def get_map(self) -> dict[str, dict[str, Any]]:
        return dict(self.values)


class FakeDb:
    def __init__(self) -> None:
        self.settings = FakeSettings()
        self.app_settings = FakeAppSettings()
        self.external_provider_settings = FakeExternalProviderSettings()
        self.user_dictionary = FakeUserDictionary()
        self.user_import_items = FakeImportItems()
        self.error_logs = FakeErrorLogRepository()

    @property
    def logged_errors(self) -> list[dict[str, Any]]:
        return self.error_logs.rows


class FakeErrorLogRepository:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def create(self, level: str, text: str, *, context_json: dict[str, Any] | None = None) -> None:
        self.rows.append({"level": level, "text": text, "context_json": context_json or {}})


class Resolver:
    def __init__(self, result: Any) -> None:
        self.result = result

    def resolve(self, **kwargs: Any) -> Any:
        return self.result


def build_service(
    db: FakeDb,
    *,
    audio_storage_provider: FakeAudioStorageProvider | None = None,
    resolver_result: Any | None = None,
    audio_path: str | None = "word_base/user/noun/apple.mp3",
    audio_calls: list[dict[str, Any]] | None = None,
    embedding: list[float] | None = None,
    details_batch_size: int = 100,
    retry_sleeps: list[float] | None = None,
) -> UserDictionaryBuildService:
    def audio_builder(**kwargs: Any) -> tuple[str | None, dict[str, Any], str | None]:
        if audio_calls is not None:
            audio_calls.append(kwargs)
        return audio_path, {"status": "ok"}, None

    return UserDictionaryBuildService(
        db,
        audio_storage_provider=audio_storage_provider or FakeAudioStorageProvider(),
        user_audio_root=Path("word_base/user"),
        resolver=Resolver(resolver_result or build_resolution()),
        audio_builder=audio_builder,
        embedding_builder=lambda **kwargs: (embedding, {"status": "ok", "model": "demo-model"}, None),
        error_masker=lambda error, fallback: str(error or fallback),
        max_jobs_per_run=10,
        details_batch_size=details_batch_size,
        retry_sleep_func=(retry_sleeps.append if retry_sleeps is not None else (lambda _seconds: None)),
    )


def build_resolution(**overrides: Any) -> SimpleNamespace:
    payload = {
        "word": "apple",
        "entry_type": "word",
        "part_of_speech": "noun",
        "level_id": 1,
        "phonetic_us": "/apple/",
        "translation_uk": "яблуко",
        "translation_ru": "яблоко",
        "translation_pl": "jablko",
        "examples_json": ["I eat an apple."],
        "source_provider_status_json": {"details": {"status": "ok"}},
        "rejected_reason": None,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_process_due_details_builds_moves_valid_entry_to_audio_queue() -> None:
    db = FakeDb()
    audio_storage_provider = FakeAudioStorageProvider()
    db.user_dictionary.entries[10] = {"id": 10, "word": "apple", "part_of_speech": "noun", "status": "queued_for_details"}
    db.user_import_items.items_by_entry[10] = [{"id": 5, "telegram_user_id": 42}]

    summary = build_service(db, audio_storage_provider=audio_storage_provider).process_due_details_builds(
        current_time=CURRENT_TIME,
    )

    assert summary == {"queued_for_audio_count": 1, "details_failed_count": 0}
    assert db.user_dictionary.entries[10]["status"] == "queued_for_audio"
    assert db.user_dictionary.entries[10]["source_provider_status_json"]["details_validation"]["attempt_count"] == 1
    assert db.user_dictionary.entries[10]["audio_storage_provider"] is audio_storage_provider
    assert db.user_import_items.synced[0]["status"] == "queued_for_audio"


def test_process_due_details_builds_drains_all_queued_entries_in_batches() -> None:
    db = FakeDb()
    for entry_id in range(1, 26):
        db.user_dictionary.entries[entry_id] = {
            "id": entry_id,
            "word": f"word-{entry_id}",
            "part_of_speech": "noun",
            "status": "queued_for_details",
        }

    summary = build_service(db, details_batch_size=10).process_due_details_builds(
        current_time=CURRENT_TIME,
    )

    assert summary == {"queued_for_audio_count": 25, "details_failed_count": 0}
    assert all(row["status"] == "queued_for_audio" for row in db.user_dictionary.entries.values())
    assert [call["limit"] for call in db.user_dictionary.list_calls] == [10, 10, 10, 10]


def test_process_due_details_builds_rejects_entry_without_examples() -> None:
    db = FakeDb()
    db.user_dictionary.entries[10] = {"id": 10, "word": "apple", "part_of_speech": "noun", "status": "queued_for_details"}

    summary = build_service(db, resolver_result=build_resolution(examples_json=[])).process_due_details_builds(
        current_time=CURRENT_TIME,
    )

    assert summary == {"queued_for_audio_count": 0, "details_failed_count": 1}
    assert db.user_dictionary.entries[10]["status"] == "details_failed"
    assert db.user_import_items.synced[0]["error_text"] == "не знайдено examples_json"
    assert db.user_dictionary.entries[10]["source_provider_status_json"]["details_validation"]["attempt_count"] == 3


def test_process_due_details_builds_marks_unhandled_entry_error_failed_and_continues() -> None:
    db = FakeDb()
    for entry_id in (1, 2, 3):
        db.user_dictionary.entries[entry_id] = {
            "id": entry_id,
            "word": f"word-{entry_id}",
            "part_of_speech": "noun",
            "status": "queued_for_details",
        }
    service = build_service(db, details_batch_size=2)
    original_build_entry_details = service.build_entry_details

    def build_or_fail(entry: dict[str, Any], **kwargs: Any) -> str:
        if entry["id"] == 2:
            raise RuntimeError("unexpected row failure")
        return original_build_entry_details(entry, **kwargs)

    service.build_entry_details = build_or_fail  # type: ignore[method-assign]

    summary = service.process_due_details_builds(
        current_time=CURRENT_TIME,
    )

    assert summary == {"queued_for_audio_count": 2, "details_failed_count": 1}
    assert db.user_dictionary.entries[1]["status"] == "queued_for_audio"
    assert db.user_dictionary.entries[2]["status"] == "details_failed"
    assert db.user_dictionary.entries[3]["status"] == "queued_for_audio"
    assert db.user_import_items.synced[-1]["entry_id"] == 3


def test_process_due_details_builds_sends_validation_feedback_to_next_retry() -> None:
    db = FakeDb()
    db.user_dictionary.entries[10] = {
        "id": 10,
        "word": "take pains",
        "part_of_speech": "verb",
        "status": "queued_for_details",
    }
    retry_sleeps: list[float] = []

    class FeedbackResolver:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        def resolve(self, **kwargs: Any) -> Any:
            self.calls.append(kwargs)
            if len(self.calls) == 1:
                return build_resolution(
                    word="take pains",
                    examples_json=[],
                    rejected_reason="example 0: gap builder could not blank usage form",
                )
            return build_resolution(
                word="take pains",
                part_of_speech="verb",
                examples_json=["They take pains to review every detail carefully."],
            )

    resolver = FeedbackResolver()
    service = UserDictionaryBuildService(
        db,
        audio_storage_provider=FakeAudioStorageProvider(),
        user_audio_root=Path("word_base/user"),
        resolver=resolver,
        audio_builder=lambda **kwargs: ("word_base/user/verb/take-pains.mp3", {"status": "ok"}, None),
        embedding_builder=lambda **kwargs: ([0.1, 0.2], {"status": "ok", "model": "demo-model"}, None),
        error_masker=lambda error, fallback: str(error or fallback),
        max_jobs_per_run=10,
        retry_sleep_func=retry_sleeps.append,
    )

    summary = service.process_due_details_builds(
        current_time=CURRENT_TIME,
    )

    assert summary == {"queued_for_audio_count": 1, "details_failed_count": 0}
    assert resolver.calls[0]["details_retry_feedback"] is None
    assert "gap builder could not blank usage form" in resolver.calls[1]["details_retry_feedback"]
    assert 'exact lookup_word phrase "take pains"' in resolver.calls[1]["details_retry_feedback"]
    assert retry_sleeps == [2.0]


def test_process_due_details_builds_retries_provider_error_before_success() -> None:
    db = FakeDb()
    db.user_dictionary.entries[10] = {"id": 10, "word": "apple", "part_of_speech": "noun", "status": "queued_for_details"}
    retry_sleeps: list[float] = []
    resolver = Resolver(build_resolution())
    calls = {"count": 0}

    def flaky_resolve(**kwargs: Any) -> Any:
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("temporary provider outage")
        return build_resolution()

    resolver.resolve = flaky_resolve  # type: ignore[method-assign]
    service = UserDictionaryBuildService(
        db,
        audio_storage_provider=FakeAudioStorageProvider(),
        user_audio_root=Path("word_base/user"),
        resolver=resolver,
        audio_builder=lambda **kwargs: ("word_base/user/noun/apple.mp3", {"status": "ok"}, None),
        embedding_builder=lambda **kwargs: ([0.1, 0.2], {"status": "ok", "model": "demo-model"}, None),
        error_masker=lambda error, fallback: str(error or fallback),
        max_jobs_per_run=10,
        retry_sleep_func=retry_sleeps.append,
    )

    summary = service.process_due_details_builds(
        current_time=CURRENT_TIME,
    )

    assert summary == {"queued_for_audio_count": 1, "details_failed_count": 0}
    assert calls["count"] == 3
    assert retry_sleeps == [2.0, 2.0]
    assert db.user_dictionary.entries[10]["source_provider_status_json"]["details_validation"]["attempt_count"] == 3


def test_process_due_details_builds_persists_provider_retry_failure_status() -> None:
    db = FakeDb()
    db.user_dictionary.entries[10] = {
        "id": 10,
        "word": "apple",
        "part_of_speech": "noun",
        "status": "queued_for_details",
        "source_provider_status_json": {"existing": True},
    }
    retry_sleeps: list[float] = []

    class FailingResolver:
        def resolve(self, **kwargs: Any) -> Any:
            raise RuntimeError("provider offline")

    service = UserDictionaryBuildService(
        db,
        audio_storage_provider=FakeAudioStorageProvider(),
        user_audio_root=Path("word_base/user"),
        resolver=FailingResolver(),
        audio_builder=lambda **kwargs: ("word_base/user/noun/apple.mp3", {"status": "ok"}, None),
        embedding_builder=lambda **kwargs: ([0.1, 0.2], {"status": "ok", "model": "demo-model"}, None),
        error_masker=lambda error, fallback: str(error or fallback),
        max_jobs_per_run=10,
        retry_sleep_func=retry_sleeps.append,
    )

    summary = service.process_due_details_builds(
        current_time=CURRENT_TIME,
    )

    provider_status = db.user_dictionary.entries[10]["source_provider_status_json"]
    assert summary == {"queued_for_audio_count": 0, "details_failed_count": 1}
    assert retry_sleeps == [2.0, 2.0]
    assert provider_status["existing"] is True
    assert provider_status["details_phase"]["attempt_count"] == 3
    assert provider_status["details_phase"]["error"] == "provider offline"
    assert db.logged_errors[-1]["context_json"]["stage"] == "details"
    assert db.logged_errors[-1]["context_json"]["user_dictionary_entry_id"] == 10


def test_audio_and_embedding_make_entry_available_for_rotation() -> None:
    db = FakeDb()
    audio_calls: list[dict[str, Any]] = []
    db.user_dictionary.entries[10] = {
        "id": 10,
        "word": "apple",
        "part_of_speech": "noun",
        "translation_uk": "яблуко",
        "examples_json": ["I eat an apple."],
        "status": "queued_for_audio",
    }
    service = build_service(db, audio_calls=audio_calls, embedding=[0.1, 0.2])

    audio_summary = service.process_due_audio_builds(current_time=CURRENT_TIME)
    embedding_summary = service.process_due_embedding_builds(current_time=CURRENT_TIME)

    assert audio_summary["queued_for_embedding_count"] == 1
    assert audio_calls[0]["audio_dir"] == Path("word_base/user/noun")
    assert embedding_summary["ready_for_rotation_count"] == 1
    assert db.user_dictionary.entries[10]["status"] == "ready_for_rotation"
    assert db.user_dictionary.entries[10]["source_provider_status_json"]["google_tts"]["attempt_count"] == 1
    assert db.user_dictionary.entries[10]["source_provider_status_json"]["embedding_phase"]["attempt_count"] == 1
    assert db.user_dictionary.available_entries == [10]
    assert db.user_import_items.synced[-1]["status"] == "ready_for_rotation"


def test_process_due_audio_builds_drains_all_batches() -> None:
    db = FakeDb()
    for entry_id in range(25):
        db.user_dictionary.entries[entry_id] = {
            "id": entry_id,
            "word": f"word-{entry_id}",
            "part_of_speech": "noun",
            "translation_uk": "слово",
            "examples_json": ["Example."],
            "status": "queued_for_audio",
        }
    service = build_service(db)

    summary = service.process_due_audio_builds(current_time=CURRENT_TIME)

    assert summary == {
        "ready_for_rotation_count": 0,
        "queued_for_embedding_count": 25,
        "audio_failed_count": 0,
    }
    assert len(db.user_dictionary.list_calls) == 4
    assert all(row["status"] == "queued_for_embedding" for row in db.user_dictionary.entries.values())


def test_audio_phase_respects_configured_schedule() -> None:
    db = FakeDb()
    db.settings.app_user_import_test_mode = False
    db.app_settings.values["user_import.runtime_settings"] = {
        "audio_build_hour": 2,
        "audio_build_weekdays": [0, 1, 2, 3, 4, 5, 6],
    }
    service = build_service(db)

    assert service.should_run_audio_phase(datetime(2026, 5, 3, 1, 0, 0)) is False
    assert service.should_run_audio_phase(datetime(2026, 5, 3, 2, 0, 0)) is True


def test_audio_never_marks_entry_ready_without_embedding_even_when_embedding_worker_disabled() -> None:
    db = FakeDb()
    db.app_settings.values["user_import.runtime_settings"] = {"embedding_build_enabled": False}
    db.user_dictionary.entries[10] = {
        "id": 10,
        "word": "apple",
        "part_of_speech": "noun",
        "translation_uk": "яблуко",
        "examples_json": ["I eat an apple."],
        "status": "queued_for_audio",
    }

    audio_summary = build_service(db).process_due_audio_builds(current_time=CURRENT_TIME)
    embedding_summary = build_service(db, embedding=[0.1, 0.2]).process_due_embedding_builds(current_time=CURRENT_TIME)

    assert audio_summary == {
        "ready_for_rotation_count": 0,
        "queued_for_embedding_count": 1,
        "audio_failed_count": 0,
    }
    assert embedding_summary == {
        "ready_for_rotation_count": 0,
        "retry_scheduled_count": 0,
        "embedding_failed_count": 0,
    }
    assert db.user_dictionary.entries[10]["status"] == "queued_for_embedding"
    assert db.user_dictionary.available_entries == []
    assert db.user_import_items.synced[-1]["status"] == "queued_for_embedding"


def test_embedding_build_uses_provider_task_config() -> None:
    db = FakeDb()
    calls: list[dict[str, Any]] = []
    db.external_provider_settings.values["user_import.embeddings"] = {
        "provider_key": "local_sentence_transformers",
        "is_enabled": True,
        "config_json": {"model": "db-model", "device": "cuda"},
    }
    db.user_dictionary.entries[10] = {
        "id": 10,
        "word": "apple",
        "part_of_speech": "noun",
        "translation_uk": "яблуко",
        "examples_json": ["I eat an apple."],
        "status": "queued_for_embedding",
    }

    def embedding_builder(**kwargs: Any):
        calls.append(kwargs)
        return [0.1, 0.2], {"status": "ok", "model": kwargs["model_name"]}, None

    service = UserDictionaryBuildService(
        db,
        audio_storage_provider=FakeAudioStorageProvider(),
        user_audio_root=Path("word_base/user"),
        resolver=Resolver(build_resolution()),
        audio_builder=lambda **kwargs: ("word_base/user/noun/apple.mp3", {"status": "ok"}, None),
        embedding_builder=embedding_builder,
        error_masker=lambda error, fallback: str(error or fallback),
        max_jobs_per_run=10,
    )

    service.process_due_embedding_builds(current_time=CURRENT_TIME)

    assert calls[0]["model_name"] == "db-model"
    assert calls[0]["device"] == "cuda"


def test_embedding_build_marks_failed_when_provider_disabled() -> None:
    db = FakeDb()
    db.external_provider_settings.values["user_import.embeddings"] = {
        "provider_key": "disabled",
        "is_enabled": False,
        "config_json": {},
    }
    db.user_dictionary.entries[10] = {
        "id": 10,
        "word": "apple",
        "part_of_speech": "noun",
        "translation_uk": "яблуко",
        "examples_json": ["I eat an apple."],
        "status": "queued_for_embedding",
    }

    summary = build_service(db, embedding=[0.1, 0.2]).process_due_embedding_builds(current_time=CURRENT_TIME)

    assert summary == {"ready_for_rotation_count": 0, "retry_scheduled_count": 0, "embedding_failed_count": 1}
    assert db.user_dictionary.entries[10]["status"] == "embedding_failed"
    assert db.user_import_items.synced[-1]["error_text"] == "Embedding provider is disabled"
    assert db.logged_errors[-1]["context_json"]["stage"] == "embedding"
    assert db.logged_errors[-1]["context_json"]["provider_key"] == "disabled"


def test_audio_failure_retries_provider_exceptions_and_marks_failed() -> None:
    db = FakeDb()
    calls: list[dict[str, Any]] = []
    retry_sleeps: list[float] = []
    db.user_dictionary.entries[10] = {
        "id": 10,
        "word": "apple",
        "part_of_speech": "noun",
        "translation_uk": "яблуко",
        "examples_json": ["I eat an apple."],
        "status": "queued_for_audio",
    }

    def failing_audio(**kwargs: Any) -> tuple[str | None, dict[str, Any], str | None]:
        calls.append(kwargs)
        raise RuntimeError("google tts timeout")

    service = UserDictionaryBuildService(
        db,
        audio_storage_provider=FakeAudioStorageProvider(),
        user_audio_root=Path("word_base/user"),
        resolver=Resolver(build_resolution()),
        audio_builder=failing_audio,
        embedding_builder=lambda **kwargs: ([0.1, 0.2], {"status": "ok", "model": "demo-model"}, None),
        error_masker=lambda error, fallback: str(error or fallback),
        max_jobs_per_run=10,
        retry_sleep_func=retry_sleeps.append,
    )

    summary = service.process_due_audio_builds(current_time=CURRENT_TIME)

    assert summary == {
        "ready_for_rotation_count": 0,
        "queued_for_embedding_count": 0,
        "audio_failed_count": 1,
    }
    assert len(calls) == 3
    assert retry_sleeps == [2.0, 2.0]
    assert db.user_dictionary.entries[10]["status"] == "audio_failed"
    assert db.user_dictionary.entries[10]["source_provider_status_json"]["google_tts"] == {
        "status": "error",
        "error_type": "RuntimeError",
        "attempt_count": 3,
    }
    assert db.user_import_items.synced[-1]["error_text"] == "google tts timeout"
    assert db.logged_errors[-1]["context_json"]["stage"] == "audio"
    assert db.logged_errors[-1]["text"].startswith("domain=user_import stage=audio")


def test_embedding_failure_retries_three_times_and_marks_failed() -> None:
    db = FakeDb()
    calls: list[dict[str, Any]] = []
    retry_sleeps: list[float] = []
    db.user_dictionary.entries[10] = {
        "id": 10,
        "word": "apple",
        "part_of_speech": "noun",
        "translation_uk": "яблуко",
        "examples_json": ["I eat an apple."],
        "status": "queued_for_embedding",
    }

    def failing_embedding(**kwargs: Any) -> tuple[None, dict[str, Any], str]:
        calls.append(kwargs)
        return None, {"status": "error", "model": "demo-model"}, "out of memory"

    service = UserDictionaryBuildService(
        db,
        audio_storage_provider=FakeAudioStorageProvider(),
        user_audio_root=Path("word_base/user"),
        resolver=Resolver(build_resolution()),
        audio_builder=lambda **kwargs: ("word_base/user/noun/apple.mp3", {"status": "ok"}, None),
        embedding_builder=failing_embedding,
        error_masker=lambda error, fallback: str(error or fallback),
        max_jobs_per_run=10,
        retry_sleep_func=retry_sleeps.append,
    )

    summary = service.process_due_embedding_builds(current_time=CURRENT_TIME)

    assert summary == {"ready_for_rotation_count": 0, "retry_scheduled_count": 0, "embedding_failed_count": 1}
    assert len(calls) == 3
    assert retry_sleeps == [2.0, 2.0]
    assert db.user_dictionary.entries[10]["status"] == "embedding_failed"
    assert db.user_dictionary.entries[10]["source_provider_status_json"]["embedding_phase"]["last_error"] == "out of memory"
    assert db.user_import_items.synced[-1]["status"] == "embedding_failed"
    assert db.logged_errors[-1]["context_json"]["stage"] == "embedding"


def test_embedding_failure_retries_provider_exceptions_and_marks_failed() -> None:
    db = FakeDb()
    calls: list[dict[str, Any]] = []
    retry_sleeps: list[float] = []
    db.user_dictionary.entries[10] = {
        "id": 10,
        "word": "apple",
        "part_of_speech": "noun",
        "translation_uk": "яблуко",
        "examples_json": ["I eat an apple."],
        "status": "queued_for_embedding",
    }

    def failing_embedding(**kwargs: Any) -> tuple[list[float] | None, dict[str, Any], str | None]:
        calls.append(kwargs)
        raise RuntimeError("CUDA out of memory")

    service = UserDictionaryBuildService(
        db,
        audio_storage_provider=FakeAudioStorageProvider(),
        user_audio_root=Path("word_base/user"),
        resolver=Resolver(build_resolution()),
        audio_builder=lambda **kwargs: ("word_base/user/noun/apple.mp3", {"status": "ok"}, None),
        embedding_builder=failing_embedding,
        error_masker=lambda error, fallback: str(error or fallback),
        max_jobs_per_run=10,
        retry_sleep_func=retry_sleeps.append,
    )

    summary = service.process_due_embedding_builds(current_time=CURRENT_TIME)

    assert summary == {"ready_for_rotation_count": 0, "retry_scheduled_count": 0, "embedding_failed_count": 1}
    assert len(calls) == 3
    assert retry_sleeps == [2.0, 2.0]
    assert db.user_dictionary.entries[10]["status"] == "embedding_failed"
    assert db.user_dictionary.entries[10]["source_provider_status_json"]["embedding_phase"] == {
        "status": "error",
        "error_type": "RuntimeError",
        "last_error": "CUDA out of memory",
        "attempt_count": 3,
    }
    assert db.user_import_items.synced[-1]["error_text"] == "CUDA out of memory"
    assert db.logged_errors[-1]["context_json"]["error_text"] == "CUDA out of memory"
