from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.bootstrap.router import build_bootstrap_router
from app.admin_api.context import AdminRouterContext
from app.application.admin.permissions import AdminPermissionDeniedError


class FakeAdminBootstrapService:
    def __init__(self) -> None:
        self.bootstrap_calls = []

    def bootstrap(self, user):
        self.bootstrap_calls.append({"user": user})
        return {"user": user, "version": "test"}


class FakeDeniedAdminBootstrapService:
    def bootstrap(self, user):
        raise AdminPermissionDeniedError("Access denied")


def test_admin_bootstrap_route_uses_bootstrap_service_context_directly() -> None:
    bootstrap_service = FakeAdminBootstrapService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    app = _build_app(bootstrap_service, actor)

    response = TestClient(app).get("/app/bootstrap")

    assert response.status_code == 200
    assert response.json() == {"user": actor, "version": "test"}
    assert bootstrap_service.bootstrap_calls == [{"user": actor}]


def test_admin_bootstrap_route_maps_permission_denied_to_http_403() -> None:
    actor = {"telegram_user_id": 2, "acl_group_title": "student"}
    app = _build_app(FakeDeniedAdminBootstrapService(), actor)

    response = TestClient(app).get("/app/bootstrap")

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied"}


def _build_app(bootstrap_service, actor) -> FastAPI:
    app = FastAPI()
    app.include_router(
        build_bootstrap_router(
            AdminRouterContext(audio_storage_provider=lambda: object(),
                current_admin_user=lambda request: actor,
                admin_ai_usage_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("ai usage service should not be used")
                ),
                admin_auth_service=lambda: (_ for _ in ()).throw(AssertionError("auth service should not be used")),
                admin_billing_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("billing service should not be used")
                ),
                admin_bootstrap_service=lambda: bootstrap_service,
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
                    AssertionError("import read service should not be used")
                ),
                admin_log_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("log read service should not be used")
                ),
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
