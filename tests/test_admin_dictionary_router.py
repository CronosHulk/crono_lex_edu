from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.admin_api.dictionary.router as dictionary_router
from app.admin_api.context import AdminRouterContext
from app.admin_api.dictionary.router import build_dictionary_router
from app.application.admin.dictionary.errors import (
    AdminDictionaryActionAccessDeniedError,
    AdminDictionaryReadAccessDeniedError,
    AdminDictionaryReadEntryNotFoundError,
    AdminDictionaryReadVerifiedFilterError,
    AdminDictionaryServiceAccessDeniedError,
    AdminDictionaryServiceAudioNotFoundError,
    AdminDictionaryServiceEntryNotFoundError,
    AdminDictionaryServiceValidationError,
)
from app.storage.audio import filesystem_audio_storage_provider


class FakeAdminDictionaryReadService:
    def __init__(self) -> None:
        self.list_calls: list[dict] = []
        self.detail_calls: list[dict] = []

    def list_dictionary_entries(self, *, actor: dict, params: dict) -> dict:
        self.list_calls.append({"actor": actor, "params": params})
        return {"items": [{"id": 7, "word": "harbor"}], "page": params["page"], "page_size": params["page_size"]}

    def get_dictionary_entry(self, *, actor: dict, entry_id: int) -> dict:
        self.detail_calls.append({"actor": actor, "entry_id": entry_id})
        return {"id": entry_id, "word": "harbor"}


class InvalidVerifiedAdminDictionaryReadService(FakeAdminDictionaryReadService):
    def list_dictionary_entries(self, *, actor: dict, params: dict) -> dict:
        self.list_calls.append({"actor": actor, "params": params})
        raise AdminDictionaryReadVerifiedFilterError()


class MissingEntryAdminDictionaryReadService(FakeAdminDictionaryReadService):
    def get_dictionary_entry(self, *, actor: dict, entry_id: int) -> dict:
        self.detail_calls.append({"actor": actor, "entry_id": entry_id})
        raise AdminDictionaryReadEntryNotFoundError()


class DeniedAdminDictionaryReadService(FakeAdminDictionaryReadService):
    def list_dictionary_entries(self, *, actor: dict, params: dict) -> dict:
        self.list_calls.append({"actor": actor, "params": params})
        raise AdminDictionaryReadAccessDeniedError("Access denied")


class FakeAdminDictionaryActionService:
    def __init__(self) -> None:
        self.verify_calls: list[dict] = []

    def verify_entries(self, *, actor: dict, entry_ids: list[int]) -> dict:
        self.verify_calls.append({"actor": actor, "entry_ids": entry_ids})
        return {"status": "ok", "verified_count": len(entry_ids)}


class FakeAdminDictionaryService:
    def __init__(self) -> None:
        self.update_calls: list[dict] = []
        self.audio_calls: list[dict] = []

    def update_dictionary_entry(self, *, actor: dict, entry_id: int, payload: dict) -> dict:
        self.update_calls.append({"actor": actor, "entry_id": entry_id, "payload": payload})
        return {"id": entry_id, **payload}

    def get_audio_path(self, *, actor: dict, entry_id: int) -> str:
        self.audio_calls.append({"actor": actor, "entry_id": entry_id})
        return f"runtime/audio/{entry_id}.mp3"


class InvalidUpdateAdminDictionaryService(FakeAdminDictionaryService):
    def update_dictionary_entry(self, *, actor: dict, entry_id: int, payload: dict) -> dict:
        self.update_calls.append({"actor": actor, "entry_id": entry_id, "payload": payload})
        raise AdminDictionaryServiceValidationError("translation_uk is required")


class MissingUpdateAdminDictionaryService(FakeAdminDictionaryService):
    def update_dictionary_entry(self, *, actor: dict, entry_id: int, payload: dict) -> dict:
        self.update_calls.append({"actor": actor, "entry_id": entry_id, "payload": payload})
        raise AdminDictionaryServiceEntryNotFoundError()


class MissingAudioAdminDictionaryService(FakeAdminDictionaryService):
    def get_audio_path(self, *, actor: dict, entry_id: int) -> str:
        self.audio_calls.append({"actor": actor, "entry_id": entry_id})
        raise AdminDictionaryServiceAudioNotFoundError()


class DeniedUpdateAdminDictionaryService(FakeAdminDictionaryService):
    def update_dictionary_entry(self, *, actor: dict, entry_id: int, payload: dict) -> dict:
        self.update_calls.append({"actor": actor, "entry_id": entry_id, "payload": payload})
        raise AdminDictionaryServiceAccessDeniedError("Access denied")


class DeniedVerifyAdminDictionaryActionService(FakeAdminDictionaryActionService):
    def verify_entries(self, *, actor: dict, entry_ids: list[int]) -> dict:
        self.verify_calls.append({"actor": actor, "entry_ids": entry_ids})
        raise AdminDictionaryActionAccessDeniedError("Access denied")


def _unused_service(name: str):
    return lambda: (_ for _ in ()).throw(AssertionError(f"{name} should not be used"))


_DEFAULT_AUDIO_STORAGE_PROVIDER = object()


def build_dictionary_test_client(
    *,
    read_service,
    action_service: FakeAdminDictionaryActionService | None = None,
    dictionary_service: FakeAdminDictionaryService | None = None,
    actor: dict | None = None,
    audio_storage_provider: object = _DEFAULT_AUDIO_STORAGE_PROVIDER,
) -> TestClient:
    actor = actor or {"telegram_user_id": 1, "acl_group_title": "admin"}
    action_service = action_service or FakeAdminDictionaryActionService()
    dictionary_service = dictionary_service or FakeAdminDictionaryService()
    if audio_storage_provider is _DEFAULT_AUDIO_STORAGE_PROVIDER:
        audio_storage_provider = filesystem_audio_storage_provider()
    if audio_storage_provider is None:
        raise AssertionError("audio_storage_provider must not be None")
    app = FastAPI()
    app.include_router(
        build_dictionary_router(
            AdminRouterContext(
                current_admin_user=lambda request: actor,
                admin_ai_usage_read_service=_unused_service("ai usage service"),
                admin_auth_service=_unused_service("auth service"),
                admin_billing_read_service=_unused_service("billing service"),
                admin_bootstrap_service=_unused_service("bootstrap service"),
                admin_dashboard_service=_unused_service("dashboard service"),
                admin_dictionary_action_service=lambda: action_service,
                admin_dictionary_read_service=lambda: read_service,
                admin_dictionary_service=lambda: dictionary_service,
                admin_entity_service=_unused_service("entity service"),
                admin_exercise_text_service=_unused_service("exercise text service"),
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
                audio_storage_provider=lambda: audio_storage_provider,
            )
        )
    )
    return TestClient(app)


def test_dictionary_router_routes_use_direct_service_context(monkeypatch) -> None:
    read_service = FakeAdminDictionaryReadService()
    action_service = FakeAdminDictionaryActionService()
    dictionary_service = FakeAdminDictionaryService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    audio_storage_provider = object()
    audio_response_calls = []
    monkeypatch.setattr(
        dictionary_router,
        "build_audio_response",
        lambda audio_path, *, storage_provider: audio_response_calls.append(
            {"audio_path": audio_path, "storage_provider": storage_provider}
        )
        or {"audio": audio_path},
    )
    client = build_dictionary_test_client(
        read_service=read_service,
        action_service=action_service,
        dictionary_service=dictionary_service,
        actor=actor,
        audio_storage_provider=audio_storage_provider,
    )

    list_response = client.get(
        "/dictionary/entries",
        params=[
            ("page", "2"),
            ("page_size", "100"),
            ("archived", "true"),
            ("search", "har"),
            ("part_of_speech", "noun"),
            ("category", "core"),
            ("entry_type", "word"),
            ("verified", "verified"),
        ],
    )
    verify_response = client.post("/dictionary/entries/verify", json={"entry_ids": [7, 8]})
    detail_response = client.get("/dictionary/entries/7")
    update_response = client.patch(
        "/dictionary/entries/7",
        json={"word": "harbor", "translation_uk": "harbor uk", "entry_type": "word"},
    )
    audio_response = client.get("/dictionary/entries/7/audio")

    assert list_response.status_code == 200
    assert list_response.json()["items"] == [{"id": 7, "word": "harbor"}]
    assert verify_response.status_code == 200
    assert verify_response.json() == {"status": "ok", "verified_count": 2}
    assert detail_response.status_code == 200
    assert detail_response.json() == {"id": 7, "word": "harbor"}
    assert update_response.status_code == 200
    assert update_response.json() == {"id": 7, "word": "harbor", "translation_uk": "harbor uk", "entry_type": "word"}
    assert audio_response.status_code == 200
    assert audio_response.json() == {"audio": "runtime/audio/7.mp3"}
    assert audio_response_calls == [
        {"audio_path": "runtime/audio/7.mp3", "storage_provider": audio_storage_provider}
    ]

    assert read_service.list_calls == [
        {
            "actor": actor,
            "params": {
                "page": 2,
                "page_size": 100,
                "archived": "true",
                "search": "har",
                "part_of_speech": ["noun"],
                "category": ["core"],
                "entry_type": ["word"],
                "verified": "verified",
            },
        }
    ]
    assert action_service.verify_calls == [{"actor": actor, "entry_ids": [7, 8]}]
    assert read_service.detail_calls == [{"actor": actor, "entry_id": 7}]
    assert dictionary_service.update_calls == [
        {
            "actor": actor,
            "entry_id": 7,
            "payload": {"word": "harbor", "translation_uk": "harbor uk", "entry_type": "word"},
        }
    ]
    assert dictionary_service.audio_calls == [{"actor": actor, "entry_id": 7}]


def test_dictionary_router_maps_read_validation_errors() -> None:
    read_service = InvalidVerifiedAdminDictionaryReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_dictionary_test_client(read_service=read_service, actor=actor)

    response = client.get("/dictionary/entries", params={"verified": "invalid"})

    assert response.status_code == 422
    assert response.json() == {"detail": "verified must be one of: all, verified, unverified"}
    assert read_service.list_calls == [
        {
            "actor": actor,
            "params": {
                "page": 1,
                "page_size": 50,
                "archived": "false",
                "search": "",
                "part_of_speech": None,
                "category": None,
                "entry_type": None,
                "verified": "invalid",
            },
        }
    ]


def test_dictionary_router_maps_read_not_found_errors() -> None:
    read_service = MissingEntryAdminDictionaryReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_dictionary_test_client(read_service=read_service, actor=actor)

    response = client.get("/dictionary/entries/404")

    assert response.status_code == 404
    assert response.json() == {"detail": "Dictionary entry not found"}
    assert read_service.detail_calls == [{"actor": actor, "entry_id": 404}]


def test_dictionary_router_maps_read_access_denied_errors() -> None:
    read_service = DeniedAdminDictionaryReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "student"}
    client = build_dictionary_test_client(read_service=read_service, actor=actor)

    response = client.get("/dictionary/entries")

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied"}


def test_dictionary_router_maps_update_validation_errors() -> None:
    read_service = FakeAdminDictionaryReadService()
    dictionary_service = InvalidUpdateAdminDictionaryService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_dictionary_test_client(read_service=read_service, dictionary_service=dictionary_service, actor=actor)

    response = client.patch("/dictionary/entries/7", json={"word": "harbor", "translation_uk": " "})

    assert response.status_code == 400
    assert response.json() == {"detail": "translation_uk is required"}
    assert dictionary_service.update_calls == [
        {
            "actor": actor,
            "entry_id": 7,
            "payload": {"word": "harbor", "translation_uk": " "},
        }
    ]


def test_dictionary_router_maps_update_not_found_errors() -> None:
    read_service = FakeAdminDictionaryReadService()
    dictionary_service = MissingUpdateAdminDictionaryService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_dictionary_test_client(read_service=read_service, dictionary_service=dictionary_service, actor=actor)

    response = client.patch("/dictionary/entries/404", json={"word": "harbor"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Dictionary entry not found"}
    assert dictionary_service.update_calls == [{"actor": actor, "entry_id": 404, "payload": {"word": "harbor"}}]


def test_dictionary_router_maps_service_access_denied_errors() -> None:
    read_service = FakeAdminDictionaryReadService()
    dictionary_service = DeniedUpdateAdminDictionaryService()
    actor = {"telegram_user_id": 1, "acl_group_title": "student"}
    client = build_dictionary_test_client(read_service=read_service, dictionary_service=dictionary_service, actor=actor)

    response = client.patch("/dictionary/entries/7", json={"word": "harbor"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied"}
    assert dictionary_service.update_calls == [{"actor": actor, "entry_id": 7, "payload": {"word": "harbor"}}]


def test_dictionary_router_maps_action_verify_access_denied_errors() -> None:
    read_service = FakeAdminDictionaryReadService()
    action_service = DeniedVerifyAdminDictionaryActionService()
    actor = {"telegram_user_id": 1, "acl_group_title": "student"}
    client = build_dictionary_test_client(read_service=read_service, action_service=action_service, actor=actor)

    response = client.post("/dictionary/entries/verify", json={"entry_ids": [7]})

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied"}
    assert action_service.verify_calls == [{"actor": actor, "entry_ids": [7]}]


def test_dictionary_router_maps_audio_not_found_errors() -> None:
    read_service = FakeAdminDictionaryReadService()
    dictionary_service = MissingAudioAdminDictionaryService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_dictionary_test_client(read_service=read_service, dictionary_service=dictionary_service, actor=actor)

    response = client.get("/dictionary/entries/404/audio")

    assert response.status_code == 404
    assert response.json() == {"detail": "Audio not found"}
    assert dictionary_service.audio_calls == [{"actor": actor, "entry_id": 404}]


def test_dictionary_router_builds_audio_file_response(tmp_path, monkeypatch) -> None:
    audio_dir = tmp_path / "runtime" / "audio"
    audio_dir.mkdir(parents=True)
    audio_file = audio_dir / "7.mp3"
    audio_file.write_bytes(b"mp3")
    monkeypatch.chdir(tmp_path)
    read_service = FakeAdminDictionaryReadService()
    dictionary_service = FakeAdminDictionaryService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_dictionary_test_client(read_service=read_service, dictionary_service=dictionary_service, actor=actor)

    response = client.get("/dictionary/entries/7/audio")

    assert response.status_code == 200
    assert response.content == b"mp3"
    assert response.headers["content-type"] == "audio/mpeg"
    assert dictionary_service.audio_calls == [{"actor": actor, "entry_id": 7}]
