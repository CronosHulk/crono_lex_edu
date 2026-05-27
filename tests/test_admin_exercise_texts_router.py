from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.admin_api.exercise_texts.router as exercise_texts_router
from app.admin_api.context import AdminRouterContext
from app.admin_api.exercise_texts.router import build_exercise_texts_router
from app.application.admin.exercise_texts.errors import (
    AdminExerciseTextGenerationError,
    AdminExerciseTextGenerationNotFoundError,
    AdminExerciseTextServiceError,
    AdminExerciseTextServiceValidationError,
    AdminExerciseTextTTSError,
    AdminExerciseTextTTSNotFoundError,
)


class FakeAdminExerciseTextService:
    def __init__(self, error: AdminExerciseTextServiceError | None = None) -> None:
        self.calls: list[dict] = []
        self.error = error

    def list_items(self, *, actor: dict, params: dict) -> dict:
        if self.error is not None:
            raise self.error
        self.calls.append({"action": "list", "actor": actor, "params": params})
        return {"items": [{"id": 11}], "page": params["page"], "page_size": params["page_size"]}

    def create_item(self, *, actor: dict, payload: dict) -> dict:
        self.calls.append({"action": "create", "actor": actor, "payload": payload})
        return {"id": 12, **payload}

    def get_item(self, *, actor: dict, exercise_text_id: int) -> dict:
        self.calls.append({"action": "detail", "actor": actor, "exercise_text_id": exercise_text_id})
        return {"id": exercise_text_id}

    def update_item(self, *, actor: dict, exercise_text_id: int, payload: dict) -> dict:
        self.calls.append({"action": "update", "actor": actor, "exercise_text_id": exercise_text_id, "payload": payload})
        return {"id": exercise_text_id, **payload}

    def archive_item(self, *, actor: dict, exercise_text_id: int, version: int | None = None) -> dict:
        self.calls.append(
            {
                "action": "archive",
                "actor": actor,
                "exercise_text_id": exercise_text_id,
                "version": version,
            }
        )
        return {"id": exercise_text_id, "version": version, "status": "archived"}

    def mark_ready(self, *, actor: dict, exercise_text_id: int, payload: dict) -> dict:
        self.calls.append({"action": "ready", "actor": actor, "exercise_text_id": exercise_text_id, "payload": payload})
        return {"id": exercise_text_id, "status": "ready"}

    def confirm_paragraph_stage(self, *, actor: dict, exercise_text_id: int, paragraph_id: str, payload: dict) -> dict:
        self.calls.append(
            {
                "action": "confirm_paragraph",
                "actor": actor,
                "exercise_text_id": exercise_text_id,
                "paragraph_id": paragraph_id,
                "payload": payload,
            }
        )
        return {"id": exercise_text_id, "paragraph_id": paragraph_id}

    def publish_item(self, *, actor: dict, exercise_text_id: int, payload: dict) -> dict:
        self.calls.append({"action": "publish", "actor": actor, "exercise_text_id": exercise_text_id, "payload": payload})
        return {"id": exercise_text_id, "status": "published"}

    def unpublish_item(self, *, actor: dict, exercise_text_id: int, version: int) -> dict:
        self.calls.append({"action": "unpublish", "actor": actor, "exercise_text_id": exercise_text_id, "version": version})
        return {"id": exercise_text_id, "status": "ready", "version": version}

    def list_reference(self, *, actor: dict) -> dict:
        self.calls.append({"action": "reference", "actor": actor})
        return {"statuses": ["draft"]}

    def list_grammar_topics(self, *, actor: dict) -> dict:
        self.calls.append({"action": "grammar_topics", "actor": actor})
        return {"items": [{"id": 3}]}

    def list_tts_voices(self, *, actor: dict, provider: str | None = None) -> dict:
        self.calls.append({"action": "tts_voices", "actor": actor, "provider": provider})
        return {"items": [{"provider": provider}]}


class FakeAdminExerciseTextGenerationService:
    def __init__(self, error: AdminExerciseTextGenerationError | None = None) -> None:
        self.calls: list[dict] = []
        self.error = error

    def start_generation(self, *, actor: dict, exercise_text_id: int, stage: str) -> dict:
        if self.error is not None:
            raise self.error
        self.calls.append(
            {
                "action": "start_generation",
                "actor": actor,
                "exercise_text_id": exercise_text_id,
                "stage": stage,
            }
        )
        return {"task": {"stage": stage}, "exercise_text": {"id": exercise_text_id}}

    def generate_all(self, *, actor: dict, exercise_text_id: int) -> dict:
        self.calls.append({"action": "generate_all", "actor": actor, "exercise_text_id": exercise_text_id})
        return {"tasks": [], "exercise_text": {"id": exercise_text_id}}

    def get_generation_task(self, *, actor: dict, exercise_text_id: int, task_id: int) -> dict:
        self.calls.append(
            {
                "action": "generation_task",
                "actor": actor,
                "exercise_text_id": exercise_text_id,
                "task_id": task_id,
            }
        )
        return {"task": {"id": task_id}, "exercise_text": {"id": exercise_text_id}}


class FakeAdminExerciseTextTTSService:
    def __init__(self, *, audio_path: str = "word_base/exercise_texts/audio/demo/full.mp3", error: AdminExerciseTextTTSError | None = None) -> None:
        self.calls: list[dict] = []
        self.audio_path = audio_path
        self.error = error

    def start_tts_generation(self, *, actor: dict, exercise_text_id: int, voice_code: str | None = None) -> dict:
        if self.error is not None:
            raise self.error
        self.calls.append(
            {
                "action": "start_tts",
                "actor": actor,
                "exercise_text_id": exercise_text_id,
                "voice_code": voice_code,
            }
        )
        return {"task": {"stage": "tts"}, "exercise_text": {"id": exercise_text_id}}

    def get_audio_path(self, *, actor: dict, exercise_text_id: int, scope: str, paragraph_id: str | None = None) -> str:
        if self.error is not None:
            raise self.error
        self.calls.append(
            {
                "action": "audio",
                "actor": actor,
                "exercise_text_id": exercise_text_id,
                "scope": scope,
                "paragraph_id": paragraph_id,
            }
        )
        return self.audio_path


def _unused_service(name: str):
    return lambda: (_ for _ in ()).throw(AssertionError(f"{name} should not be used"))


_TEST_AUDIO_STORAGE_PROVIDER = object()


def _audio_storage_provider() -> object:
    return _TEST_AUDIO_STORAGE_PROVIDER


def test_exercise_text_core_routes_use_direct_service_context() -> None:
    exercise_text_service = FakeAdminExerciseTextService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    app = FastAPI()
    app.include_router(
        build_exercise_texts_router(
            AdminRouterContext(
                current_admin_user=lambda request: actor,
                admin_ai_usage_read_service=_unused_service("ai usage service"),
                admin_auth_service=_unused_service("auth service"),
                admin_billing_read_service=_unused_service("billing service"),
                admin_bootstrap_service=_unused_service("bootstrap service"),
                admin_dashboard_service=_unused_service("dashboard service"),
                admin_dictionary_action_service=_unused_service("dictionary action service"),
                admin_dictionary_read_service=_unused_service("dictionary read service"),
                admin_dictionary_service=_unused_service("dictionary service"),
                admin_entity_service=_unused_service("entity service"),
                admin_exercise_text_service=lambda: exercise_text_service,
                admin_exercise_text_generation_service=_unused_service("exercise text generation service"),
                admin_exercise_text_tts_service=_unused_service("exercise text tts service"),
                admin_import_read_service=_unused_service("import read service"),
                admin_log_read_service=_unused_service("log read service"),
                admin_read_service=_unused_service("read service"),
                admin_settings_service=_unused_service("settings service"),
                admin_user_dictionary_bulk_action=_unused_service("user dictionary bulk action"),
                admin_user_dictionary_promote_action=_unused_service("user dictionary promote action"),
                admin_user_dictionary_read_service=_unused_service("user dictionary read service"),
                admin_user_action_service=_unused_service("user action service"),
                admin_user_read_service=_unused_service("user read service"),
                audio_storage_provider=_audio_storage_provider,
            )
        )
    )
    client = TestClient(app)

    list_response = client.get(
        "/exercise-texts",
        params=[
            ("page", "2"),
            ("page_size", "100"),
            ("archived", "true"),
            ("search", "space"),
            ("sort", "title_asc"),
            ("status", "draft"),
            ("difficulty_band", "A1_A2"),
            ("text_type", "article"),
            ("topic_id", "3"),
            ("has_quiz", "yes"),
            ("has_tts", "no"),
        ],
    )
    create_response = client.post(
        "/exercise-texts",
        json={
            "title": "Demo",
            "difficulty_band": "A1_A2",
            "text_types": ["article"],
            "topic_ids": [3],
            "content_jsonb": {"schema_version": 1},
        },
    )
    detail_response = client.get("/exercise-texts/11")
    update_response = client.put("/exercise-texts/11", json={"version": 2, "title": "Updated"})
    delete_response = client.delete("/exercise-texts/11", params={"version": "3"})
    archive_response = client.post("/exercise-texts/11/archive", json={"version": 4})
    ready_response = client.post("/exercise-texts/11/ready", json={"version": 5})
    confirm_response = client.post(
        "/exercise-texts/11/paragraphs/p1/confirm-stage",
        json={"version": 6, "stage": "quiz"},
    )
    publish_response = client.post("/exercise-texts/11/publish", json={"version": 7})
    unpublish_response = client.post("/exercise-texts/11/unpublish", json={"version": 8})
    reference_response = client.get("/reference/exercise-text-options")
    grammar_topics_response = client.get("/reference/grammar-topics")
    tts_voices_response = client.get("/reference/tts-voices", params={"provider": "google"})

    assert list_response.status_code == 200
    assert create_response.status_code == 200
    assert detail_response.status_code == 200
    assert update_response.status_code == 200
    assert delete_response.status_code == 200
    assert archive_response.status_code == 200
    assert ready_response.status_code == 200
    assert confirm_response.status_code == 200
    assert publish_response.status_code == 200
    assert unpublish_response.status_code == 200
    assert reference_response.status_code == 200
    assert grammar_topics_response.status_code == 200
    assert tts_voices_response.status_code == 200

    assert exercise_text_service.calls == [
        {
            "action": "list",
            "actor": actor,
            "params": {
                "page": 2,
                "page_size": 100,
                "archived": True,
                "search": "space",
                "sort": "title_asc",
                "status": ["draft"],
                "difficulty_band": ["A1_A2"],
                "text_type": ["article"],
                "topic_id": [3],
                "has_quiz": "yes",
                "has_tts": "no",
            },
        },
        {
            "action": "create",
            "actor": actor,
            "payload": {
                "title": "Demo",
                "difficulty_band": "A1_A2",
                "text_types": ["article"],
                "topic_ids": [3],
                "content_jsonb": {"schema_version": 1},
            },
        },
        {"action": "detail", "actor": actor, "exercise_text_id": 11},
        {"action": "update", "actor": actor, "exercise_text_id": 11, "payload": {"title": "Updated", "version": 2}},
        {"action": "archive", "actor": actor, "exercise_text_id": 11, "version": 3},
        {"action": "archive", "actor": actor, "exercise_text_id": 11, "version": 4},
        {"action": "ready", "actor": actor, "exercise_text_id": 11, "payload": {"version": 5}},
        {
            "action": "confirm_paragraph",
            "actor": actor,
            "exercise_text_id": 11,
            "paragraph_id": "p1",
            "payload": {"version": 6, "stage": "quiz"},
        },
        {"action": "publish", "actor": actor, "exercise_text_id": 11, "payload": {"version": 7}},
        {"action": "unpublish", "actor": actor, "exercise_text_id": 11, "version": 8},
        {"action": "reference", "actor": actor},
        {"action": "grammar_topics", "actor": actor},
        {"action": "tts_voices", "actor": actor, "provider": "google"},
    ]


def test_exercise_text_core_routes_map_service_errors() -> None:
    exercise_text_service = FakeAdminExerciseTextService(
        error=AdminExerciseTextServiceValidationError("status contains unsupported value: broken")
    )
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    app = FastAPI()
    app.include_router(
        build_exercise_texts_router(
            AdminRouterContext(
                current_admin_user=lambda request: actor,
                admin_ai_usage_read_service=_unused_service("ai usage service"),
                admin_auth_service=_unused_service("auth service"),
                admin_billing_read_service=_unused_service("billing service"),
                admin_bootstrap_service=_unused_service("bootstrap service"),
                admin_dashboard_service=_unused_service("dashboard service"),
                admin_dictionary_action_service=_unused_service("dictionary action service"),
                admin_dictionary_read_service=_unused_service("dictionary read service"),
                admin_dictionary_service=_unused_service("dictionary service"),
                admin_entity_service=_unused_service("entity service"),
                admin_exercise_text_service=lambda: exercise_text_service,
                admin_exercise_text_generation_service=_unused_service("exercise text generation service"),
                admin_exercise_text_tts_service=_unused_service("exercise text tts service"),
                admin_import_read_service=_unused_service("import read service"),
                admin_log_read_service=_unused_service("log read service"),
                admin_read_service=_unused_service("read service"),
                admin_settings_service=_unused_service("settings service"),
                admin_user_dictionary_bulk_action=_unused_service("user dictionary bulk action"),
                admin_user_dictionary_promote_action=_unused_service("user dictionary promote action"),
                admin_user_dictionary_read_service=_unused_service("user dictionary read service"),
                admin_user_action_service=_unused_service("user action service"),
                admin_user_read_service=_unused_service("user read service"),
                audio_storage_provider=_audio_storage_provider,
            )
        )
    )
    client = TestClient(app)

    response = client.get("/exercise-texts", params={"status": "broken"})

    assert response.status_code == 400
    assert response.json() == {"detail": "status contains unsupported value: broken"}


def test_exercise_text_generation_and_tts_routes_use_direct_service_context(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    audio_path = "word_base/exercise_texts/audio/demo/full.mp3"
    audio_file = tmp_path / audio_path
    audio_file.parent.mkdir(parents=True)
    audio_file.write_bytes(b"audio")
    generation_service = FakeAdminExerciseTextGenerationService()
    tts_service = FakeAdminExerciseTextTTSService(audio_path=audio_path)
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    audio_storage_provider = object()
    audio_response_calls = []
    monkeypatch.setattr(
        exercise_texts_router,
        "build_audio_response",
        lambda response_audio_path, *, storage_provider: audio_response_calls.append(
            {"audio_path": response_audio_path, "storage_provider": storage_provider}
        )
        or {"audio": response_audio_path},
    )
    app = FastAPI()
    app.include_router(
        build_exercise_texts_router(
            AdminRouterContext(
                current_admin_user=lambda request: actor,
                admin_ai_usage_read_service=_unused_service("ai usage service"),
                admin_auth_service=_unused_service("auth service"),
                admin_billing_read_service=_unused_service("billing service"),
                admin_bootstrap_service=_unused_service("bootstrap service"),
                admin_dashboard_service=_unused_service("dashboard service"),
                admin_dictionary_action_service=_unused_service("dictionary action service"),
                admin_dictionary_read_service=_unused_service("dictionary read service"),
                admin_dictionary_service=_unused_service("dictionary service"),
                admin_entity_service=_unused_service("entity service"),
                admin_exercise_text_service=_unused_service("exercise text service"),
                admin_exercise_text_generation_service=lambda: generation_service,
                admin_exercise_text_tts_service=lambda: tts_service,
                admin_import_read_service=_unused_service("import read service"),
                admin_log_read_service=_unused_service("log read service"),
                admin_read_service=_unused_service("read service"),
                admin_settings_service=_unused_service("settings service"),
                admin_user_dictionary_bulk_action=_unused_service("user dictionary bulk action"),
                admin_user_dictionary_promote_action=_unused_service("user dictionary promote action"),
                admin_user_dictionary_read_service=_unused_service("user dictionary read service"),
                admin_user_action_service=_unused_service("user action service"),
                admin_user_read_service=_unused_service("user read service"),
                audio_storage_provider=lambda: audio_storage_provider,
            )
        )
    )
    client = TestClient(app)

    content_response = client.post("/exercise-texts/11/generate-content")
    translations_response = client.post("/exercise-texts/11/generate-translations")
    quiz_response = client.post("/exercise-texts/11/generate-quiz")
    all_response = client.post("/exercise-texts/11/generate-all")
    tts_response = client.post("/exercise-texts/11/generate-tts", json={"voice_code": "voice-1"})
    task_response = client.get("/exercise-texts/11/generation-tasks/51")
    audio_response = client.get("/exercise-texts/11/audio", params={"scope": "paragraph", "paragraph_id": "p1"})

    assert content_response.status_code == 200
    assert translations_response.status_code == 200
    assert quiz_response.status_code == 200
    assert all_response.status_code == 200
    assert tts_response.status_code == 200
    assert task_response.status_code == 200
    assert audio_response.status_code == 200
    assert audio_response.json() == {"audio": audio_path}
    assert audio_response_calls == [
        {"audio_path": audio_path, "storage_provider": audio_storage_provider}
    ]

    assert generation_service.calls == [
        {"action": "start_generation", "actor": actor, "exercise_text_id": 11, "stage": "content"},
        {"action": "start_generation", "actor": actor, "exercise_text_id": 11, "stage": "translations"},
        {"action": "start_generation", "actor": actor, "exercise_text_id": 11, "stage": "quiz"},
        {"action": "generate_all", "actor": actor, "exercise_text_id": 11},
        {"action": "generation_task", "actor": actor, "exercise_text_id": 11, "task_id": 51},
    ]
    assert tts_service.calls == [
        {"action": "start_tts", "actor": actor, "exercise_text_id": 11, "voice_code": "voice-1"},
        {
            "action": "audio",
            "actor": actor,
            "exercise_text_id": 11,
            "scope": "paragraph",
            "paragraph_id": "p1",
        },
    ]


def test_exercise_text_generation_routes_map_service_errors() -> None:
    generation_service = FakeAdminExerciseTextGenerationService(
        error=AdminExerciseTextGenerationNotFoundError("Exercise text not found")
    )
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    app = FastAPI()
    app.include_router(
        build_exercise_texts_router(
            AdminRouterContext(
                current_admin_user=lambda request: actor,
                admin_ai_usage_read_service=_unused_service("ai usage service"),
                admin_auth_service=_unused_service("auth service"),
                admin_billing_read_service=_unused_service("billing service"),
                admin_bootstrap_service=_unused_service("bootstrap service"),
                admin_dashboard_service=_unused_service("dashboard service"),
                admin_dictionary_action_service=_unused_service("dictionary action service"),
                admin_dictionary_read_service=_unused_service("dictionary read service"),
                admin_dictionary_service=_unused_service("dictionary service"),
                admin_entity_service=_unused_service("entity service"),
                admin_exercise_text_service=_unused_service("exercise text service"),
                admin_exercise_text_generation_service=lambda: generation_service,
                admin_exercise_text_tts_service=_unused_service("exercise text tts service"),
                admin_import_read_service=_unused_service("import read service"),
                admin_log_read_service=_unused_service("log read service"),
                admin_read_service=_unused_service("read service"),
                admin_settings_service=_unused_service("settings service"),
                admin_user_dictionary_bulk_action=_unused_service("user dictionary bulk action"),
                admin_user_dictionary_promote_action=_unused_service("user dictionary promote action"),
                admin_user_dictionary_read_service=_unused_service("user dictionary read service"),
                admin_user_action_service=_unused_service("user action service"),
                admin_user_read_service=_unused_service("user read service"),
                audio_storage_provider=_audio_storage_provider,
            )
        )
    )
    client = TestClient(app)

    response = client.post("/exercise-texts/99/generate-content")

    assert response.status_code == 404
    assert response.json() == {"detail": "Exercise text not found"}


def test_exercise_text_tts_routes_map_service_errors() -> None:
    tts_service = FakeAdminExerciseTextTTSService(error=AdminExerciseTextTTSNotFoundError("Exercise text not found"))
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    app = FastAPI()
    app.include_router(
        build_exercise_texts_router(
            AdminRouterContext(
                current_admin_user=lambda request: actor,
                admin_ai_usage_read_service=_unused_service("ai usage service"),
                admin_auth_service=_unused_service("auth service"),
                admin_billing_read_service=_unused_service("billing service"),
                admin_bootstrap_service=_unused_service("bootstrap service"),
                admin_dashboard_service=_unused_service("dashboard service"),
                admin_dictionary_action_service=_unused_service("dictionary action service"),
                admin_dictionary_read_service=_unused_service("dictionary read service"),
                admin_dictionary_service=_unused_service("dictionary service"),
                admin_entity_service=_unused_service("entity service"),
                admin_exercise_text_service=_unused_service("exercise text service"),
                admin_exercise_text_generation_service=_unused_service("exercise text generation service"),
                admin_exercise_text_tts_service=lambda: tts_service,
                admin_import_read_service=_unused_service("import read service"),
                admin_log_read_service=_unused_service("log read service"),
                admin_read_service=_unused_service("read service"),
                admin_settings_service=_unused_service("settings service"),
                admin_user_dictionary_bulk_action=_unused_service("user dictionary bulk action"),
                admin_user_dictionary_promote_action=_unused_service("user dictionary promote action"),
                admin_user_dictionary_read_service=_unused_service("user dictionary read service"),
                admin_user_action_service=_unused_service("user action service"),
                admin_user_read_service=_unused_service("user read service"),
                audio_storage_provider=_audio_storage_provider,
            )
        )
    )
    client = TestClient(app)

    response = client.post("/exercise-texts/99/generate-tts")

    assert response.status_code == 404
    assert response.json() == {"detail": "Exercise text not found"}
