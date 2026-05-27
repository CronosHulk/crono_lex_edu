from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.context import AdminRouterContext
from app.admin_api.imports.router import build_imports_router
from app.application.admin.imports.errors import (
    AdminImportReadAccessDeniedError,
    AdminImportReadNotFoundError,
    AdminImportReadValidationError,
)


class FakeAdminImportReadService:
    def __init__(self) -> None:
        self.job_list_calls = []
        self.item_list_calls = []
        self.detail_calls = []

    def list_import_jobs(self, *, actor, params):
        self.job_list_calls.append({"actor": actor, "params": params})
        return {"actor": actor, "params": params, "jobs": []}

    def list_import_items(self, *, actor, params):
        self.item_list_calls.append({"actor": actor, "params": params})
        return {"actor": actor, "params": params, "items": []}

    def get_import_job_detail(self, *, actor, import_job_id):
        self.detail_calls.append({"actor": actor, "import_job_id": import_job_id})
        return {"actor": actor, "import_job_id": import_job_id}


class MissingImportJobReadService(FakeAdminImportReadService):
    def get_import_job_detail(self, *, actor, import_job_id):
        self.detail_calls.append({"actor": actor, "import_job_id": import_job_id})
        raise AdminImportReadNotFoundError()


class InvalidImportJobListReadService(FakeAdminImportReadService):
    def list_import_jobs(self, *, actor, params):
        self.job_list_calls.append({"actor": actor, "params": params})
        raise AdminImportReadValidationError("status contains unsupported value 'unknown'")


class AccessDeniedImportJobListReadService(FakeAdminImportReadService):
    def list_import_jobs(self, *, actor, params):
        self.job_list_calls.append({"actor": actor, "params": params})
        raise AdminImportReadAccessDeniedError("Import jobs access is not allowed")


def build_imports_test_client(import_read_service, actor) -> TestClient:
    app = FastAPI()
    app.include_router(
        build_imports_router(
            AdminRouterContext(audio_storage_provider=lambda: object(),
                current_admin_user=lambda request: actor,
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
                admin_entity_service=lambda: (_ for _ in ()).throw(AssertionError("entity service should not be used")),
                admin_exercise_text_service=lambda: (_ for _ in ()).throw(
                    AssertionError("exercise text service should not be used")
                ),
                admin_exercise_text_generation_service=lambda: (_ for _ in ()).throw(
                    AssertionError("exercise text generation service should not be used")
                ),
                admin_exercise_text_tts_service=lambda: (_ for _ in ()).throw(
                    AssertionError("exercise text tts service should not be used")
                ),
                admin_import_read_service=lambda: import_read_service,
                admin_log_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("log read service should not be used")
                ),
                admin_read_service=lambda: (_ for _ in ()).throw(AssertionError("read service should not be used")),
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
    return TestClient(app)


def test_admin_import_routes_use_import_read_service_context_directly() -> None:
    import_read_service = FakeAdminImportReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_imports_test_client(import_read_service, actor)

    jobs_response = client.get(
        "/import-jobs",
        params={
            "page": 2,
            "page_size": 100,
            "search": "deck",
            "status": ["queued", "completed"],
            "source_type": ["telegram"],
            "user_id": "user-1",
        },
    )
    items_response = client.get(
        "/import-items",
        params={
            "page": 3,
            "page_size": 50,
            "search": "apple",
            "status": ["imported"],
            "import_job_id": 7,
            "user_id": "user-2",
        },
    )
    detail_response = client.get("/import-jobs/9")

    assert jobs_response.status_code == 200
    assert jobs_response.json() == {
        "actor": actor,
        "params": {
            "page": 2,
            "page_size": 100,
            "search": "deck",
            "status": ["queued", "completed"],
            "source_type": ["telegram"],
            "user_id": "user-1",
        },
        "jobs": [],
    }
    assert items_response.status_code == 200
    assert items_response.json() == {
        "actor": actor,
        "params": {
            "page": 3,
            "page_size": 50,
            "search": "apple",
            "status": ["imported"],
            "import_job_id": 7,
            "user_id": "user-2",
        },
        "items": [],
    }
    assert detail_response.status_code == 200
    assert detail_response.json() == {"actor": actor, "import_job_id": 9}
    assert import_read_service.job_list_calls == [
        {
            "actor": actor,
            "params": {
                "page": 2,
                "page_size": 100,
                "search": "deck",
                "status": ["queued", "completed"],
                "source_type": ["telegram"],
                "user_id": "user-1",
            },
        }
    ]
    assert import_read_service.item_list_calls == [
        {
            "actor": actor,
            "params": {
                "page": 3,
                "page_size": 50,
                "search": "apple",
                "status": ["imported"],
                "import_job_id": 7,
                "user_id": "user-2",
            },
        }
    ]
    assert import_read_service.detail_calls == [{"actor": actor, "import_job_id": 9}]


def test_admin_import_router_maps_import_read_service_errors() -> None:
    import_read_service = MissingImportJobReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_imports_test_client(import_read_service, actor)

    response = client.get("/import-jobs/404")

    assert response.status_code == 404
    assert response.json() == {"detail": "Import job not found"}
    assert import_read_service.detail_calls == [{"actor": actor, "import_job_id": 404}]


def test_admin_import_router_maps_list_validation_errors() -> None:
    import_read_service = InvalidImportJobListReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_imports_test_client(import_read_service, actor)

    response = client.get("/import-jobs", params={"status": ["unknown"]})

    assert response.status_code == 400
    assert response.json() == {"detail": "status contains unsupported value 'unknown'"}
    assert import_read_service.job_list_calls == [
        {
            "actor": actor,
            "params": {
                "page": 1,
                "page_size": 50,
                "search": "",
                "status": ["unknown"],
                "source_type": None,
                "user_id": None,
            },
        }
    ]


def test_admin_import_router_maps_list_access_denied_errors() -> None:
    import_read_service = AccessDeniedImportJobListReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_imports_test_client(import_read_service, actor)

    response = client.get("/import-jobs", params={"status": ["queued"]})

    assert response.status_code == 403
    assert response.json() == {"detail": "Import jobs access is not allowed"}
    assert import_read_service.job_list_calls == [
        {
            "actor": actor,
            "params": {
                "page": 1,
                "page_size": 50,
                "search": "",
                "status": ["queued"],
                "source_type": None,
                "user_id": None,
            },
        }
    ]
