from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.admin_api.auth.constants import ADMIN_COOKIE_NAME
from app.api import build_api_router
from app.contracts import (
    ActionRequest,
    BillingNotificationDeliveryResultRequest,
    BootstrapRequest,
    BotMessageCleanupResultRequest,
    BotMessageListRequest,
    BotMessageListResponse,
    BotMessageLookupRequest,
    BotMessageTrackRequest,
    BotMessageTrackResponse,
    ButtonModel,
    ImportDispatchResponse,
    MenuRestoreRequest,
    ReminderScreenModel,
    ScreenModel,
    TelegramUserContext,
    TextRequest,
)


class FakeImportNotificationService:
    def process_due_import_notifications(self):
        return [
            {
                "telegram_user_id": 1,
                "chat_id": 99,
                "screen": ScreenModel(screen_id="import_words:summary", text="done"),
            },
            {
                "telegram_user_id": 2,
                "chat_id": 100,
                "screen": ScreenModel(screen_id="admin:restore", text="restore"),
            },
        ]


class FakeSubscriptionMaintenanceRuntimeService:
    def __init__(self) -> None:
        self.calls = 0

    def process_due_subscription_maintenance(self) -> dict[str, object]:
        self.calls += 1
        return {
            "paid_expiration": {
                "processed_users_count": 1,
                "downgraded_to_free_count": 1,
            },
            "trial_expiration": {
                "processed_users_count": 2,
                "trial_closed_count": 2,
            },
            "task_log_id": 77,
        }


class FakeBillingNotificationService:
    def __init__(self) -> None:
        self.bot_notification_results: list[dict[str, object]] = []
        self.receipt_delivery_results: list[dict[str, object]] = []
        self.receipt_admin_alert_results: list[dict[str, object]] = []

    def save_bot_notification_delivery_result(
        self,
        notification_id: int,
        *,
        is_sent: bool,
        error_text: str | None,
    ) -> None:
        self.bot_notification_results.append(
            {"notification_id": notification_id, "is_sent": is_sent, "error_text": error_text}
        )

    def save_receipt_delivery_result(
        self,
        receipt_id: int,
        *,
        is_sent: bool,
        error_text: str | None,
    ) -> None:
        self.receipt_delivery_results.append(
            {"receipt_id": receipt_id, "is_sent": is_sent, "error_text": error_text}
        )

    def save_receipt_admin_alert_result(
        self,
        receipt_id: int,
        *,
        is_sent: bool,
        error_text: str | None,
    ) -> None:
        self.receipt_admin_alert_results.append(
            {"receipt_id": receipt_id, "is_sent": is_sent, "error_text": error_text}
        )


class FakeBillingWebhookService:
    def handle_monobank_webhook(self, **kwargs):
        return {"ok": True, "request_url": kwargs["request_url"]}


class FakeAdminAuthService:
    def __init__(self) -> None:
        self.session_lookups: list[str | None] = []

    def get_session_user(self, session_token, *, request_context):
        _ = request_context
        self.session_lookups.append(session_token)
        return {"telegram_user_id": 1, "acl_group_title": "super_admin"}


class FakeAdminBootstrapService:
    def __init__(self) -> None:
        self.users: list[dict[str, object]] = []

    def bootstrap(self, user):
        self.users.append(dict(user))
        return {"version": "test-admin", "user": user}


class FakeClientRuntimeBootstrapService:
    def __init__(self) -> None:
        self.bootstrap_calls: list[dict[str, object]] = []
        self.restored_menu_user_id: int | None = None
        self.unexpected_error_screen_users: list[int] = []
        self.unexpected_error_logs: list[dict[str, object]] = []

    def bootstrap(self, user, message_text):
        self.bootstrap_calls.append({"telegram_user_id": user.telegram_user_id, "message_text": message_text})
        return ScreenModel(
            screen_id="menu",
            text=f"bootstrap:{user.telegram_user_id}:{message_text}",
            buttons=[ButtonModel(action="m:menu", text="Меню")],
        )

    def build_main_menu_restore_screen(self, telegram_user_id):
        self.restored_menu_user_id = telegram_user_id
        return ScreenModel(screen_id="menu", text="restore")

    def build_unexpected_error_screen(self, user):
        self.unexpected_error_screen_users.append(user.telegram_user_id)
        return ScreenModel(
            screen_id="transient:error",
            text="runtime непередбачена ситуація",
            metadata={
                "force_resend": True,
                "auto_advance_after_ms": 5000,
                "next_action": "m:menu",
            },
        )

    def log_unexpected_error(self, *, route, user, error, details):
        self.unexpected_error_logs.append(
            {
                "route": route,
                "telegram_user_id": user.telegram_user_id,
                "error_type": type(error).__name__,
                "error_text": str(error),
                "details": details,
            }
        )


class FakeClientRuntimeInputService:
    def __init__(self) -> None:
        self.action_calls: list[dict[str, object]] = []
        self.text_input_calls: list[dict[str, object]] = []

    def handle_action(self, user, action):
        self.action_calls.append({"telegram_user_id": user.telegram_user_id, "action": action})
        return ScreenModel(
            screen_id="runtime-action",
            text=f"runtime-action:{user.telegram_user_id}:{action}",
        )

    def handle_text_input(self, user, text):
        self.text_input_calls.append({"telegram_user_id": user.telegram_user_id, "text": text})
        return ScreenModel(
            screen_id="runtime-text",
            text=f"runtime-text:{user.telegram_user_id}:{text}",
        )


class FakeService:
    def __init__(self) -> None:
        self.logged_errors: list[tuple[str, str]] = []
        self.db = SimpleNamespace(settings=SimpleNamespace(app_internal_api_token="internal-token"))
        self.client_runtime_bootstrap_service = FakeClientRuntimeBootstrapService()
        self.client_runtime_input_service = FakeClientRuntimeInputService()
        self.client_runtime_bot_message_service = FakeBotMessageRuntimeService()
        self.client_runtime_reminder_service = RuntimeReminderDispatchService()
        self.client_import_notification_service = FakeImportNotificationService()
        self.subscription_maintenance_runtime_service = FakeSubscriptionMaintenanceRuntimeService()
        self.billing_notification_service = FakeBillingNotificationService()
        self.billing_webhook_service = FakeBillingWebhookService()

    def bootstrap(self, user, message_text):
        raise AssertionError("Client router should use client runtime bootstrap service")

    def build_main_menu_restore_screen(self, telegram_user_id):
        raise AssertionError("Client router should use client runtime bootstrap service")

    def handle_action(self, user, action):
        raise AssertionError("Client router should use client runtime input service")

    def handle_text_input(self, user, text):
        raise AssertionError("Client router should use client runtime input service")

    def log_unexpected_error(self, **kwargs):
        raise AssertionError("Client router should use client runtime bootstrap service")

    def dispatch_due_reminders(self):
        raise AssertionError("Client router should use client runtime reminder service")

    def track_bot_message(self, telegram_user_id, chat_id, message_id, screen_id, delete_after_hours=None):
        raise AssertionError("Client router should use client runtime bot-message service")

    def get_bot_message_log(self, telegram_user_id, chat_id, message_id):
        raise AssertionError("Client router should use client runtime bot-message service")

    def list_active_bot_messages(self, telegram_user_id, chat_id):
        raise AssertionError("Client router should use client runtime bot-message service")

    def dispatch_due_bot_message_cleanup(self):
        raise AssertionError("Client router should use client runtime bot-message service")

    def save_bot_message_cleanup_result(self, message_log_id, is_deleted, error_text=None):
        raise AssertionError("Client router should use client runtime bot-message service")

    def log_error(self, level, text):
        raise AssertionError("Client router should use client runtime bootstrap service")


class FakeBotMessageRuntimeService:
    def __init__(self) -> None:
        self.tracked_message = None
        self.lookup_message = None
        self.list_active_messages = None
        self.cleanup_calls = 0
        self.cleanup_result = None

    def track_bot_message(
        self,
        telegram_user_id,
        chat_id,
        message_id,
        screen_id,
        delete_after_hours=None,
    ):
        self.tracked_message = (telegram_user_id, chat_id, message_id, screen_id, delete_after_hours)
        return {
            "id": 701,
            "telegram_user_id": telegram_user_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "screen_id": screen_id,
        }

    def get_bot_message_log(self, telegram_user_id, chat_id, message_id):
        self.lookup_message = (telegram_user_id, chat_id, message_id)
        if message_id == 999:
            return None
        return {
            "id": 702,
            "telegram_user_id": telegram_user_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "screen_id": "reminder:1",
        }

    def list_active_bot_messages(self, telegram_user_id, chat_id):
        self.list_active_messages = (telegram_user_id, chat_id)
        return [
            {
                "id": 702,
                "telegram_user_id": telegram_user_id,
                "chat_id": chat_id,
                "message_id": 501,
                "screen_id": "menu",
            }
        ]

    def dispatch_due_bot_message_cleanup(self):
        self.cleanup_calls += 1
        return [
            {
                "id": 77,
                "telegram_user_id": 1,
                "chat_id": 99,
                "message_id": 501,
                "screen_id": "menu",
            }
        ]

    def save_bot_message_cleanup_result(self, message_log_id, is_deleted, error_text=None):
        self.cleanup_result = (message_log_id, is_deleted, error_text)


class FailingBotMessageCleanupService:
    def dispatch_due_bot_message_cleanup(self):
        raise AssertionError("raw bot-message service bypassed runtime cleanup dispatch")


class RuntimeBotMessageCleanupService:
    def __init__(self) -> None:
        self.cleanup_calls = 0

    def dispatch_due_bot_message_cleanup(self):
        self.cleanup_calls += 1
        return [
            {
                "id": 78,
                "telegram_user_id": 1,
                "chat_id": 99,
                "message_id": 502,
                "screen_id": "menu",
            }
        ]


class FailingReminderDispatchService:
    def dispatch_due_reminders(self):
        raise AssertionError("raw reminder service bypassed runtime dispatch")


class RuntimeReminderDispatchService:
    def __init__(self) -> None:
        self.dispatch_calls = 0

    def dispatch_due_reminders(self):
        self.dispatch_calls += 1
        return [
            ReminderScreenModel(
                telegram_user_id=1,
                chat_id=99,
                screen=ScreenModel(screen_id="reminder:701", text="time"),
            )
        ]


def get_route_endpoint(path: str, method: str, service: FakeService | None = None):
    router = build_api_router(service or FakeService())
    for route in router.routes:
        if getattr(route, "path", None) == f"/api/v1{path}" and method in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError(f"Route {method} {path} not found")


def test_api_router_preserves_admin_and_client_paths() -> None:
    router = build_api_router(FakeService())
    route_keys = {
        (method, route.path)
        for route in router.routes
        for method in getattr(route, "methods", set())
    }

    expected_routes = {
        ("GET", "/api/v1/health"),
        ("POST", "/api/v1/admin/auth/start"),
        ("POST", "/api/v1/admin/auth/verify-otp"),
        ("POST", "/api/v1/admin/auth/magic"),
        ("POST", "/api/v1/admin/auth/set-password"),
        ("POST", "/api/v1/admin/auth/logout"),
        ("GET", "/api/v1/admin/auth/me"),
        ("GET", "/api/v1/admin/app/bootstrap"),
        ("GET", "/api/v1/admin/{entity_type}/filter-metadata"),
        ("GET", "/api/v1/admin/dictionary/entries"),
        ("GET", "/api/v1/admin/dictionary/entries/{entry_id}"),
        ("PATCH", "/api/v1/admin/dictionary/entries/{entry_id}"),
        ("GET", "/api/v1/admin/exercise-texts"),
        ("POST", "/api/v1/admin/exercise-texts"),
        ("GET", "/api/v1/admin/exercise-texts/{exercise_text_id}"),
        ("PUT", "/api/v1/admin/exercise-texts/{exercise_text_id}"),
        ("DELETE", "/api/v1/admin/exercise-texts/{exercise_text_id}"),
        ("POST", "/api/v1/admin/exercise-texts/{exercise_text_id}/archive"),
        ("POST", "/api/v1/admin/exercise-texts/{exercise_text_id}/ready"),
        ("POST", "/api/v1/admin/exercise-texts/{exercise_text_id}/generate-content"),
        ("POST", "/api/v1/admin/exercise-texts/{exercise_text_id}/generate-translations"),
        ("POST", "/api/v1/admin/exercise-texts/{exercise_text_id}/generate-quiz"),
        ("POST", "/api/v1/admin/exercise-texts/{exercise_text_id}/generate-all"),
        ("POST", "/api/v1/admin/exercise-texts/{exercise_text_id}/generate-tts"),
        ("GET", "/api/v1/admin/exercise-texts/{exercise_text_id}/generation-tasks/{task_id}"),
        ("POST", "/api/v1/admin/exercise-texts/{exercise_text_id}/publish"),
        ("POST", "/api/v1/admin/exercise-texts/{exercise_text_id}/unpublish"),
        ("GET", "/api/v1/admin/exercise-texts/{exercise_text_id}/audio"),
        ("GET", "/api/v1/admin/reference/exercise-text-options"),
        ("GET", "/api/v1/admin/reference/grammar-topics"),
        ("GET", "/api/v1/admin/reference/tts-voices"),
        ("GET", "/api/v1/admin/users"),
        ("GET", "/api/v1/admin/users/filter-metadata"),
        ("GET", "/api/v1/admin/users/{user_id}"),
        ("GET", "/api/v1/admin/users/{user_id}/login-history"),
        ("GET", "/api/v1/admin/login-history"),
        ("GET", "/api/v1/admin/task-logs"),
        ("GET", "/api/v1/admin/task-logs/{task_log_id}"),
        ("GET", "/api/v1/admin/billing/payments"),
        ("GET", "/api/v1/admin/billing/payments/{payment_id}"),
        ("GET", "/api/v1/admin/billing/monobank-audit"),
        ("GET", "/api/v1/admin/billing/monobank-audit/{audit_log_id}"),
        ("GET", "/api/v1/admin/import-jobs"),
        ("GET", "/api/v1/admin/import-items"),
        ("GET", "/api/v1/admin/error-log"),
        ("GET", "/api/v1/admin/import-jobs/{import_job_id}"),
        ("DELETE", "/api/v1/admin/settings/import-data"),
        ("POST", "/api/v1/admin/users/{user_id}/roles"),
        ("POST", "/api/v1/admin/users/{user_id}/password-reset"),
        ("POST", "/api/v1/admin/{entity_type}/{entity_id}/archive"),
        ("DELETE", "/api/v1/admin/{entity_type}/{entity_id}"),
        ("GET", "/api/v1/admin/dictionary/entries/{entry_id}/audio"),
        ("POST", "/api/v1/bootstrap"),
        ("POST", "/api/v1/action"),
        ("POST", "/api/v1/text"),
        ("POST", "/api/v1/reminders/dispatch"),
        ("POST", "/api/v1/bot/messages/track"),
        ("POST", "/api/v1/bot/messages/lookup"),
        ("POST", "/api/v1/bot/messages/active"),
        ("POST", "/api/v1/bot/messages/cleanup/dispatch"),
        ("POST", "/api/v1/imports/process"),
        ("POST", "/api/v1/billing/monobank/webhook"),
        ("POST", "/api/v1/bot/messages/{message_log_id}/cleanup-result"),
    }

    assert expected_routes <= route_keys


def test_admin_users_filter_metadata_route_precedes_user_detail_route() -> None:
    router = build_api_router(FakeService())
    paths = [
        route.path
        for route in router.routes
        if "GET" in getattr(route, "methods", set())
    ]

    assert paths.index("/api/v1/admin/users/filter-metadata") < paths.index("/api/v1/admin/users/{user_id}")


def test_admin_settings_import_data_delete_route_precedes_generic_entity_delete_route() -> None:
    router = build_api_router(FakeService())
    paths = [
        route.path
        for route in router.routes
        if "DELETE" in getattr(route, "methods", set())
    ]

    assert paths.index("/api/v1/admin/settings/import-data") < paths.index("/api/v1/admin/{entity_type}/{entity_id}")


def test_api_router_admin_routes_use_prewired_admin_dependencies() -> None:
    service = FakeService()
    admin_auth_service = FakeAdminAuthService()
    admin_bootstrap_service = FakeAdminBootstrapService()
    service.admin_service_dependencies = SimpleNamespace(
        admin_auth_service=admin_auth_service,
        admin_bootstrap_service=admin_bootstrap_service,
    )
    app = FastAPI()
    app.include_router(build_api_router(service))
    client = TestClient(app)
    client.cookies.set(ADMIN_COOKIE_NAME, "session-token")

    response = client.get("/api/v1/admin/app/bootstrap")

    assert response.status_code == 200
    assert response.json()["version"] == "test-admin"
    assert admin_auth_service.session_lookups == ["session-token"]
    assert admin_bootstrap_service.users == [
        {"telegram_user_id": 1, "acl_group_title": "super_admin"}
    ]


def test_healthcheck_route_returns_ok() -> None:
    endpoint = get_route_endpoint("/health", "GET")

    assert endpoint() == {"status": "ok"}


def test_client_router_requires_internal_token() -> None:
    app = FastAPI()
    app.include_router(build_api_router(FakeService()))
    payload = {
        "user": {"telegram_user_id": 1, "raw_telegram_json": "{}"},
        "message_text": "/start",
    }

    response = TestClient(app).post("/api/v1/bootstrap", json=payload)

    assert response.status_code == 401


def test_client_router_rejects_when_internal_token_is_not_configured() -> None:
    service = FakeService()
    service.db.settings.app_internal_api_token = ""
    app = FastAPI()
    app.include_router(build_api_router(service))
    payload = {
        "user": {"telegram_user_id": 1, "raw_telegram_json": "{}"},
        "message_text": "/start",
    }

    response = TestClient(app).post("/api/v1/bootstrap", json=payload, headers={"X-CronoLex-Internal-Token": "x"})

    assert response.status_code == 503


def test_client_router_accepts_internal_token() -> None:
    app = FastAPI()
    app.include_router(build_api_router(FakeService()))
    payload = {
        "user": {"telegram_user_id": 1, "raw_telegram_json": "{}"},
        "message_text": "/start",
    }

    response = TestClient(app).post(
        "/api/v1/bootstrap",
        json=payload,
        headers={"X-CronoLex-Internal-Token": "internal-token"},
    )

    assert response.status_code == 200
    assert response.json()["screen"]["screen_id"] == "menu"


def test_video_pipeline_route_is_not_connected_to_backend_api() -> None:
    app = FastAPI()
    app.include_router(build_api_router(FakeService()))
    client = TestClient(app)

    missing_response = client.post(
        "/internal/video/exercise-package",
        headers={"X-CronoLex-Internal-Token": "internal-token"},
        json={"learner_id": "learner_a2", "words_count": 5, "locale": "uk", "include_formats": ["word_intro"]},
    )
    ok_response = client.post(
        "/api/v1/internal/video/exercise-package",
        headers={"X-CronoLex-Internal-Token": "internal-token"},
        json={"learner_id": "learner_a2", "words_count": 5, "locale": "uk", "include_formats": ["word_intro"]},
    )

    assert missing_response.status_code == 404
    assert ok_response.status_code == 404


def test_bootstrap_route_returns_screen() -> None:
    service = FakeService()
    endpoint = get_route_endpoint("/bootstrap", "POST", service)

    response = endpoint(
        BootstrapRequest(
            user=TelegramUserContext(telegram_user_id=1, raw_telegram_json="{}"),
            message_text="/start",
        )
    )

    assert response.screen.screen_id == "menu"
    assert response.screen.buttons[0].action == "m:menu"
    assert service.client_runtime_bootstrap_service.bootstrap_calls == [
        {"telegram_user_id": 1, "message_text": "/start"}
    ]


def test_restore_menu_route_returns_screen() -> None:
    service = FakeService()
    endpoint = get_route_endpoint("/menu/restore", "POST", service)

    response = endpoint(MenuRestoreRequest(telegram_user_id=7))

    assert response.screen.screen_id == "menu"
    assert response.screen.text == "restore"
    assert service.client_runtime_bootstrap_service.restored_menu_user_id == 7


def test_action_route_returns_screen() -> None:
    service = FakeService()
    endpoint = get_route_endpoint("/action", "POST", service)

    response = endpoint(
        ActionRequest(
            user=TelegramUserContext(telegram_user_id=1, raw_telegram_json="{}"),
            action="m:menu",
        )
    )

    assert response.screen.screen_id == "runtime-action"
    assert response.screen.text == "runtime-action:1:m:menu"
    assert service.client_runtime_input_service.action_calls == [
        {"telegram_user_id": 1, "action": "m:menu"}
    ]


def test_text_route_returns_screen() -> None:
    service = FakeService()
    endpoint = get_route_endpoint("/text", "POST", service)

    response = endpoint(
        TextRequest(
            user=TelegramUserContext(telegram_user_id=1, raw_telegram_json="{}"),
            text="Рівень англійської",
        )
    )

    assert response.screen.screen_id == "runtime-text"
    assert response.screen.text == "runtime-text:1:Рівень англійської"
    assert service.client_runtime_input_service.text_input_calls == [
        {"telegram_user_id": 1, "text": "Рівень англійської"}
    ]


def test_reminder_dispatch_route_prefers_runtime_reminder_service() -> None:
    service = FakeService()
    runtime_service = RuntimeReminderDispatchService()
    service.client_reminder_dispatch_service = FailingReminderDispatchService()
    service.client_runtime_reminder_service = runtime_service
    endpoint = get_route_endpoint("/reminders/dispatch", "POST", service)

    response = endpoint()

    assert runtime_service.dispatch_calls == 1
    assert response.reminders[0].chat_id == 99
    assert response.reminders[0].screen.screen_id == "reminder:701"


def test_track_bot_message_route_returns_ok() -> None:
    service = FakeService()
    endpoint = get_route_endpoint("/bot/messages/track", "POST", service)

    response = endpoint(
        BotMessageTrackRequest(
            telegram_user_id=1,
            chat_id=99,
            message_id=501,
            screen_id="menu",
            delete_after_hours=6,
        )
    )

    assert response == BotMessageTrackResponse(
        id=701,
        telegram_user_id=1,
        chat_id=99,
        message_id=501,
        screen_id="menu",
    )
    assert service.client_runtime_bot_message_service.tracked_message == (1, 99, 501, "menu", 6)


def test_cleanup_dispatch_route_returns_due_messages() -> None:
    service = FakeService()
    endpoint = get_route_endpoint("/bot/messages/cleanup/dispatch", "POST", service)

    response = endpoint()

    assert service.client_runtime_bot_message_service.cleanup_calls == 1
    assert response.messages[0].id == 77
    assert response.messages[0].message_id == 501


def test_cleanup_dispatch_route_prefers_runtime_bot_message_service() -> None:
    service = FakeService()
    runtime_service = RuntimeBotMessageCleanupService()
    service.client_bot_message_service = FailingBotMessageCleanupService()
    service.client_runtime_bot_message_service = runtime_service
    endpoint = get_route_endpoint("/bot/messages/cleanup/dispatch", "POST", service)

    response = endpoint()

    assert runtime_service.cleanup_calls == 1
    assert response.messages[0].id == 78
    assert response.messages[0].message_id == 502


def test_subscription_maintenance_route_returns_runtime_summary() -> None:
    service = FakeService()
    endpoint = get_route_endpoint("/subscriptions/maintenance/process", "POST", service)

    response = endpoint()

    assert response.summary == {
        "paid_expiration": {
            "processed_users_count": 1,
            "downgraded_to_free_count": 1,
        },
        "trial_expiration": {
            "processed_users_count": 2,
            "trial_closed_count": 2,
        },
        "task_log_id": 77,
    }
    assert service.subscription_maintenance_runtime_service.calls == 1


def test_lookup_bot_message_route_returns_tracked_row() -> None:
    service = FakeService()
    endpoint = get_route_endpoint("/bot/messages/lookup", "POST", service)

    response = endpoint(
        BotMessageLookupRequest(
            telegram_user_id=1,
            chat_id=99,
            message_id=501,
        )
    )

    assert response == BotMessageTrackResponse(
        id=702,
        telegram_user_id=1,
        chat_id=99,
        message_id=501,
        screen_id="reminder:1",
    )
    assert service.client_runtime_bot_message_service.lookup_message == (1, 99, 501)


def test_lookup_bot_message_route_returns_none_when_missing() -> None:
    service = FakeService()
    endpoint = get_route_endpoint("/bot/messages/lookup", "POST", service)

    response = endpoint(
        BotMessageLookupRequest(
            telegram_user_id=1,
            chat_id=99,
            message_id=999,
        )
    )

    assert response is None


def test_list_active_bot_messages_route_returns_rows() -> None:
    service = FakeService()
    endpoint = get_route_endpoint("/bot/messages/active", "POST", service)

    response = endpoint(
        BotMessageListRequest(
            telegram_user_id=1,
            chat_id=99,
        )
    )

    assert response == BotMessageListResponse(
        messages=[
            {
                "id": 702,
                "telegram_user_id": 1,
                "chat_id": 99,
                "message_id": 501,
                "screen_id": "menu",
            }
        ]
    )
    assert service.client_runtime_bot_message_service.list_active_messages == (1, 99)


def test_cleanup_result_route_returns_ok() -> None:
    service = FakeService()
    endpoint = get_route_endpoint("/bot/messages/{message_log_id}/cleanup-result", "POST", service)
    response = endpoint(
        77,
        BotMessageCleanupResultRequest(is_deleted=False, error_text="message not found"),
    )

    assert response == {"status": "ok"}
    assert service.client_runtime_bot_message_service.cleanup_result == (
        77,
        False,
        "message not found",
    )


def test_billing_delivery_result_routes_delegate_to_billing_notification_service() -> None:
    service = FakeService()

    notification_endpoint = get_route_endpoint(
        "/billing/notifications/{notification_id}/delivery-result",
        "POST",
        service,
    )
    receipt_endpoint = get_route_endpoint(
        "/billing/receipts/{receipt_id}/delivery-result",
        "POST",
        service,
    )
    admin_alert_endpoint = get_route_endpoint(
        "/billing/receipts/{receipt_id}/admin-alert-result",
        "POST",
        service,
    )

    assert notification_endpoint(
        5,
        BillingNotificationDeliveryResultRequest(is_sent=False, error_text="notification failed"),
    ) == {"status": "ok"}
    assert receipt_endpoint(
        6,
        BillingNotificationDeliveryResultRequest(is_sent=True, error_text=None),
    ) == {"status": "ok"}
    assert admin_alert_endpoint(
        7,
        BillingNotificationDeliveryResultRequest(is_sent=False, error_text="alert failed"),
    ) == {"status": "ok"}

    billing_service = service.billing_notification_service
    assert billing_service.bot_notification_results == [
        {"notification_id": 5, "is_sent": False, "error_text": "notification failed"}
    ]
    assert billing_service.receipt_delivery_results == [
        {"receipt_id": 6, "is_sent": True, "error_text": None}
    ]
    assert billing_service.receipt_admin_alert_results == [
        {"receipt_id": 7, "is_sent": False, "error_text": "alert failed"}
    ]


def test_import_dispatch_route_returns_notifications() -> None:
    endpoint = get_route_endpoint("/imports/process", "POST")

    response = endpoint()

    assert response == ImportDispatchResponse(
        notifications=[
            {
                "telegram_user_id": 1,
                "chat_id": 99,
                "screen": ScreenModel(screen_id="import_words:summary", text="done"),
            },
            {
                "telegram_user_id": 2,
                "chat_id": 100,
                "screen": ScreenModel(screen_id="admin:restore", text="restore"),
            },
        ]
    )


def test_action_route_returns_transient_error_screen_when_service_crashes() -> None:
    class BrokenRuntimeInputService(FakeClientRuntimeInputService):
        def handle_action(self, user, action):
            raise RuntimeError("boom")

    service = FakeService()
    service.client_runtime_input_service = BrokenRuntimeInputService()
    endpoint = get_route_endpoint("/action", "POST", service)

    response = endpoint(
        ActionRequest(
            user=TelegramUserContext(telegram_user_id=1, language_code="uk", raw_telegram_json="{}"),
            action="m:s",
        )
    )

    assert response.screen.screen_id == "transient:error"
    assert "непередбачена ситуація" in response.screen.text
    assert response.screen.metadata["force_resend"] is True
    assert response.screen.metadata["auto_advance_after_ms"] == 5000
    assert response.screen.metadata["next_action"] == "m:menu"
    runtime_service = service.client_runtime_bootstrap_service
    assert runtime_service.unexpected_error_screen_users == [1]
    assert len(runtime_service.unexpected_error_logs) == 1
    error_log = runtime_service.unexpected_error_logs[0]
    assert error_log["route"] == "action:m:s"
    assert error_log["telegram_user_id"] == 1
    assert error_log["error_type"] == "RuntimeError"
    assert error_log["error_text"] == "boom"
    assert "RuntimeError: boom" in error_log["details"]
    assert service.logged_errors == []


def test_action_request_rejects_too_long_action() -> None:
    try:
        ActionRequest(user={"telegram_user_id": 1, "raw_telegram_json": "{}"}, action="x" * 257)
    except ValidationError as error:
        assert "String should have at most 256 characters" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValidationError was expected")


def test_bot_message_track_request_rejects_invalid_cleanup_window() -> None:
    try:
        BotMessageTrackRequest(
            telegram_user_id=1,
            chat_id=1,
            message_id=1,
            screen_id="main",
            delete_after_hours=0,
        )
    except ValidationError as error:
        assert "Input should be greater than or equal to 1" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValidationError was expected")
