from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.ai_usage.router import build_ai_usage_router
from app.admin_api.context import AdminRouterContext
from app.application.admin.ai_usage.errors import (
    AdminAIUsageReadAccessDeniedError,
    AdminAIUsageReadTooManyAttemptsError,
    AdminAIUsageReadUnauthorizedError,
    AdminAIUsageReadValidationError,
)


class FakeAdminAIUsageReadService:
    def __init__(self) -> None:
        self.summary_calls = []
        self.session_calls = []
        self.delete_calls = []

    def summarize(self, *, actor, period):
        self.summary_calls.append({"actor": actor, "period": period})
        return {"actor": actor, "period": period, "summary": {}}

    def list_sessions(self, *, actor, params):
        self.session_calls.append({"actor": actor, "params": params})
        return {"actor": actor, "params": params, "items": []}

    def delete_all_sessions_with_otp(self, *, actor, challenge_id, otp):
        self.delete_calls.append({"actor": actor, "challenge_id": challenge_id, "otp": otp})
        return {"actor": actor, "challenge_id": challenge_id, "otp": otp, "status": "ok"}


class InvalidSummaryAIUsageReadService(FakeAdminAIUsageReadService):
    def summarize(self, *, actor, period):
        self.summary_calls.append({"actor": actor, "period": period})
        raise AdminAIUsageReadValidationError("period must be one of: all, day, month, week")


class InvalidSessionsAIUsageReadService(FakeAdminAIUsageReadService):
    def list_sessions(self, *, actor, params):
        self.session_calls.append({"actor": actor, "params": params})
        raise AdminAIUsageReadValidationError("provider_key values must match pattern")


class AccessDeniedDeleteAIUsageReadService(FakeAdminAIUsageReadService):
    def delete_all_sessions_with_otp(self, *, actor, challenge_id, otp):
        self.delete_calls.append({"actor": actor, "challenge_id": challenge_id, "otp": otp})
        raise AdminAIUsageReadAccessDeniedError("Access denied")


class UnauthorizedDeleteAIUsageReadService(FakeAdminAIUsageReadService):
    def delete_all_sessions_with_otp(self, *, actor, challenge_id, otp):
        self.delete_calls.append({"actor": actor, "challenge_id": challenge_id, "otp": otp})
        raise AdminAIUsageReadUnauthorizedError("Invalid OTP")


class TooManyAttemptsDeleteAIUsageReadService(FakeAdminAIUsageReadService):
    def delete_all_sessions_with_otp(self, *, actor, challenge_id, otp):
        self.delete_calls.append({"actor": actor, "challenge_id": challenge_id, "otp": otp})
        raise AdminAIUsageReadTooManyAttemptsError("Too many attempts")


def build_ai_usage_test_client(ai_usage_service, actor) -> TestClient:
    app = FastAPI()
    app.include_router(
        build_ai_usage_router(
            AdminRouterContext(audio_storage_provider=lambda: object(),
                current_admin_user=lambda request: actor,
                admin_ai_usage_read_service=lambda: ai_usage_service,
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
    return TestClient(app)


def test_admin_ai_usage_routes_use_ai_usage_service_context_directly() -> None:
    ai_usage_service = FakeAdminAIUsageReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_ai_usage_test_client(ai_usage_service, actor)

    summary_response = client.get("/ai-usage/summary?period=month")
    sessions_response = client.get(
        "/ai-usage/sessions",
        params={
            "page": 2,
            "page_size": 100,
            "period": "all",
            "search": "tts",
            "task_scope": ["import", "tts"],
            "task_key": ["generate"],
            "provider_key": ["openai"],
            "model": ["gpt-test"],
            "user_id": "42",
        },
    )
    delete_response = client.request(
        "DELETE",
        "/ai-usage/sessions",
        json={"challenge_id": 12, "otp": "123456"},
    )

    assert summary_response.status_code == 200
    assert summary_response.json() == {"actor": actor, "period": "month", "summary": {}}
    assert sessions_response.status_code == 200
    assert sessions_response.json() == {
        "actor": actor,
        "params": {
            "page": 2,
            "page_size": 100,
            "period": "all",
            "search": "tts",
            "task_scope": ["import", "tts"],
            "task_key": ["generate"],
            "provider_key": ["openai"],
            "model": ["gpt-test"],
            "actor_user_id": "42",
        },
        "items": [],
    }
    assert delete_response.status_code == 200
    assert delete_response.json() == {"actor": actor, "challenge_id": 12, "otp": "123456", "status": "ok"}
    assert ai_usage_service.summary_calls == [{"actor": actor, "period": "month"}]
    assert ai_usage_service.session_calls == [
        {
            "actor": actor,
            "params": {
                "page": 2,
                "page_size": 100,
                "period": "all",
                "search": "tts",
                "task_scope": ["import", "tts"],
                "task_key": ["generate"],
                "provider_key": ["openai"],
                "model": ["gpt-test"],
                "actor_user_id": "42",
            },
        }
    ]
    assert ai_usage_service.delete_calls == [{"actor": actor, "challenge_id": 12, "otp": "123456"}]


def test_admin_ai_usage_router_maps_summary_validation_errors() -> None:
    ai_usage_service = InvalidSummaryAIUsageReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_ai_usage_test_client(ai_usage_service, actor)

    response = client.get("/ai-usage/summary?period=decade")

    assert response.status_code == 400
    assert response.json() == {"detail": "period must be one of: all, day, month, week"}
    assert ai_usage_service.summary_calls == [{"actor": actor, "period": "decade"}]


def test_admin_ai_usage_router_maps_session_list_validation_errors() -> None:
    ai_usage_service = InvalidSessionsAIUsageReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_ai_usage_test_client(ai_usage_service, actor)

    response = client.get("/ai-usage/sessions", params={"provider_key": ["bad value"]})

    assert response.status_code == 400
    assert response.json() == {"detail": "provider_key values must match pattern"}
    assert ai_usage_service.session_calls == [
        {
            "actor": actor,
            "params": {
                "page": 1,
                "page_size": 50,
                "period": "week",
                "search": "",
                "task_scope": None,
                "task_key": None,
                "provider_key": ["bad value"],
                "model": None,
                "actor_user_id": None,
            },
        }
    ]


def test_admin_ai_usage_router_maps_delete_access_denied_errors() -> None:
    ai_usage_service = AccessDeniedDeleteAIUsageReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_ai_usage_test_client(ai_usage_service, actor)

    response = client.request(
        "DELETE",
        "/ai-usage/sessions",
        json={"challenge_id": 12, "otp": "123456"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied"}
    assert ai_usage_service.delete_calls == [{"actor": actor, "challenge_id": 12, "otp": "123456"}]


def test_admin_ai_usage_router_maps_delete_unauthorized_errors() -> None:
    ai_usage_service = UnauthorizedDeleteAIUsageReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_ai_usage_test_client(ai_usage_service, actor)

    response = client.request(
        "DELETE",
        "/ai-usage/sessions",
        json={"challenge_id": 12, "otp": "123456"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid OTP"}
    assert ai_usage_service.delete_calls == [{"actor": actor, "challenge_id": 12, "otp": "123456"}]


def test_admin_ai_usage_router_maps_delete_too_many_attempts_errors() -> None:
    ai_usage_service = TooManyAttemptsDeleteAIUsageReadService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_ai_usage_test_client(ai_usage_service, actor)

    response = client.request(
        "DELETE",
        "/ai-usage/sessions",
        json={"challenge_id": 12, "otp": "123456"},
    )

    assert response.status_code == 429
    assert response.json() == {"detail": "Too many attempts"}
    assert ai_usage_service.delete_calls == [{"actor": actor, "challenge_id": 12, "otp": "123456"}]
