from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.context import AdminRouterContext
from app.admin_api.logs.router import build_logs_router
from app.application.admin.logs.errors import (
    AdminLogReadAccessDeniedError,
    AdminLogReadNotFoundError,
    AdminLogReadValidationError,
)


class FakeAdminLogReadService:
    def __init__(self) -> None:
        self.login_history_calls = []
        self.task_log_calls = []
        self.task_log_detail_calls = []
        self.error_log_calls = []

    def list_login_history(self, *, actor, params):
        self.login_history_calls.append({"actor": actor, "params": params})
        return {"actor": actor, "params": params, "login_history": []}

    def list_task_logs(self, *, actor, params):
        self.task_log_calls.append({"actor": actor, "params": params})
        return {"actor": actor, "params": params, "task_logs": []}

    def get_task_log_detail(self, *, actor, task_log_id):
        self.task_log_detail_calls.append({"actor": actor, "task_log_id": task_log_id})
        return {"actor": actor, "task_log_id": task_log_id}

    def list_error_logs(self, *, actor, params):
        self.error_log_calls.append({"actor": actor, "params": params})
        return {"actor": actor, "params": params, "error_logs": []}


class MissingTaskLogReadService(FakeAdminLogReadService):
    def get_task_log_detail(self, *, actor, task_log_id):
        self.task_log_detail_calls.append({"actor": actor, "task_log_id": task_log_id})
        raise AdminLogReadNotFoundError("Task log not found")


class InvalidLoginHistoryListReadService(FakeAdminLogReadService):
    def list_login_history(self, *, actor, params):
        self.login_history_calls.append({"actor": actor, "params": params})
        raise AdminLogReadValidationError("result contains unsupported value 'bad'")


class InvalidTaskLogListReadService(FakeAdminLogReadService):
    def list_task_logs(self, *, actor, params):
        self.task_log_calls.append({"actor": actor, "params": params})
        raise AdminLogReadValidationError("scope must be one of: billing, operations")


class DeniedTaskLogDetailReadService(FakeAdminLogReadService):
    def get_task_log_detail(self, *, actor, task_log_id):
        self.task_log_detail_calls.append({"actor": actor, "task_log_id": task_log_id})
        raise AdminLogReadAccessDeniedError("Task log access is not allowed")


class InvalidErrorLogListReadService(FakeAdminLogReadService):
    def list_error_logs(self, *, actor, params):
        self.error_log_calls.append({"actor": actor, "params": params})
        raise AdminLogReadValidationError("level contains unsupported value 'info'")


def build_test_app(log_read_service: FakeAdminLogReadService, actor: dict | None = None) -> FastAPI:
    current_actor = actor or {"telegram_user_id": 1, "acl_group_title": "admin"}
    app = FastAPI()
    app.include_router(
        build_logs_router(
            AdminRouterContext(audio_storage_provider=lambda: object(),
                current_admin_user=lambda request: current_actor,
                admin_ai_usage_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("ai usage service should not be used")
                ),
                admin_auth_service=lambda: (_ for _ in ()).throw(AssertionError("auth service should not be used")),
                admin_billing_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("billing service should not be used")
                ),
                admin_bootstrap_service=lambda: (_ for _ in ()).throw(
                    AssertionError("bootstrap service should not be used")
                ),
                admin_dashboard_service=lambda: (_ for _ in ()).throw(
                    AssertionError("dashboard service should not be used")
                ),
                admin_dictionary_action_service=lambda: (_ for _ in ()).throw(
                    AssertionError("dictionary action service should not be used")
                ),
                admin_dictionary_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("dictionary read service should not be used")
                ),
                admin_dictionary_service=lambda: (_ for _ in ()).throw(
                    AssertionError("dictionary service should not be used")
                ),
                admin_entity_service=lambda: (_ for _ in ()).throw(
                    AssertionError("entity service should not be used")
                ),
                admin_exercise_text_service=lambda: (_ for _ in ()).throw(
                    AssertionError("exercise text service should not be used")
                ),
                admin_exercise_text_generation_service=lambda: (_ for _ in ()).throw(
                    AssertionError("exercise text generation service should not be used")
                ),
                admin_exercise_text_tts_service=lambda: (_ for _ in ()).throw(
                    AssertionError("exercise text tts service should not be used")
                ),
                admin_import_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("import service should not be used")
                ),
                admin_log_read_service=lambda: log_read_service,
                admin_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("read service should not be used")
                ),
                admin_settings_service=lambda: (_ for _ in ()).throw(
                    AssertionError("settings service should not be used")
                ),
                admin_user_dictionary_bulk_action=lambda: (_ for _ in ()).throw(
                    AssertionError("user dictionary bulk action should not be used")
                ),
                admin_user_dictionary_promote_action=lambda: (_ for _ in ()).throw(
                    AssertionError("user dictionary promote action should not be used")
                ),
                admin_user_dictionary_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("user dictionary read service should not be used")
                ),
                admin_user_action_service=lambda: (_ for _ in ()).throw(
                    AssertionError("user action service should not be used")
                ),
                admin_user_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("user read service should not be used")
                ),
            )
        )
    )
    return app


def test_admin_log_routes_use_log_read_service_context_directly() -> None:
    log_read_service = FakeAdminLogReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = TestClient(build_test_app(log_read_service, actor))

    login_history_response = client.get(
        "/login-history",
        params={
            "page": 2,
            "page_size": 100,
            "user_id": "user-1",
            "interface_context": ["admin_web"],
            "result": ["success"],
            "api_origin": "https://admin.cronolex.test",
        },
    )
    task_logs_response = client.get(
        "/task-logs",
        params={
            "page": 3,
            "page_size": 50,
            "search": "import",
            "task_type": ["user_vocabulary_import"],
            "status": ["completed"],
            "user_id": "user-2",
            "import_job_id": 7,
            "scope": "operations",
        },
    )
    task_log_detail_response = client.get("/task-logs/9")
    error_logs_response = client.get(
        "/error-log",
        params={
            "page": 4,
            "page_size": 100,
            "search": "warn",
            "level": ["warn", "debug"],
        },
    )

    assert login_history_response.status_code == 200
    assert login_history_response.json() == {
        "actor": actor,
        "params": {
            "page": 2,
            "page_size": 100,
            "user_id": "user-1",
            "interface_context": ["admin_web"],
            "result": ["success"],
            "api_origin": "https://admin.cronolex.test",
        },
        "login_history": [],
    }
    assert task_logs_response.status_code == 200
    assert task_logs_response.json() == {
        "actor": actor,
        "params": {
            "page": 3,
            "page_size": 50,
            "search": "import",
            "task_type": ["user_vocabulary_import"],
            "status": ["completed"],
            "user_id": "user-2",
            "import_job_id": 7,
            "scope": "operations",
        },
        "task_logs": [],
    }
    assert task_log_detail_response.status_code == 200
    assert task_log_detail_response.json() == {"actor": actor, "task_log_id": 9}
    assert error_logs_response.status_code == 200
    assert error_logs_response.json() == {
        "actor": actor,
        "params": {
            "page": 4,
            "page_size": 100,
            "search": "warn",
            "level": ["warn", "debug"],
        },
        "error_logs": [],
    }
    assert log_read_service.login_history_calls == [
        {
            "actor": actor,
            "params": {
                "page": 2,
                "page_size": 100,
                "user_id": "user-1",
                "interface_context": ["admin_web"],
                "result": ["success"],
                "api_origin": "https://admin.cronolex.test",
            },
        }
    ]
    assert log_read_service.task_log_calls == [
        {
            "actor": actor,
            "params": {
                "page": 3,
                "page_size": 50,
                "search": "import",
                "task_type": ["user_vocabulary_import"],
                "status": ["completed"],
                "user_id": "user-2",
                "import_job_id": 7,
                "scope": "operations",
            },
        }
    ]
    assert log_read_service.task_log_detail_calls == [{"actor": actor, "task_log_id": 9}]
    assert log_read_service.error_log_calls == [
        {
            "actor": actor,
            "params": {
                "page": 4,
                "page_size": 100,
                "search": "warn",
                "level": ["warn", "debug"],
            },
        }
    ]


def test_admin_task_log_detail_translates_service_not_found_error() -> None:
    log_read_service = MissingTaskLogReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = TestClient(build_test_app(log_read_service, actor))

    response = client.get("/task-logs/404")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task log not found"}
    assert log_read_service.task_log_detail_calls == [{"actor": actor, "task_log_id": 404}]


def test_admin_task_log_detail_translates_service_access_denied_error() -> None:
    log_read_service = DeniedTaskLogDetailReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "viewer"}
    client = TestClient(build_test_app(log_read_service, actor))

    response = client.get("/task-logs/9")

    assert response.status_code == 403
    assert response.json() == {"detail": "Task log access is not allowed"}
    assert log_read_service.task_log_detail_calls == [{"actor": actor, "task_log_id": 9}]


def test_admin_log_router_maps_login_history_list_validation_errors() -> None:
    log_read_service = InvalidLoginHistoryListReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = TestClient(build_test_app(log_read_service, actor))

    response = client.get("/login-history", params={"result": ["bad"]})

    assert response.status_code == 400
    assert response.json() == {"detail": "result contains unsupported value 'bad'"}
    assert log_read_service.login_history_calls == [
        {
            "actor": actor,
            "params": {
                "page": 1,
                "page_size": 50,
                "user_id": None,
                "interface_context": None,
                "result": ["bad"],
                "api_origin": "",
            },
        }
    ]


def test_admin_log_router_maps_task_log_list_validation_errors() -> None:
    log_read_service = InvalidTaskLogListReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = TestClient(build_test_app(log_read_service, actor))

    response = client.get("/task-logs", params={"scope": "mixed"})

    assert response.status_code == 400
    assert response.json() == {"detail": "scope must be one of: billing, operations"}
    assert log_read_service.task_log_calls == [
        {
            "actor": actor,
            "params": {
                "page": 1,
                "page_size": 50,
                "search": "",
                "task_type": None,
                "status": None,
                "user_id": None,
                "import_job_id": None,
                "scope": "mixed",
            },
        }
    ]


def test_admin_log_router_maps_error_log_list_validation_errors() -> None:
    log_read_service = InvalidErrorLogListReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = TestClient(build_test_app(log_read_service, actor))

    response = client.get("/error-log", params={"level": ["info"]})

    assert response.status_code == 400
    assert response.json() == {"detail": "level contains unsupported value 'info'"}
    assert log_read_service.error_log_calls == [
        {
            "actor": actor,
            "params": {
                "page": 1,
                "page_size": 50,
                "search": "",
                "level": ["info"],
            },
        }
    ]
