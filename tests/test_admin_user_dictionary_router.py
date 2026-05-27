from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.admin_api.user_dictionary.router as user_dictionary_router
from app.admin_api.context import AdminRouterContext
from app.admin_api.user_dictionary.router import build_user_dictionary_router
from app.application.admin.user_dictionary.errors import (
    AdminUserDictionaryActionAccessDeniedError,
    AdminUserDictionaryActionNotFoundError,
    AdminUserDictionaryActionValidationError,
    AdminUserDictionaryReadAccessDeniedError,
    AdminUserDictionaryReadAudioNotFoundError,
    AdminUserDictionaryReadEntryNotFoundError,
    AdminUserDictionaryReadLevelIdFilterError,
)
from app.storage.audio import filesystem_audio_storage_provider


class FakeAdminUserDictionaryReadService:
    def __init__(self) -> None:
        self.list_calls = []
        self.audio_calls = []
        self.detail_calls = []

    def list_entries(self, *, actor, params):
        self.list_calls.append({"actor": actor, "params": params})
        return {"actor": actor, "params": params, "entries": []}

    def get_audio_path(self, *, actor, entry_id):
        self.audio_calls.append({"actor": actor, "entry_id": entry_id})
        return f"runtime/user_audio/{entry_id}.mp3"

    def get_entry_detail(self, *, actor, entry_id):
        self.detail_calls.append({"actor": actor, "entry_id": entry_id})
        return {"actor": actor, "entry_id": entry_id, "entry": {"id": entry_id}}


class InvalidListAdminUserDictionaryReadService(FakeAdminUserDictionaryReadService):
    def list_entries(self, *, actor, params):
        self.list_calls.append({"actor": actor, "params": params})
        raise AdminUserDictionaryReadLevelIdFilterError()


class DeniedListAdminUserDictionaryReadService(FakeAdminUserDictionaryReadService):
    def list_entries(self, *, actor, params):
        self.list_calls.append({"actor": actor, "params": params})
        raise AdminUserDictionaryReadAccessDeniedError("User dictionary access is not allowed")


class MissingDetailAdminUserDictionaryReadService(FakeAdminUserDictionaryReadService):
    def get_entry_detail(self, *, actor, entry_id):
        self.detail_calls.append({"actor": actor, "entry_id": entry_id})
        raise AdminUserDictionaryReadEntryNotFoundError()


class MissingAudioAdminUserDictionaryReadService(FakeAdminUserDictionaryReadService):
    def get_audio_path(self, *, actor, entry_id):
        self.audio_calls.append({"actor": actor, "entry_id": entry_id})
        raise AdminUserDictionaryReadAudioNotFoundError()


class FakeAdminUserDictionaryPromoteAction:
    def __init__(self) -> None:
        self.promote_entry_calls = []
        self.promote_entries_calls = []

    def promote_entry(self, *, actor, entry_id):
        self.promote_entry_calls.append({"actor": actor, "entry_id": entry_id})
        return {"actor": actor, "entry_id": entry_id, "promoted": True}

    def promote_entries(self, *, actor, entry_ids):
        self.promote_entries_calls.append({"actor": actor, "entry_ids": entry_ids})
        return {"actor": actor, "entry_ids": entry_ids, "promoted_count": len(entry_ids)}


class InvalidManyAdminUserDictionaryPromoteAction(FakeAdminUserDictionaryPromoteAction):
    def promote_entries(self, *, actor, entry_ids):
        self.promote_entries_calls.append({"actor": actor, "entry_ids": entry_ids})
        raise AdminUserDictionaryActionValidationError("Only ready user dictionary entries can be promoted")


class DeniedOneAdminUserDictionaryPromoteAction(FakeAdminUserDictionaryPromoteAction):
    def promote_entry(self, *, actor, entry_id):
        self.promote_entry_calls.append({"actor": actor, "entry_id": entry_id})
        raise AdminUserDictionaryActionAccessDeniedError("User dictionary promotion is not allowed")


class MissingOneAdminUserDictionaryPromoteAction(FakeAdminUserDictionaryPromoteAction):
    def promote_entry(self, *, actor, entry_id):
        self.promote_entry_calls.append({"actor": actor, "entry_id": entry_id})
        raise AdminUserDictionaryActionNotFoundError("User dictionary entry not found")


class FakeAdminUserDictionaryBulkAction:
    def __init__(self) -> None:
        self.execute_calls = []

    def execute(self, *, actor, action, entry_ids):
        self.execute_calls.append({"actor": actor, "action": action, "entry_ids": entry_ids})
        return {"actor": actor, "action": action, "entry_ids": entry_ids, "updated_count": len(entry_ids)}


class InvalidAdminUserDictionaryBulkAction(FakeAdminUserDictionaryBulkAction):
    def execute(self, *, actor, action, entry_ids):
        self.execute_calls.append({"actor": actor, "action": action, "entry_ids": entry_ids})
        raise AdminUserDictionaryActionValidationError("Only non-rejected entries can be rejected")


def _unused_service(name: str):
    return lambda: (_ for _ in ()).throw(AssertionError(f"{name} should not be used"))


_DEFAULT_AUDIO_STORAGE_PROVIDER = object()


def build_user_dictionary_test_client(
    *,
    read_service,
    promote_action: FakeAdminUserDictionaryPromoteAction | None = None,
    bulk_action: FakeAdminUserDictionaryBulkAction | None = None,
    actor: dict | None = None,
    audio_storage_provider: object = _DEFAULT_AUDIO_STORAGE_PROVIDER,
) -> TestClient:
    actor = actor or {"telegram_user_id": 1, "acl_group_title": "admin"}
    promote_action = promote_action or FakeAdminUserDictionaryPromoteAction()
    bulk_action = bulk_action or FakeAdminUserDictionaryBulkAction()
    if audio_storage_provider is _DEFAULT_AUDIO_STORAGE_PROVIDER:
        audio_storage_provider = filesystem_audio_storage_provider()
    if audio_storage_provider is None:
        raise AssertionError("audio_storage_provider must not be None")
    app = FastAPI()
    app.include_router(
        build_user_dictionary_router(
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
                admin_exercise_text_tts_service=_unused_service("exercise text tts service"),
                admin_import_read_service=_unused_service("import read service"),
                admin_log_read_service=_unused_service("log read service"),
                admin_read_service=_unused_service("read service"),
                admin_settings_service=_unused_service("settings service"),
                admin_user_dictionary_bulk_action=lambda: bulk_action,
                admin_user_dictionary_promote_action=lambda: promote_action,
                admin_user_dictionary_read_service=lambda: read_service,
                admin_user_action_service=_unused_service("user action service"),
                admin_user_read_service=_unused_service("user read service"),
                audio_storage_provider=lambda: audio_storage_provider,
            )
        )
    )
    return TestClient(app)


def test_admin_user_dictionary_routes_use_direct_service_context(monkeypatch) -> None:
    user_dictionary_read_service = FakeAdminUserDictionaryReadService()
    promote_action = FakeAdminUserDictionaryPromoteAction()
    bulk_action = FakeAdminUserDictionaryBulkAction()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    audio_storage_provider = object()
    audio_response_calls = []
    monkeypatch.setattr(
        user_dictionary_router,
        "build_audio_response",
        lambda audio_path, *, storage_provider: audio_response_calls.append(
            {"audio_path": audio_path, "storage_provider": storage_provider}
        )
        or {"audio": audio_path},
    )
    client = build_user_dictionary_test_client(
        read_service=user_dictionary_read_service,
        promote_action=promote_action,
        bulk_action=bulk_action,
        actor=actor,
        audio_storage_provider=audio_storage_provider,
    )

    list_response = client.get(
        "/user-dictionary/entries",
        params={
            "page": 2,
            "page_size": 100,
            "search": "apple",
            "status": ["ready_for_rotation"],
            "part_of_speech": ["noun"],
            "level_id": ["1", "2"],
        },
    )
    audio_response = client.get("/user-dictionary/entries/7/audio")
    detail_response = client.get("/user-dictionary/entries/7")
    promote_many_response = client.post("/user-dictionary/entries/promote", json={"entry_ids": [7, 8]})
    bulk_action_response = client.post(
        "/user-dictionary/entries/bulk-action",
        json={"action": "reject", "entry_ids": [7, 8]},
    )
    promote_one_response = client.post("/user-dictionary/entries/9/promote")

    assert list_response.status_code == 200
    assert list_response.json() == {
        "actor": actor,
        "params": {
            "page": 2,
            "page_size": 100,
            "search": "apple",
            "status": ["ready_for_rotation"],
            "part_of_speech": ["noun"],
            "level_id": ["1", "2"],
        },
        "entries": [],
    }
    assert audio_response.status_code == 200
    assert audio_response.json() == {"audio": "runtime/user_audio/7.mp3"}
    assert audio_response_calls == [
        {"audio_path": "runtime/user_audio/7.mp3", "storage_provider": audio_storage_provider}
    ]
    assert detail_response.status_code == 200
    assert detail_response.json() == {"actor": actor, "entry_id": 7, "entry": {"id": 7}}
    assert promote_many_response.status_code == 200
    assert promote_many_response.json() == {"actor": actor, "entry_ids": [7, 8], "promoted_count": 2}
    assert bulk_action_response.status_code == 200
    assert bulk_action_response.json() == {"actor": actor, "action": "reject", "entry_ids": [7, 8], "updated_count": 2}
    assert promote_one_response.status_code == 200
    assert promote_one_response.json() == {"actor": actor, "entry_id": 9, "promoted": True}
    assert user_dictionary_read_service.list_calls == [
        {
            "actor": actor,
            "params": {
                "page": 2,
                "page_size": 100,
                "search": "apple",
                "status": ["ready_for_rotation"],
                "part_of_speech": ["noun"],
                "level_id": ["1", "2"],
            },
        }
    ]
    assert user_dictionary_read_service.audio_calls == [{"actor": actor, "entry_id": 7}]
    assert user_dictionary_read_service.detail_calls == [{"actor": actor, "entry_id": 7}]
    assert promote_action.promote_entries_calls == [{"actor": actor, "entry_ids": [7, 8]}]
    assert bulk_action.execute_calls == [{"actor": actor, "action": "reject", "entry_ids": [7, 8]}]
    assert promote_action.promote_entry_calls == [{"actor": actor, "entry_id": 9}]


def test_admin_user_dictionary_router_maps_list_validation_errors() -> None:
    user_dictionary_read_service = InvalidListAdminUserDictionaryReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_user_dictionary_test_client(read_service=user_dictionary_read_service, actor=actor)

    response = client.get("/user-dictionary/entries", params={"level_id": ["bad"]})

    assert response.status_code == 422
    assert response.json() == {"detail": "level_id must contain numeric values"}
    assert user_dictionary_read_service.list_calls == [
        {
            "actor": actor,
            "params": {
                "page": 1,
                "page_size": 50,
                "search": "",
                "status": None,
                "part_of_speech": None,
                "level_id": ["bad"],
            },
        }
    ]


def test_admin_user_dictionary_router_maps_read_access_denied_errors() -> None:
    user_dictionary_read_service = DeniedListAdminUserDictionaryReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "student"}
    client = build_user_dictionary_test_client(read_service=user_dictionary_read_service, actor=actor)

    response = client.get("/user-dictionary/entries")

    assert response.status_code == 403
    assert response.json() == {"detail": "User dictionary access is not allowed"}
    assert user_dictionary_read_service.list_calls == [
        {
            "actor": actor,
            "params": {
                "page": 1,
                "page_size": 50,
                "search": "",
                "status": None,
                "part_of_speech": None,
                "level_id": None,
            },
        }
    ]


def test_admin_user_dictionary_router_maps_detail_not_found_errors() -> None:
    user_dictionary_read_service = MissingDetailAdminUserDictionaryReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_user_dictionary_test_client(read_service=user_dictionary_read_service, actor=actor)

    response = client.get("/user-dictionary/entries/404")

    assert response.status_code == 404
    assert response.json() == {"detail": "User dictionary entry was not found"}
    assert user_dictionary_read_service.detail_calls == [{"actor": actor, "entry_id": 404}]


def test_admin_user_dictionary_router_maps_audio_not_found_errors() -> None:
    user_dictionary_read_service = MissingAudioAdminUserDictionaryReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_user_dictionary_test_client(read_service=user_dictionary_read_service, actor=actor)

    response = client.get("/user-dictionary/entries/404/audio")

    assert response.status_code == 404
    assert response.json() == {"detail": "Audio not found"}
    assert user_dictionary_read_service.audio_calls == [{"actor": actor, "entry_id": 404}]


def test_admin_user_dictionary_router_maps_promote_validation_errors() -> None:
    user_dictionary_read_service = FakeAdminUserDictionaryReadService()
    promote_action = InvalidManyAdminUserDictionaryPromoteAction()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_user_dictionary_test_client(
        read_service=user_dictionary_read_service,
        promote_action=promote_action,
        actor=actor,
    )

    response = client.post("/user-dictionary/entries/promote", json={"entry_ids": [5, 6]})

    assert response.status_code == 400
    assert response.json() == {"detail": "Only ready user dictionary entries can be promoted"}
    assert promote_action.promote_entries_calls == [{"actor": actor, "entry_ids": [5, 6]}]


def test_admin_user_dictionary_router_maps_action_access_denied_errors() -> None:
    user_dictionary_read_service = FakeAdminUserDictionaryReadService()
    promote_action = DeniedOneAdminUserDictionaryPromoteAction()
    actor = {"telegram_user_id": 1, "acl_group_title": "student"}
    client = build_user_dictionary_test_client(
        read_service=user_dictionary_read_service,
        promote_action=promote_action,
        actor=actor,
    )

    response = client.post("/user-dictionary/entries/5/promote")

    assert response.status_code == 403
    assert response.json() == {"detail": "User dictionary promotion is not allowed"}
    assert promote_action.promote_entry_calls == [{"actor": actor, "entry_id": 5}]


def test_admin_user_dictionary_router_maps_promote_not_found_errors() -> None:
    user_dictionary_read_service = FakeAdminUserDictionaryReadService()
    promote_action = MissingOneAdminUserDictionaryPromoteAction()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_user_dictionary_test_client(
        read_service=user_dictionary_read_service,
        promote_action=promote_action,
        actor=actor,
    )

    response = client.post("/user-dictionary/entries/404/promote")

    assert response.status_code == 404
    assert response.json() == {"detail": "User dictionary entry not found"}
    assert promote_action.promote_entry_calls == [{"actor": actor, "entry_id": 404}]


def test_admin_user_dictionary_router_maps_bulk_validation_errors() -> None:
    user_dictionary_read_service = FakeAdminUserDictionaryReadService()
    bulk_action = InvalidAdminUserDictionaryBulkAction()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_user_dictionary_test_client(
        read_service=user_dictionary_read_service,
        bulk_action=bulk_action,
        actor=actor,
    )

    response = client.post("/user-dictionary/entries/bulk-action", json={"action": "reject", "entry_ids": [5]})

    assert response.status_code == 400
    assert response.json() == {"detail": "Only non-rejected entries can be rejected"}
    assert bulk_action.execute_calls == [{"actor": actor, "action": "reject", "entry_ids": [5]}]


def test_admin_user_dictionary_router_builds_audio_file_response(tmp_path, monkeypatch) -> None:
    audio_dir = tmp_path / "runtime" / "user_audio"
    audio_dir.mkdir(parents=True)
    audio_file = audio_dir / "7.mp3"
    audio_file.write_bytes(b"mp3")
    monkeypatch.chdir(tmp_path)
    user_dictionary_read_service = FakeAdminUserDictionaryReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_user_dictionary_test_client(read_service=user_dictionary_read_service, actor=actor)

    response = client.get("/user-dictionary/entries/7/audio")

    assert response.status_code == 200
    assert response.content == b"mp3"
    assert response.headers["content-type"] == "audio/mpeg"
    assert user_dictionary_read_service.audio_calls == [{"actor": actor, "entry_id": 7}]
