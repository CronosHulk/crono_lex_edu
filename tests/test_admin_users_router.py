from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.context import AdminRouterContext
from app.admin_api.users.router import build_users_router
from app.application.admin.read.errors import AdminReadAccessDeniedError
from app.application.admin.users.errors import (
    AdminUserActionAccessDeniedError,
    AdminUserActionForbiddenError,
    AdminUserActionNotFoundError,
    AdminUserActionValidationError,
    AdminUserReadAccessDeniedError,
    AdminUserReadNotFoundError,
    AdminUserReadValidationError,
)


class FakeAdminUserReadService:
    def __init__(self) -> None:
        self.list_calls: list[dict] = []
        self.detail_calls: list[dict] = []
        self.login_history_calls: list[dict] = []

    def list_users(self, *, actor: dict, params: dict) -> dict:
        self.list_calls.append({"actor": actor, "params": params})
        return {"items": [{"user_id": "user-1"}], "page": params["page"], "page_size": params["page_size"]}

    def get_user_detail(self, *, actor: dict, user_id: str) -> dict:
        self.detail_calls.append({"actor": actor, "user_id": user_id})
        return {"user": {"user_id": user_id}}

    def list_latest_login_history_for_user(self, *, actor: dict, user_id: str, limit: int = 10) -> dict:
        self.login_history_calls.append({"actor": actor, "user_id": user_id, "limit": limit})
        return {"items": [{"user_id": user_id, "limit": limit}]}


class InvalidUserFilterReadService(FakeAdminUserReadService):
    def list_users(self, *, actor: dict, params: dict) -> dict:
        self.list_calls.append({"actor": actor, "params": params})
        raise AdminUserReadValidationError("user_id must be a valid UUID")


class MissingUserReadService(FakeAdminUserReadService):
    def get_user_detail(self, *, actor: dict, user_id: str) -> dict:
        self.detail_calls.append({"actor": actor, "user_id": user_id})
        raise AdminUserReadNotFoundError()


class AccessDeniedLoginHistoryReadService(FakeAdminUserReadService):
    def list_latest_login_history_for_user(self, *, actor: dict, user_id: str, limit: int = 10) -> dict:
        self.login_history_calls.append({"actor": actor, "user_id": user_id, "limit": limit})
        raise AdminUserReadAccessDeniedError("Login history is not allowed")


class FakeAdminReadService:
    def __init__(self) -> None:
        self.filter_metadata_calls: list[dict] = []

    def get_filter_metadata(self, entity_type: str, *, actor: dict, params: dict | None = None) -> dict:
        self.filter_metadata_calls.append({"entity_type": entity_type, "actor": actor, "params": params})
        return {"entity": entity_type}


class AccessDeniedAdminReadService(FakeAdminReadService):
    def get_filter_metadata(self, entity_type: str, *, actor: dict, params: dict | None = None) -> dict:
        self.filter_metadata_calls.append({"entity_type": entity_type, "actor": actor, "params": params})
        raise AdminReadAccessDeniedError("Access denied")


class FakeAdminUserActionService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def set_role(self, *, actor: dict, target_user_id: str, role: str) -> dict:
        self.calls.append({"action": "set_role", "actor": actor, "target_user_id": target_user_id, "role": role})
        return {"status": "ok", "role": role}

    def set_learning_role(self, *, actor: dict, target_user_id: str, learning_role: str) -> dict:
        self.calls.append(
            {
                "action": "set_learning_role",
                "actor": actor,
                "target_user_id": target_user_id,
                "learning_role": learning_role,
            }
        )
        return {"status": "ok", "learning_role": learning_role}

    def set_subscription(self, *, actor: dict, target_user_id: str, plan_key: str) -> dict:
        self.calls.append(
            {"action": "set_subscription", "actor": actor, "target_user_id": target_user_id, "plan_key": plan_key}
        )
        return {"status": "ok", "plan_key": plan_key}

    def set_subscription_trial(self, *, actor: dict, target_user_id: str, is_trial_enabled: bool) -> dict:
        self.calls.append(
            {
                "action": "set_subscription_trial",
                "actor": actor,
                "target_user_id": target_user_id,
                "is_trial_enabled": is_trial_enabled,
            }
        )
        return {"status": "ok", "is_trial_enabled": is_trial_enabled}

    def reset_password(self, *, actor: dict, user_id: str) -> dict:
        self.calls.append({"action": "reset_password", "actor": actor, "user_id": user_id})
        return {"status": "ok", "user_id": user_id}


class InvalidAdminUserActionService(FakeAdminUserActionService):
    def set_role(self, *, actor: dict, target_user_id: str, role: str) -> dict:
        self.calls.append({"action": "set_role", "actor": actor, "target_user_id": target_user_id, "role": role})
        raise AdminUserActionValidationError("You cannot change your own role")


class ForbiddenAdminUserActionService(FakeAdminUserActionService):
    def set_learning_role(self, *, actor: dict, target_user_id: str, learning_role: str) -> dict:
        self.calls.append(
            {
                "action": "set_learning_role",
                "actor": actor,
                "target_user_id": target_user_id,
                "learning_role": learning_role,
            }
        )
        raise AdminUserActionForbiddenError("Learning role change is not allowed")


class AccessDeniedAdminUserActionService(FakeAdminUserActionService):
    def set_subscription(self, *, actor: dict, target_user_id: str, plan_key: str) -> dict:
        self.calls.append(
            {"action": "set_subscription", "actor": actor, "target_user_id": target_user_id, "plan_key": plan_key}
        )
        raise AdminUserActionAccessDeniedError("Subscription change is not allowed")


class MissingAdminUserActionService(FakeAdminUserActionService):
    def reset_password(self, *, actor: dict, user_id: str) -> dict:
        self.calls.append({"action": "reset_password", "actor": actor, "user_id": user_id})
        raise AdminUserActionNotFoundError("User not found")


def _unused_service(name: str):
    return lambda: (_ for _ in ()).throw(AssertionError(f"{name} should not be used"))


def build_users_test_client(
    *,
    user_read_service,
    read_service,
    user_action_service,
    actor: dict,
) -> TestClient:
    app = FastAPI()
    app.include_router(
        build_users_router(
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
                admin_entity_service=_unused_service("entity service"),
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
                admin_user_action_service=lambda: user_action_service,
                admin_user_read_service=lambda: user_read_service,
            )
        )
    )
    return TestClient(app)


def test_users_router_routes_use_direct_service_context() -> None:
    user_read_service = FakeAdminUserReadService()
    read_service = FakeAdminReadService()
    user_action_service = FakeAdminUserActionService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_users_test_client(
        user_read_service=user_read_service,
        read_service=read_service,
        user_action_service=user_action_service,
        actor=actor,
    )

    list_response = client.get(
        "/users",
        params=[
            ("page", "2"),
            ("page_size", "100"),
            ("archived", "true"),
            ("search", "ana"),
            ("user_type", "teacher"),
            ("user_id", "user-1"),
            ("role", "admin"),
            ("status", "active"),
        ],
    )
    filter_response = client.get("/users/filter-metadata")
    detail_response = client.get("/users/user-1")
    login_history_response = client.get("/users/user-1/login-history", params={"limit": "3"})
    role_response = client.post("/users/user-1/roles", json={"role": "admin"})
    learning_role_response = client.post("/users/user-1/learning-role", json={"learning_role": "teacher"})
    subscription_response = client.post("/users/user-1/subscription", json={"plan_key": "free"})
    trial_response = client.post("/users/user-1/subscription-trial", json={"is_trial_enabled": True})
    password_reset_response = client.post("/users/user-1/password-reset")

    assert list_response.status_code == 200
    assert list_response.json()["items"] == [{"user_id": "user-1"}]
    assert filter_response.status_code == 200
    assert filter_response.json() == {"entity": "users"}
    assert detail_response.status_code == 200
    assert detail_response.json() == {"user": {"user_id": "user-1"}}
    assert login_history_response.status_code == 200
    assert login_history_response.json() == {"items": [{"user_id": "user-1", "limit": 3}]}
    assert role_response.status_code == 200
    assert learning_role_response.status_code == 200
    assert subscription_response.status_code == 200
    assert trial_response.status_code == 200
    assert password_reset_response.status_code == 200

    assert user_read_service.list_calls == [
        {
            "actor": actor,
            "params": {
                "page": 2,
                "page_size": 100,
                "archived": "true",
                "search": "ana",
                "user_type": "teacher",
                "user_id": "user-1",
                "role": ["admin"],
                "status": ["active"],
            },
        }
    ]
    assert read_service.filter_metadata_calls == [{"entity_type": "users", "actor": actor, "params": None}]
    assert user_read_service.detail_calls == [{"actor": actor, "user_id": "user-1"}]
    assert user_read_service.login_history_calls == [{"actor": actor, "user_id": "user-1", "limit": 3}]
    assert user_action_service.calls == [
        {"action": "set_role", "actor": actor, "target_user_id": "user-1", "role": "admin"},
        {
            "action": "set_learning_role",
            "actor": actor,
            "target_user_id": "user-1",
            "learning_role": "teacher",
        },
        {"action": "set_subscription", "actor": actor, "target_user_id": "user-1", "plan_key": "free"},
        {
            "action": "set_subscription_trial",
            "actor": actor,
            "target_user_id": "user-1",
            "is_trial_enabled": True,
        },
        {"action": "reset_password", "actor": actor, "user_id": "user-1"},
    ]


def test_users_router_maps_user_read_list_errors() -> None:
    user_read_service = InvalidUserFilterReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_users_test_client(
        user_read_service=user_read_service,
        read_service=FakeAdminReadService(),
        user_action_service=FakeAdminUserActionService(),
        actor=actor,
    )

    response = client.get("/users", params={"user_id": "not-a-uuid"})

    assert response.status_code == 400
    assert response.json() == {"detail": "user_id must be a valid UUID"}
    assert user_read_service.list_calls == [
        {
            "actor": actor,
            "params": {
                "page": 1,
                "page_size": 50,
                "archived": "false",
                "search": "",
                "user_type": "student",
                "user_id": "not-a-uuid",
                "role": None,
                "status": None,
            },
        }
    ]


def test_users_router_maps_filter_metadata_read_access_denied_errors() -> None:
    read_service = AccessDeniedAdminReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "student"}
    client = build_users_test_client(
        user_read_service=FakeAdminUserReadService(),
        read_service=read_service,
        user_action_service=FakeAdminUserActionService(),
        actor=actor,
    )

    response = client.get("/users/filter-metadata")

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied"}
    assert read_service.filter_metadata_calls == [{"entity_type": "users", "actor": actor, "params": None}]


def test_users_router_maps_user_read_detail_errors() -> None:
    user_read_service = MissingUserReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_users_test_client(
        user_read_service=user_read_service,
        read_service=FakeAdminReadService(),
        user_action_service=FakeAdminUserActionService(),
        actor=actor,
    )

    response = client.get("/users/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
    assert user_read_service.detail_calls == [{"actor": actor, "user_id": "missing"}]


def test_users_router_maps_login_history_read_access_denied_errors() -> None:
    user_read_service = AccessDeniedLoginHistoryReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "student"}
    client = build_users_test_client(
        user_read_service=user_read_service,
        read_service=FakeAdminReadService(),
        user_action_service=FakeAdminUserActionService(),
        actor=actor,
    )

    response = client.get("/users/user-1/login-history", params={"limit": "3"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Login history is not allowed"}
    assert user_read_service.login_history_calls == [{"actor": actor, "user_id": "user-1", "limit": 3}]


def test_users_router_maps_user_action_validation_errors() -> None:
    user_action_service = InvalidAdminUserActionService()
    actor = {"telegram_user_id": 1, "acl_group_title": "super_admin"}
    client = build_users_test_client(
        user_read_service=FakeAdminUserReadService(),
        read_service=FakeAdminReadService(),
        user_action_service=user_action_service,
        actor=actor,
    )

    response = client.post("/users/user-1/roles", json={"role": "admin"})

    assert response.status_code == 400
    assert response.json() == {"detail": "You cannot change your own role"}
    assert user_action_service.calls == [
        {"action": "set_role", "actor": actor, "target_user_id": "user-1", "role": "admin"}
    ]


def test_users_router_maps_user_action_forbidden_errors() -> None:
    user_action_service = ForbiddenAdminUserActionService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_users_test_client(
        user_read_service=FakeAdminUserReadService(),
        read_service=FakeAdminReadService(),
        user_action_service=user_action_service,
        actor=actor,
    )

    response = client.post("/users/user-1/learning-role", json={"learning_role": "teacher"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Learning role change is not allowed"}
    assert user_action_service.calls == [
        {
            "action": "set_learning_role",
            "actor": actor,
            "target_user_id": "user-1",
            "learning_role": "teacher",
        }
    ]


def test_users_router_maps_user_action_access_denied_errors() -> None:
    user_action_service = AccessDeniedAdminUserActionService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_users_test_client(
        user_read_service=FakeAdminUserReadService(),
        read_service=FakeAdminReadService(),
        user_action_service=user_action_service,
        actor=actor,
    )

    response = client.post("/users/user-1/subscription", json={"plan_key": "premium"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Subscription change is not allowed"}
    assert user_action_service.calls == [
        {"action": "set_subscription", "actor": actor, "target_user_id": "user-1", "plan_key": "premium"}
    ]


def test_users_router_maps_user_action_not_found_errors() -> None:
    user_action_service = MissingAdminUserActionService()
    actor = {"telegram_user_id": 1, "acl_group_title": "super_admin"}
    client = build_users_test_client(
        user_read_service=FakeAdminUserReadService(),
        read_service=FakeAdminReadService(),
        user_action_service=user_action_service,
        actor=actor,
    )

    response = client.post("/users/missing/password-reset")

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
    assert user_action_service.calls == [{"action": "reset_password", "actor": actor, "user_id": "missing"}]
