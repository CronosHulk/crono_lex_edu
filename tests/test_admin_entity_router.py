from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.context import AdminRouterContext
from app.admin_api.entity.router import build_entity_router
from app.application.admin.entity.errors import (
    AdminEntityAccessDeniedError,
    AdminEntityConflictError,
    AdminEntityInvalidIdError,
    AdminEntityUnknownError,
)
from app.application.admin.read.errors import AdminReadUnknownEntityError


class FakeAdminReadService:
    def __init__(self) -> None:
        self.filter_metadata_calls: list[dict] = []

    def get_filter_metadata(self, entity_type: str, *, actor: dict, params: dict | None = None) -> dict:
        self.filter_metadata_calls.append({"entity_type": entity_type, "actor": actor, "params": params})
        return {"entity": entity_type, "scope": params["scope"] if params else None}


class UnknownEntityAdminReadService(FakeAdminReadService):
    def get_filter_metadata(self, entity_type: str, *, actor: dict, params: dict | None = None) -> dict:
        self.filter_metadata_calls.append({"entity_type": entity_type, "actor": actor, "params": params})
        raise AdminReadUnknownEntityError()


class FakeAdminEntityService:
    def __init__(self) -> None:
        self.archive_calls: list[dict] = []
        self.delete_calls: list[dict] = []

    def archive_entity(self, *, actor: dict, entity_type: str, entity_id: str) -> dict[str, str]:
        self.archive_calls.append({"actor": actor, "entity_type": entity_type, "entity_id": entity_id})
        return {"status": "archived"}

    def delete_entity(self, *, actor: dict, entity_type: str, entity_id: str) -> dict[str, str]:
        self.delete_calls.append({"actor": actor, "entity_type": entity_type, "entity_id": entity_id})
        return {"status": "deleted"}


class InvalidIdAdminEntityService(FakeAdminEntityService):
    def archive_entity(self, *, actor: dict, entity_type: str, entity_id: str) -> dict[str, str]:
        self.archive_calls.append({"actor": actor, "entity_type": entity_type, "entity_id": entity_id})
        raise AdminEntityInvalidIdError()


class UnknownAdminEntityService(FakeAdminEntityService):
    def delete_entity(self, *, actor: dict, entity_type: str, entity_id: str) -> dict[str, str]:
        self.delete_calls.append({"actor": actor, "entity_type": entity_type, "entity_id": entity_id})
        raise AdminEntityUnknownError()


class ConflictAdminEntityService(FakeAdminEntityService):
    def delete_entity(self, *, actor: dict, entity_type: str, entity_id: str) -> dict[str, str]:
        self.delete_calls.append({"actor": actor, "entity_type": entity_type, "entity_id": entity_id})
        raise AdminEntityConflictError("Dictionary entry is assigned to users and cannot be deleted")


class AccessDeniedAdminEntityService(FakeAdminEntityService):
    def delete_entity(self, *, actor: dict, entity_type: str, entity_id: str) -> dict[str, str]:
        self.delete_calls.append({"actor": actor, "entity_type": entity_type, "entity_id": entity_id})
        raise AdminEntityAccessDeniedError("Delete is not allowed")


def _unused_service(name: str):
    return lambda: (_ for _ in ()).throw(AssertionError(f"{name} should not be used"))


def build_entity_test_client(read_service, entity_service, actor: dict) -> TestClient:
    app = FastAPI()
    app.include_router(
        build_entity_router(
            AdminRouterContext(audio_storage_provider=lambda: object(),
                current_admin_user=lambda request: actor,
                admin_ai_usage_read_service=_unused_service("ai usage service"),
                admin_auth_service=_unused_service("auth service"),
                admin_billing_read_service=_unused_service("billing service"),
                admin_bootstrap_service=_unused_service("bootstrap service"),
                admin_dashboard_service=_unused_service("dashboard service"),
                admin_dictionary_action_service=_unused_service("dictionary action service"),
                admin_dictionary_read_service=_unused_service("dictionary read service"),
                admin_dictionary_service=_unused_service("dictionary service"),
                admin_entity_service=lambda: entity_service,
                admin_exercise_text_service=_unused_service("exercise text service"),
                admin_exercise_text_generation_service=_unused_service("exercise text generation service"),
                admin_exercise_text_tts_service=_unused_service("exercise text tts service"),
                admin_import_read_service=_unused_service("import read service"),
                admin_log_read_service=_unused_service("log read service"),
                admin_read_service=lambda: read_service,
                admin_settings_service=_unused_service("settings service"),
                admin_user_dictionary_bulk_action=_unused_service("user dictionary bulk action"),
                admin_user_dictionary_promote_action=_unused_service("user dictionary promote action"),
                admin_user_dictionary_read_service=_unused_service("user dictionary read service"),
                admin_user_action_service=_unused_service("user action service"),
                admin_user_read_service=_unused_service("user read service"),
            )
        )
    )
    return TestClient(app)


def test_entity_router_routes_use_direct_service_context() -> None:
    read_service = FakeAdminReadService()
    entity_service = FakeAdminEntityService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_entity_test_client(read_service, entity_service, actor)

    filter_response = client.get("/task_logs/filter-metadata", params={"scope": "billing"})
    archive_response = client.post("/users/42/archive")
    delete_response = client.delete("/dictionary/7")

    assert filter_response.status_code == 200
    assert filter_response.json() == {"entity": "task_logs", "scope": "billing"}
    assert archive_response.status_code == 200
    assert archive_response.json() == {"status": "archived"}
    assert delete_response.status_code == 200
    assert delete_response.json() == {"status": "deleted"}
    assert read_service.filter_metadata_calls == [
        {"entity_type": "task_logs", "actor": actor, "params": {"scope": "billing"}}
    ]
    assert entity_service.archive_calls == [{"actor": actor, "entity_type": "users", "entity_id": "42"}]
    assert entity_service.delete_calls == [{"actor": actor, "entity_type": "dictionary", "entity_id": "7"}]


def test_entity_router_maps_admin_read_service_errors() -> None:
    read_service = UnknownEntityAdminReadService()
    entity_service = FakeAdminEntityService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_entity_test_client(read_service, entity_service, actor)

    response = client.get("/unknown/filter-metadata")

    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown entity"}
    assert read_service.filter_metadata_calls == [
        {"entity_type": "unknown", "actor": actor, "params": {"scope": "operations"}}
    ]


def test_entity_router_maps_admin_entity_validation_errors() -> None:
    read_service = FakeAdminReadService()
    entity_service = InvalidIdAdminEntityService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_entity_test_client(read_service, entity_service, actor)

    response = client.post("/dictionary/not-int/archive")

    assert response.status_code == 400
    assert response.json() == {"detail": "entity_id must be an integer"}
    assert entity_service.archive_calls == [{"actor": actor, "entity_type": "dictionary", "entity_id": "not-int"}]


def test_entity_router_maps_admin_entity_not_found_errors() -> None:
    read_service = FakeAdminReadService()
    entity_service = UnknownAdminEntityService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_entity_test_client(read_service, entity_service, actor)

    response = client.delete("/dictionary/7")

    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown entity"}
    assert entity_service.delete_calls == [{"actor": actor, "entity_type": "dictionary", "entity_id": "7"}]


def test_entity_router_maps_admin_entity_conflict_errors() -> None:
    read_service = FakeAdminReadService()
    entity_service = ConflictAdminEntityService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_entity_test_client(read_service, entity_service, actor)

    response = client.delete("/dictionary/7")

    assert response.status_code == 409
    assert response.json() == {"detail": "Dictionary entry is assigned to users and cannot be deleted"}
    assert entity_service.delete_calls == [{"actor": actor, "entity_type": "dictionary", "entity_id": "7"}]


def test_entity_router_maps_admin_entity_access_denied_errors() -> None:
    read_service = FakeAdminReadService()
    entity_service = AccessDeniedAdminEntityService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_entity_test_client(read_service, entity_service, actor)

    response = client.delete("/dictionary/7")

    assert response.status_code == 403
    assert response.json() == {"detail": "Delete is not allowed"}
    assert entity_service.delete_calls == [{"actor": actor, "entity_type": "dictionary", "entity_id": "7"}]
