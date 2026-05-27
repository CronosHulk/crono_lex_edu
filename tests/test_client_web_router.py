from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.client_api.client_web.router as client_web_router
from app.application.client_web.auth_errors import (
    ClientWebAuthNotFoundError,
    ClientWebAuthRateLimitError,
    ClientWebAuthUnauthorizedError,
    ClientWebAuthValidationError,
)
from app.application.client_web.import_errors import (
    ClientWebImportNotFoundError,
    ClientWebImportProviderUnavailableError,
    ClientWebImportValidationError,
)
from app.application.client_web.learning_errors import (
    ClientWebLearningConflictError,
    ClientWebLearningNotFoundError,
    ClientWebLearningPaymentRequiredError,
    ClientWebLearningValidationError,
)
from app.application.client_web.plan_service import (
    ClientWebPlanProfileNotFoundError,
    ClientWebPlanValidationError,
)
from app.application.client_web.settings_service import (
    ClientWebSettingsValidationError,
)
from app.application.client_web.teacher_students_errors import (
    ClientWebTeacherStudentConfigurationError,
    ClientWebTeacherStudentConflictError,
    ClientWebTeacherStudentForbiddenError,
    ClientWebTeacherStudentNotFoundError,
    ClientWebTeacherStudentUpstreamError,
    ClientWebTeacherStudentValidationError,
)
from app.billing.services.checkout_service import (
    BillingCheckoutMaintenanceError,
    BillingCheckoutProfileNotFoundError,
    BillingCheckoutProviderUnavailableError,
    BillingCheckoutValidationError,
)
from app.billing.services.history_service import BillingPaymentHistoryProfileNotFoundError
from app.billing.services.status_service import (
    BillingPaymentStatusConfigurationError,
    BillingPaymentStatusNotFoundError,
)

ORIGINAL_CLIENT_WEB_AUTH_SERVICE = client_web_router.ClientWebAuthService
ORIGINAL_CLIENT_WEB_LEARNING_SERVICE = client_web_router.ClientWebLearningService
ORIGINAL_CLIENT_WEB_IMPORT_SERVICE = client_web_router.ClientWebImportService
ORIGINAL_CLIENT_WEB_SETTINGS_SERVICE = client_web_router.ClientWebSettingsService
ORIGINAL_CLIENT_WEB_PLAN_SERVICE = client_web_router.ClientWebPlanService
ORIGINAL_BILLING_CHECKOUT_SERVICE = client_web_router.BillingCheckoutService
ORIGINAL_BILLING_PAYMENT_STATUS_SERVICE = client_web_router.BillingPaymentStatusService
ORIGINAL_BILLING_PAYMENT_HISTORY_SERVICE = client_web_router.BillingPaymentHistoryService
ORIGINAL_CLIENT_WEB_TEACHER_STUDENT_SERVICE = client_web_router.ClientWebTeacherStudentService


class FakeClientWebSettings:
    app_admin_cookie_secure = False
    app_admin_session_hours = 1
    bot_token = ""


class FakeAppSettings:
    value: dict | None = None

    def get_value(self, key: str) -> dict | None:
        return self.value


class FakeClientWebDb:
    settings = FakeClientWebSettings()
    app_settings = FakeAppSettings()


class FakePostUpgradeRescanService:
    def queue_post_upgrade_rescan(self, **kwargs):
        return {"status": "queued", **kwargs}


class FakeLearningService:
    def __init__(self) -> None:
        self.db = FakeClientWebDb()
        self.time_service = object()
        self.reference = object()
        self.billing_provider_factory = object()
        self.audio_storage_provider = object()
        self.user_import_bound_google_doc_sync_service = FakePostUpgradeRescanService()
        self._wire_client_web_runtime()

    def _build_menu_screen(self, telegram_user_id: int, locale: str, **kwargs):
        return SimpleNamespace(
            text=f"Menu for {telegram_user_id}/{locale}",
            buttons=[SimpleNamespace(text="Почати", action="m:start", url=None)],
            metadata={"buttons_per_row": 1, **kwargs},
        )

    def _wire_client_web_runtime(self) -> None:
        auth_service_cls = _runtime_service_cls(
            client_web_router.ClientWebAuthService,
            ORIGINAL_CLIENT_WEB_AUTH_SERVICE,
            FakeClientWebAuthService,
        )
        learning_service_cls = _runtime_service_cls(
            client_web_router.ClientWebLearningService,
            ORIGINAL_CLIENT_WEB_LEARNING_SERVICE,
            FakeClientWebLearningService,
        )
        import_service_cls = _runtime_service_cls(
            client_web_router.ClientWebImportService,
            ORIGINAL_CLIENT_WEB_IMPORT_SERVICE,
            FakeClientWebImportService,
        )
        settings_service_cls = _runtime_service_cls(
            client_web_router.ClientWebSettingsService,
            ORIGINAL_CLIENT_WEB_SETTINGS_SERVICE,
            FakeClientWebSettingsService,
        )
        plan_service_cls = _runtime_service_cls(
            client_web_router.ClientWebPlanService,
            ORIGINAL_CLIENT_WEB_PLAN_SERVICE,
            FakeClientWebPlanService,
        )
        billing_checkout_service_cls = _runtime_service_cls(
            client_web_router.BillingCheckoutService,
            ORIGINAL_BILLING_CHECKOUT_SERVICE,
            FakeBillingCheckoutService,
        )
        billing_payment_status_service_cls = _runtime_service_cls(
            client_web_router.BillingPaymentStatusService,
            ORIGINAL_BILLING_PAYMENT_STATUS_SERVICE,
            FakeBillingPaymentStatusService,
        )
        billing_payment_history_service_cls = _runtime_service_cls(
            client_web_router.BillingPaymentHistoryService,
            ORIGINAL_BILLING_PAYMENT_HISTORY_SERVICE,
            FakeBillingPaymentHistoryService,
        )
        teacher_student_service_cls = _runtime_service_cls(
            client_web_router.ClientWebTeacherStudentService,
            ORIGINAL_CLIENT_WEB_TEACHER_STUDENT_SERVICE,
            FakeTeacherStudentService,
        )

        self.client_web_auth_service = auth_service_cls()
        self.client_web_learning_service = learning_service_cls(self, object())
        self.client_web_import_results_service = object()
        self.client_web_import_processing_service = SimpleNamespace(
            build_validation_provider=lambda settings, task_settings=None: SimpleNamespace(
                settings=settings,
                task_settings=task_settings,
            ),
            event_publisher=lambda _event: None,
        )
        self.client_web_import_service = import_service_cls(
            self,
            results_service=self.client_web_import_results_service,
            processing_service=self.client_web_import_processing_service,
            google_doc_text_fetcher=lambda source_url: source_url,
        )
        self.client_web_settings_service = settings_service_cls(
            self.db,
            self.reference,
            self.time_service,
            entitlement_provider=object(),
        )
        self.client_web_plan_service = plan_service_cls(
            self.db,
            self.time_service,
            account_provider=object(),
            post_upgrade_rescan=self.user_import_bound_google_doc_sync_service.queue_post_upgrade_rescan,
        )
        self.client_web_billing_checkout_service = billing_checkout_service_cls(
            self.db,
            self.time_service,
            billing_provider_factory=self.billing_provider_factory,
        )
        self.client_web_billing_payment_status_service = billing_payment_status_service_cls(
            self.db,
            self.time_service,
            post_upgrade_rescan=self.user_import_bound_google_doc_sync_service.queue_post_upgrade_rescan,
            billing_provider_factory=self.billing_provider_factory,
        )
        self.client_web_billing_payment_history_service = billing_payment_history_service_cls(self.db)
        self.client_web_teacher_student_service = teacher_student_service_cls(
            self.db,
            self.time_service,
            object(),
            lambda: object(),
        )
        self.client_web_import_event_streamer = (
            lambda *, telegram_user_id, job_id: iter(
                [f"event: connected\ndata: {{\"job_id\":{job_id},\"telegram_user_id\":{telegram_user_id}}}\n\n"]
            )
        )


def _runtime_service_cls(current: object, original: object, fallback: object) -> object:
    return fallback if current is original else current


class FakeClientWebAuthService:
    sent_menus: list[tuple[dict, str, dict | None]] = []

    def __init__(self, *args, **kwargs) -> None:
        pass

    def get_session_user(self, *args, **kwargs) -> dict:
        return {"telegram_user_id": 431130422, "interface_locale": "uk"}

    def verify_otp(self, *args, **kwargs):
        return SimpleNamespace(
            session_token="session-token",
            user={"telegram_user_id": 431130422, "interface_locale": "uk", "chat_id": 55},
        )

    def send_login_menu(self, user: dict, menu_text: str, reply_markup: dict | None) -> None:
        self.sent_menus.append((user, menu_text, reply_markup))


class UnauthenticatedClientWebAuthService(FakeClientWebAuthService):
    def get_session_user(self, *args, **kwargs) -> dict:
        raise ClientWebAuthUnauthorizedError("Session expired")


class UnauthorizedClientWebAuthStartService(FakeClientWebAuthService):
    def start_login(self, *args, **kwargs):
        raise ClientWebAuthUnauthorizedError("User is not registered in Telegram bot")


class RateLimitedClientWebAuthService(FakeClientWebAuthService):
    def verify_otp(self, *args, **kwargs):
        raise ClientWebAuthRateLimitError("Too many attempts")


class InvalidPasswordUpdateClientWebAuthService(FakeClientWebAuthService):
    def update_password(self, *args, **kwargs):
        raise ClientWebAuthValidationError("Password must contain digits")


class FakeClientWebLearningService:
    init_calls: list[tuple[object, object]] = []
    priority_calls: list[tuple[dict, str, int]] = []
    dictionary_learn_calls: list[tuple[dict, str, int]] = []

    def __init__(self, service, gateway, **_kwargs: object) -> None:
        self.service = service
        self.gateway = gateway
        self.init_calls.append((service, gateway))

    def words(self, user: dict, **kwargs) -> dict:
        return {
            "items": [
                {
                    "id": 1,
                    "word": "sample",
                    "topic": "",
                    "level": "A1",
                    "translation": "приклад",
                    "status": "Імпортоване",
                }
            ],
            "total": 1,
            "page": kwargs["page"],
            "page_size": kwargs["page_size"],
            "pages": 1,
            "mode": kwargs["mode"],
            "topic": kwargs["topic"],
            "telegram_user_id": user["telegram_user_id"],
        }

    def word_filters(self, user: dict) -> dict:
        return {
            "topics": [{"value": "business", "label": "бізнес"}],
            "levels": [{"value": "A1", "label": "A1"}],
            "telegram_user_id": user["telegram_user_id"],
        }

    def dictionary_search(self, user: dict, **kwargs) -> dict:
        return {
            "items": [{"id": "core:7", "word_source": "core", "word_id": 7, "word": "storage"}],
            "total": 1,
            "page": kwargs["page"],
            "page_size": kwargs["page_size"],
            "pages": 1,
            "query": kwargs["query"],
            "level": kwargs["level"],
            "telegram_user_id": user["telegram_user_id"],
        }

    def learn_dictionary_word(self, user: dict, *, word_source: str, word_id: int) -> dict:
        self.dictionary_learn_calls.append((user, word_source, word_id))
        return {"word_source": word_source, "word_id": word_id, "priority_rank": 1777390201}

    def prioritize_word(self, user: dict, *, word_source: str, word_id: int) -> dict:
        self.priority_calls.append((user, word_source, word_id))
        return {"word_source": word_source, "word_id": word_id, "priority_rank": 1777390200}

    def finish(self, user: dict) -> dict:
        return {"active_session": None, "telegram_user_id": user["telegram_user_id"]}

    def audio_path(self, user: dict, *, session_word_id: int) -> str:
        return f"runtime/audio/{session_word_id}.mp3"

    def dictionary_search_audio_path(self, user: dict, *, word_source: str, word_id: int) -> str:
        return f"runtime/audio/{word_source}-{word_id}.mp3"


class InvalidClientWebLearningService(FakeClientWebLearningService):
    def words(self, user: dict, **kwargs) -> dict:
        raise ClientWebLearningValidationError("Unsupported learning word mode")


class LockedClientWebLearningService(FakeClientWebLearningService):
    def dictionary_search(self, user: dict, **kwargs) -> dict:
        raise ClientWebLearningPaymentRequiredError("This word level is not available on your plan")


class MissingClientWebLearningService(FakeClientWebLearningService):
    def prioritize_word(self, user: dict, *, word_source: str, word_id: int) -> dict:
        raise ClientWebLearningNotFoundError("Learning word was not found")

    def audio_path(self, user: dict, *, session_word_id: int) -> str:
        raise ClientWebLearningNotFoundError("Audio not found")


class ConflictingClientWebLearningService(FakeClientWebLearningService):
    def finish(self, user: dict) -> dict:
        raise ClientWebLearningConflictError("Training session is active in another interface")


class FakeClientWebImportService:
    init_kwargs: list[dict[str, object]] = []
    submit_payloads: list[tuple[dict, dict]] = []
    clear_binding_users: list[dict] = []
    ensured_jobs: list[tuple[dict, int]] = []

    def __init__(self, service, **kwargs: object) -> None:
        self.service = service
        self.init_kwargs.append(dict(kwargs))

    def submit_import(self, user: dict, **kwargs) -> dict:
        kwargs.pop("background_tasks", None)
        self.submit_payloads.append((user, kwargs))
        return {
            "job": {"id": 9, "status": "completed", "total_items": 1, "successful_items": 1, "failed_items": 0},
            "results": {
                "items": [{"id": 1, "word": "carry on", "status_category": "queued", "status_label": "В черзі на додавання"}],
                "total": 1,
                "page": 1,
                "page_size": 20,
                "pages": 1,
            },
        }

    def list_results(self, user: dict, **kwargs) -> dict:
        return {
            "items": [],
            "total": 0,
            "page": kwargs["page"],
            "page_size": kwargs["page_size"],
            "status_category": kwargs["status_category"],
            "pages": 0,
            "telegram_user_id": user["telegram_user_id"],
            "job_id": kwargs["job_id"],
        }

    def list_user_results(self, user: dict, **kwargs) -> dict:
        return {
            "items": [],
            "total": 0,
            "page": kwargs["page"],
            "page_size": kwargs["page_size"],
            "status_category": kwargs["status_category"],
            "pages": 0,
            "telegram_user_id": user["telegram_user_id"],
        }

    def ensure_job_for_user(self, user: dict, job_id: int) -> None:
        self.ensured_jobs.append((user, job_id))

    def clear_google_doc_binding(self, user: dict) -> dict:
        self.clear_binding_users.append(user)
        return {"status": "ok"}


class InvalidClientWebImportService(FakeClientWebImportService):
    def list_results(self, user: dict, **kwargs) -> dict:
        raise ClientWebImportValidationError("Import result page_size must be one of 20, 50 or 100")

    def list_user_results(self, user: dict, **kwargs) -> dict:
        raise ClientWebImportValidationError("Import result status_category must be all, added, queued or rejected")


class InvalidClientWebImportSubmitService(FakeClientWebImportService):
    def submit_import(self, user: dict, **kwargs) -> dict:
        raise ClientWebImportValidationError("Provide exactly one import source: Google Doc URL or TXT file")


class UnavailableClientWebImportSubmitService(FakeClientWebImportService):
    def submit_import(self, user: dict, **kwargs) -> dict:
        raise ClientWebImportProviderUnavailableError("Google Doc cannot be downloaded")


class MissingClientWebImportService(FakeClientWebImportService):
    def ensure_job_for_user(self, user: dict, job_id: int) -> None:
        raise ClientWebImportNotFoundError("Import job not found")

    def list_results(self, user: dict, **kwargs) -> dict:
        raise ClientWebImportNotFoundError("Import job not found")


class FakeClientWebPlanService:
    list_calls: list[dict] = []
    select_calls: list[tuple[dict, str]] = []

    def __init__(self, db, time_service, *, account_provider, post_upgrade_rescan) -> None:
        self.db = db
        self.time_service = time_service
        self.account_provider = account_provider
        self.post_upgrade_rescan = post_upgrade_rescan

    def list_plans(self, user: dict) -> dict:
        self.__class__.list_calls.append(user)
        return {"current_plan_key": "free", "plans": [], "telegram_user_id": user["telegram_user_id"]}

    def select_plan(self, user: dict, *, plan_key: str) -> dict:
        self.__class__.select_calls.append((user, plan_key))
        return {"current_plan_key": plan_key, "telegram_user_id": user["telegram_user_id"]}


class InvalidClientWebPlanService(FakeClientWebPlanService):
    def list_plans(self, user: dict) -> dict:
        raise ClientWebPlanValidationError("Invalid plan settings")

    def select_plan(self, user: dict, *, plan_key: str) -> dict:
        raise ClientWebPlanValidationError("Paid plans require billing checkout")


class MissingProfileClientWebPlanService(FakeClientWebPlanService):
    def select_plan(self, user: dict, *, plan_key: str) -> dict:
        raise ClientWebPlanProfileNotFoundError("User profile not found")


class FakeClientWebSettingsService:
    get_calls: list[dict] = []
    update_calls: list[tuple[dict, dict]] = []

    def __init__(self, db, reference, time_service, *, entitlement_provider) -> None:
        self.db = db
        self.reference = reference
        self.time_service = time_service
        self.entitlement_provider = entitlement_provider

    def get_settings(self, user: dict) -> dict:
        self.__class__.get_calls.append(user)
        return {"settings": {"telegram_user_id": user["telegram_user_id"]}}

    def update_settings(self, user: dict, **kwargs) -> dict:
        self.__class__.update_calls.append((user, kwargs))
        return {"settings": kwargs, "telegram_user_id": user["telegram_user_id"]}


class InvalidClientWebSettingsService(FakeClientWebSettingsService):
    def get_settings(self, user: dict) -> dict:
        raise ClientWebSettingsValidationError("Invalid settings")

    def update_settings(self, user: dict, **kwargs) -> dict:
        raise ClientWebSettingsValidationError("Unsupported interface locale")


class FakeTeacherStudentService:
    init_calls: list[tuple[object, object, object, object]] = []
    meet_calls: list[tuple[dict, str]] = []

    def __init__(self, db, time_service, telegram_gateway, google_provider_factory, **_kwargs: object) -> None:
        self.db = db
        self.time_service = time_service
        self.telegram_gateway = telegram_gateway
        self.google_provider_factory = google_provider_factory
        self.__class__.init_calls.append((db, time_service, telegram_gateway, google_provider_factory))

    def create_meet_session(self, user: dict, *, student_user_id: str) -> dict:
        self.meet_calls.append((user, student_user_id))
        return {"meet_session": {"student_user_id": student_user_id}}


class InvalidTeacherStudentValidationService(FakeTeacherStudentService):
    def create_group(self, user: dict, *, title: str) -> dict:
        raise ClientWebTeacherStudentValidationError("group title is required")

    def update_student_alias(self, user: dict, *, student_user_id: str, teacher_alias: str | None) -> dict:
        raise ClientWebTeacherStudentValidationError("teacher_alias must be at most 80 characters")


class ForbiddenTeacherStudentService(FakeTeacherStudentService):
    def list_students(self, user: dict, **kwargs) -> dict:
        raise ClientWebTeacherStudentForbiddenError("Teacher access is required")


class MissingTeacherStudentService(FakeTeacherStudentService):
    def update_student_level(self, user: dict, *, student_user_id: str, language_level: str) -> dict:
        raise ClientWebTeacherStudentNotFoundError("Student not found")


class ConflictTeacherStudentService(FakeTeacherStudentService):
    def create_meet_session(self, user: dict, *, student_user_id: str) -> dict:
        raise ClientWebTeacherStudentConflictError("google_auth_required")


class UpstreamTeacherStudentService(FakeTeacherStudentService):
    def create_meet_session(self, user: dict, *, student_user_id: str) -> dict:
        raise ClientWebTeacherStudentUpstreamError("google_meet_creation_failed")


class UnconfiguredTeacherStudentService(FakeTeacherStudentService):
    def create_google_oauth_redirect(
        self,
        user: dict,
        *,
        return_to: str,
        pending_action: str | None,
        student_user_id: str | None,
    ) -> str:
        raise ClientWebTeacherStudentConfigurationError("Google OAuth is not configured")


class FakeBillingPaymentHistoryService:
    calls: list[tuple[dict, int, int]] = []

    def __init__(self, db) -> None:
        self.db = db

    def list_client_payments(self, user: dict, *, page: int, page_size: int) -> dict:
        self.calls.append((user, page, page_size))
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "pages": 0,
            "telegram_user_id": user["telegram_user_id"],
        }


class MissingProfileBillingPaymentHistoryService:
    def __init__(self, db) -> None:
        self.db = db

    def list_client_payments(self, user: dict, *, page: int, page_size: int) -> dict:
        raise BillingPaymentHistoryProfileNotFoundError()


class FakeBillingCheckoutService:
    checkout_calls: list[tuple[dict, dict]] = []
    init_factories: list[object | None] = []
    offer_calls = 0

    def __init__(self, db, time_service, *, billing_provider_factory) -> None:
        self.db = db
        self.time_service = time_service
        self.billing_provider_factory = billing_provider_factory
        self.__class__.init_factories.append(billing_provider_factory)

    def get_offer(self) -> dict:
        self.__class__.offer_calls += 1
        return {"offer_text": "offer", "offer_text_hash": "a" * 64, "offer_version": "a" * 16}

    def create_checkout(self, user: dict, **kwargs) -> dict:
        self.__class__.checkout_calls.append((user, kwargs))
        return {"checkout": {"page_url": "https://pay.example/p2_demo"}, "telegram_user_id": user["telegram_user_id"]}


class InvalidBillingCheckoutService(FakeBillingCheckoutService):
    def create_checkout(self, user: dict, **kwargs) -> dict:
        raise BillingCheckoutValidationError("offer_accepted must be true")


class MissingProfileBillingCheckoutService(FakeBillingCheckoutService):
    def create_checkout(self, user: dict, **kwargs) -> dict:
        raise BillingCheckoutProfileNotFoundError("User profile not found")


class MaintenanceBillingCheckoutService(FakeBillingCheckoutService):
    def create_checkout(self, user: dict, **kwargs) -> dict:
        raise BillingCheckoutMaintenanceError("Maintenance window")


class ProviderUnavailableBillingCheckoutService(FakeBillingCheckoutService):
    def create_checkout(self, user: dict, **kwargs) -> dict:
        raise BillingCheckoutProviderUnavailableError("Monobank checkout is temporarily unavailable")


class InvalidOfferBillingCheckoutService(FakeBillingCheckoutService):
    def get_offer(self) -> dict:
        raise BillingCheckoutValidationError("Invalid billing runtime settings")


class FakeBillingPaymentStatusService:
    calls: list[tuple[dict, int]] = []
    init_factories: list[object | None] = []

    def __init__(self, db, time_service, *, post_upgrade_rescan, billing_provider_factory) -> None:
        self.db = db
        self.time_service = time_service
        self.post_upgrade_rescan = post_upgrade_rescan
        self.billing_provider_factory = billing_provider_factory
        self.__class__.init_factories.append(billing_provider_factory)

    def get_client_payment_status(self, user: dict, *, payment_id: int, request_ip: str | None) -> dict:
        self.calls.append((user, payment_id))
        return {"payment": {"id": payment_id}, "telegram_user_id": user["telegram_user_id"]}


class MissingBillingPaymentStatusService(FakeBillingPaymentStatusService):
    def get_client_payment_status(self, user: dict, *, payment_id: int, request_ip: str | None) -> dict:
        raise BillingPaymentStatusNotFoundError("Billing payment not found")


class InvalidBillingPaymentStatusService(FakeBillingPaymentStatusService):
    def get_client_payment_status(self, user: dict, *, payment_id: int, request_ip: str | None) -> dict:
        raise BillingPaymentStatusConfigurationError("Invalid billing runtime settings")


def test_client_web_plans_get_uses_authenticated_user(monkeypatch) -> None:
    FakeClientWebPlanService.list_calls = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebPlanService", FakeClientWebPlanService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/plans")

    assert response.status_code == 200
    assert response.json() == {"current_plan_key": "free", "plans": [], "telegram_user_id": 431130422}
    assert FakeClientWebPlanService.list_calls == [{"telegram_user_id": 431130422, "interface_locale": "uk"}]


def test_client_web_plans_get_translates_plan_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebPlanService", InvalidClientWebPlanService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/plans")

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid plan settings"}


def test_client_web_plans_select_uses_authenticated_user_and_payload(monkeypatch) -> None:
    FakeClientWebPlanService.select_calls = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebPlanService", FakeClientWebPlanService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post("/client-web/plans/select", json={"plan_key": "free"})

    assert response.status_code == 200
    assert response.json() == {"current_plan_key": "free", "telegram_user_id": 431130422}
    assert FakeClientWebPlanService.select_calls == [
        ({"telegram_user_id": 431130422, "interface_locale": "uk"}, "free")
    ]


@pytest.mark.parametrize(
    ("plan_service_cls", "expected_status", "expected_detail"),
    [
        (InvalidClientWebPlanService, 400, "Paid plans require billing checkout"),
        (MissingProfileClientWebPlanService, 404, "User profile not found"),
    ],
)
def test_client_web_plans_select_translates_plan_errors(
    monkeypatch,
    plan_service_cls,
    expected_status: int,
    expected_detail: str,
) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebPlanService", plan_service_cls)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post("/client-web/plans/select", json={"plan_key": "free"})

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}


def test_client_web_settings_get_uses_authenticated_user(monkeypatch) -> None:
    FakeClientWebSettingsService.get_calls = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebSettingsService", FakeClientWebSettingsService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/settings")

    assert response.status_code == 200
    assert response.json() == {"settings": {"telegram_user_id": 431130422}}
    assert FakeClientWebSettingsService.get_calls == [{"telegram_user_id": 431130422, "interface_locale": "uk"}]


def test_client_web_settings_get_translates_settings_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebSettingsService", InvalidClientWebSettingsService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/settings")

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid settings"}


def test_client_web_settings_patch_uses_authenticated_user_and_payload(monkeypatch) -> None:
    FakeClientWebSettingsService.update_calls = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebSettingsService", FakeClientWebSettingsService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).patch(
        "/client-web/settings",
        json={"interface_locale": "UK", "reminder_weekdays": [2, 0]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "settings": {
            "interface_locale": "uk",
            "language_level": None,
            "words_per_session": None,
            "daily_reminder_hour": None,
            "reminder_weekdays": [0, 2],
            "reminder_schedule": None,
        },
        "telegram_user_id": 431130422,
    }
    assert FakeClientWebSettingsService.update_calls == [
        (
            {"telegram_user_id": 431130422, "interface_locale": "uk"},
            {
                "interface_locale": "uk",
                "language_level": None,
                "words_per_session": None,
                "daily_reminder_hour": None,
                "reminder_weekdays": [0, 2],
                "reminder_schedule": None,
            },
        )
    ]


def test_client_web_settings_patch_translates_settings_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebSettingsService", InvalidClientWebSettingsService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).patch("/client-web/settings", json={"interface_locale": "uk"})

    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported interface locale"}


def test_client_web_learning_words_accepts_imported_rotation_mode(monkeypatch) -> None:
    FakeClientWebLearningService.init_calls = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebLearningService", FakeClientWebLearningService)

    app = FastAPI()
    learning_service = FakeLearningService()
    app.include_router(client_web_router.build_client_web_router(learning_service))

    response = TestClient(app).get("/client-web/learning/words?mode=imported_rotation&page=1&page_size=20&topic=business&topic=travel")

    assert response.status_code == 200
    assert response.json()["mode"] == "imported_rotation"
    assert response.json()["topic"] == ["business", "travel"]
    assert len(FakeClientWebLearningService.init_calls) == 1
    assert FakeClientWebLearningService.init_calls[0][0] is learning_service


def test_client_web_learning_words_translates_validation_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebLearningService", InvalidClientWebLearningService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/learning/words?mode=unknown&page=1&page_size=20")

    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported learning word mode"}


def test_client_web_learning_dictionary_search_translates_payment_required_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebLearningService", LockedClientWebLearningService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/learning/dictionary-search?q=stor&page=1&page_size=20&level=B1")

    assert response.status_code == 402
    assert response.json() == {"detail": "This word level is not available on your plan"}


def test_client_web_learning_priority_translates_not_found_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebLearningService", MissingClientWebLearningService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post(
        "/client-web/learning/words/priority",
        json={"word_source": "core", "word_id": 404},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Learning word was not found"}


def test_client_web_learning_finish_translates_conflict_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebLearningService", ConflictingClientWebLearningService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post("/client-web/learning/finish")

    assert response.status_code == 409
    assert response.json() == {"detail": "Training session is active in another interface"}


def test_client_web_learning_session_audio_builds_response_at_route_boundary(monkeypatch) -> None:
    audio_response_calls = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebLearningService", FakeClientWebLearningService)
    monkeypatch.setattr(
        client_web_router,
        "build_audio_response",
        lambda audio_path, *, storage_provider: audio_response_calls.append(
            {"audio_path": audio_path, "storage_provider": storage_provider}
        )
        or {"audio_path": audio_path},
    )

    app = FastAPI()
    runtime = FakeLearningService()
    app.include_router(client_web_router.build_client_web_router(runtime))

    client = TestClient(app)
    response = client.get("/client-web/learning/session-words/11/audio")
    dictionary_response = client.get("/client-web/learning/dictionary-search/core/7/audio")

    assert response.status_code == 200
    assert response.json() == {"audio_path": "runtime/audio/11.mp3"}
    assert dictionary_response.status_code == 200
    assert dictionary_response.json() == {"audio_path": "runtime/audio/core-7.mp3"}
    assert audio_response_calls == [
        {"audio_path": "runtime/audio/11.mp3", "storage_provider": runtime.audio_storage_provider},
        {"audio_path": "runtime/audio/core-7.mp3", "storage_provider": runtime.audio_storage_provider},
    ]


def test_client_web_learning_session_audio_translates_not_found_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebLearningService", MissingClientWebLearningService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/learning/session-words/11/audio")

    assert response.status_code == 404
    assert response.json() == {"detail": "Audio not found"}


def test_client_web_auth_me_returns_guest_without_session_noise(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", UnauthenticatedClientWebAuthService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/auth/me")

    assert response.status_code == 200
    assert response.json() == {"user": None}


def test_client_web_auth_start_translates_auth_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", UnauthorizedClientWebAuthStartService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post("/client-web/auth/start", json={"username": "missing"})

    assert response.status_code == 401
    assert response.json() == {"detail": "User is not registered in Telegram bot"}


def test_client_web_auth_password_patch_translates_validation_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", InvalidPasswordUpdateClientWebAuthService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).patch(
        "/client-web/auth/password",
        json={"password": "Next1234", "confirm_password": "Next1234"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Password must contain digits"}


def test_client_web_auth_error_status_code_maps_not_found() -> None:
    assert client_web_router.client_web_auth_error_status_code(ClientWebAuthNotFoundError("User not found")) == 404


def test_client_web_analytics_settings_are_public() -> None:
    FakeClientWebDb.app_settings.value = {
        "google_analytics_id": "G-ABCDEF12",
        "google_ads_id": "AW-123456789",
    }
    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/analytics-settings")

    assert response.status_code == 200
    assert response.json() == {
        "google_analytics_id": "G-ABCDEF12",
        "google_ads_id": "AW-123456789",
    }
    FakeClientWebDb.app_settings.value = None


def test_client_web_protected_routes_still_reject_missing_session(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", UnauthenticatedClientWebAuthService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/learning/word-filters")

    assert response.status_code == 401


def test_client_web_learning_word_filters_returns_reference_options(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebLearningService", FakeClientWebLearningService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/learning/word-filters")

    assert response.status_code == 200
    assert response.json()["topics"] == [{"value": "business", "label": "бізнес"}]


def test_client_web_dictionary_search_uses_authenticated_user(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebLearningService", FakeClientWebLearningService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/learning/dictionary-search?q=stor&page=2&page_size=20&level=A1")

    assert response.status_code == 200
    assert response.json()["query"] == "stor"
    assert response.json()["level"] == "A1"
    assert response.json()["telegram_user_id"] == 431130422


def test_client_web_dictionary_search_learn_uses_authenticated_user(monkeypatch) -> None:
    FakeClientWebLearningService.dictionary_learn_calls = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebLearningService", FakeClientWebLearningService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post(
        "/client-web/learning/dictionary-search/learn",
        json={"word_source": "CORE", "word_id": 7},
    )

    assert response.status_code == 200
    assert response.json() == {"word_source": "core", "word_id": 7, "priority_rank": 1777390201}
    assert FakeClientWebLearningService.dictionary_learn_calls == [
        ({"telegram_user_id": 431130422, "interface_locale": "uk"}, "core", 7)
    ]


def test_client_web_learning_word_priority_uses_authenticated_user(monkeypatch) -> None:
    FakeClientWebLearningService.priority_calls = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebLearningService", FakeClientWebLearningService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post(
        "/client-web/learning/words/priority",
        json={"word_source": "USER", "word_id": 88},
    )

    assert response.status_code == 200
    assert response.json() == {"word_source": "user", "word_id": 88, "priority_rank": 1777390200}
    assert FakeClientWebLearningService.priority_calls == [
        ({"telegram_user_id": 431130422, "interface_locale": "uk"}, "user", 88)
    ]


def test_client_web_import_submit_uses_authenticated_user(monkeypatch) -> None:
    FakeClientWebImportService.submit_payloads = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebImportService", FakeClientWebImportService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post(
        "/client-web/imports",
        json={"text_content": "carry on", "file_name": "words.txt"},
    )

    assert response.status_code == 200
    assert response.json()["job"]["id"] == 9
    assert FakeClientWebImportService.submit_payloads == [
        (
            {"telegram_user_id": 431130422, "interface_locale": "uk"},
            {"source_url": None, "text_content": "carry on", "file_name": "words.txt"},
        )
    ]


def test_client_web_import_service_receives_provider_adapters(monkeypatch) -> None:
    FakeClientWebImportService.init_kwargs = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebImportService", FakeClientWebImportService)

    learning_service = FakeLearningService()
    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(learning_service))

    response = TestClient(app).post(
        "/client-web/imports",
        json={"text_content": "carry on", "file_name": "words.txt"},
    )

    assert response.status_code == 200
    assert len(FakeClientWebImportService.init_kwargs) == 1
    init_kwargs = FakeClientWebImportService.init_kwargs[0]
    assert init_kwargs["results_service"] is learning_service.client_web_import_results_service
    assert init_kwargs["processing_service"] is learning_service.client_web_import_processing_service
    assert callable(init_kwargs["google_doc_text_fetcher"])
    assert "build_validation_provider" not in init_kwargs
    assert "event_publisher" not in init_kwargs


@pytest.mark.parametrize(
    ("import_service_cls", "expected_status", "expected_detail"),
    [
        (InvalidClientWebImportSubmitService, 400, "Provide exactly one import source: Google Doc URL or TXT file"),
        (UnavailableClientWebImportSubmitService, 502, "Google Doc cannot be downloaded"),
    ],
)
def test_client_web_import_submit_translates_import_errors(
    monkeypatch,
    import_service_cls,
    expected_status: int,
    expected_detail: str,
) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebImportService", import_service_cls)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post(
        "/client-web/imports",
        json={"text_content": "carry on", "file_name": "words.txt"},
    )

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}


def test_client_web_import_items_are_paginated(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebImportService", FakeClientWebImportService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/imports/9/items?page=2&page_size=50&status_category=queued")

    assert response.status_code == 200
    assert response.json()["job_id"] == 9
    assert response.json()["page"] == 2
    assert response.json()["page_size"] == 50
    assert response.json()["status_category"] == "queued"


def test_client_web_import_items_translate_import_validation_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebImportService", InvalidClientWebImportService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/imports/9/items?page=1&page_size=21&status_category=queued")

    assert response.status_code == 400
    assert response.json() == {"detail": "Import result page_size must be one of 20, 50 or 100"}


def test_client_web_import_items_translate_import_not_found(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebImportService", MissingClientWebImportService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/imports/9/items?page=1&page_size=20&status_category=queued")

    assert response.status_code == 404
    assert response.json() == {"detail": "Import job not found"}


def test_client_web_import_events_stream_uses_authenticated_user(monkeypatch) -> None:
    FakeClientWebImportService.init_kwargs = []
    FakeClientWebImportService.ensured_jobs = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebImportService", FakeClientWebImportService)

    learning_service = FakeLearningService()
    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(learning_service))

    with TestClient(app).stream("GET", "/client-web/imports/events?job_id=9") as response:
        body = response.read().decode()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: connected" in body
    assert FakeClientWebImportService.ensured_jobs == [
        ({"telegram_user_id": 431130422, "interface_locale": "uk"}, 9)
    ]
    assert FakeClientWebImportService.init_kwargs[0]["results_service"] is (
        learning_service.client_web_import_results_service
    )
    assert FakeClientWebImportService.init_kwargs[0]["processing_service"] is (
        learning_service.client_web_import_processing_service
    )
    assert callable(FakeClientWebImportService.init_kwargs[0]["google_doc_text_fetcher"])


def test_client_web_import_events_translate_import_not_found(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebImportService", MissingClientWebImportService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/imports/events?job_id=9")

    assert response.status_code == 404
    assert response.json() == {"detail": "Import job not found"}


def test_client_web_import_user_items_are_paginated(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebImportService", FakeClientWebImportService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/imports/items?page=2&page_size=50&status_category=queued")

    assert response.status_code == 200
    assert response.json()["telegram_user_id"] == 431130422
    assert response.json()["page"] == 2
    assert response.json()["page_size"] == 50
    assert response.json()["status_category"] == "queued"


def test_client_web_import_user_items_translate_import_validation_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebImportService", InvalidClientWebImportService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/imports/items?page=1&page_size=20&status_category=queued")

    assert response.status_code == 400
    assert response.json() == {"detail": "Import result status_category must be all, added, queued or rejected"}


def test_client_web_import_items_reject_invalid_status_category(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebImportService", FakeClientWebImportService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/imports/9/items?page=1&page_size=20&status_category=broken")

    assert response.status_code == 422


def test_client_web_import_google_doc_binding_delete_uses_authenticated_user(monkeypatch) -> None:
    FakeClientWebImportService.clear_binding_users = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebImportService", FakeClientWebImportService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).delete("/client-web/imports/google-doc-binding")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert FakeClientWebImportService.clear_binding_users == [{"telegram_user_id": 431130422, "interface_locale": "uk"}]


def test_client_web_billing_offer_authenticates_user(monkeypatch) -> None:
    FakeBillingCheckoutService.offer_calls = 0
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "BillingCheckoutService", FakeBillingCheckoutService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/billing/offer")

    assert response.status_code == 200
    assert response.json() == {"offer_text": "offer", "offer_text_hash": "a" * 64, "offer_version": "a" * 16}
    assert FakeBillingCheckoutService.offer_calls == 1


def test_client_web_billing_offer_translates_checkout_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "BillingCheckoutService", InvalidOfferBillingCheckoutService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/billing/offer")

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid billing runtime settings"}


def test_client_web_billing_checkout_uses_authenticated_user_and_payload(monkeypatch) -> None:
    FakeBillingCheckoutService.checkout_calls = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "BillingCheckoutService", FakeBillingCheckoutService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post(
        "/client-web/billing/checkout",
        json={
            "plan_key": "premium",
            "period_months": 1,
            "offer_accepted": True,
            "offer_text_hash": "a" * 64,
            "source_path": "/plans",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"checkout": {"page_url": "https://pay.example/p2_demo"}, "telegram_user_id": 431130422}
    assert FakeBillingCheckoutService.checkout_calls == [
        (
            {"telegram_user_id": 431130422, "interface_locale": "uk"},
            {
                "plan_key": "premium",
                "period_months": 1,
                "offer_accepted": True,
                "offer_text_hash": "a" * 64,
                "source_path": "/plans",
                "request_ip": "testclient",
                "user_agent": "testclient",
            },
        )
    ]


def test_client_web_billing_checkout_service_receives_runtime_billing_provider_factory(monkeypatch) -> None:
    FakeBillingCheckoutService.init_factories = []
    billing_provider_factory = object()
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "BillingCheckoutService", FakeBillingCheckoutService)
    runtime = FakeLearningService()
    runtime.billing_provider_factory = billing_provider_factory
    runtime._wire_client_web_runtime()

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(runtime))

    response = TestClient(app).get("/client-web/billing/offer")

    assert response.status_code == 200
    assert FakeBillingCheckoutService.init_factories[-1] is billing_provider_factory


@pytest.mark.parametrize(
    ("checkout_service_cls", "expected_status", "expected_detail"),
    [
        (InvalidBillingCheckoutService, 400, "offer_accepted must be true"),
        (MissingProfileBillingCheckoutService, 404, "User profile not found"),
        (MaintenanceBillingCheckoutService, 503, "Maintenance window"),
        (ProviderUnavailableBillingCheckoutService, 502, "Monobank checkout is temporarily unavailable"),
    ],
)
def test_client_web_billing_checkout_translates_service_errors(
    monkeypatch,
    checkout_service_cls,
    expected_status: int,
    expected_detail: str,
) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "BillingCheckoutService", checkout_service_cls)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post(
        "/client-web/billing/checkout",
        json={
            "plan_key": "premium",
            "period_months": 1,
            "offer_accepted": True,
            "offer_text_hash": "a" * 64,
            "source_path": "/plans",
        },
    )

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}


def test_client_web_billing_payments_list_uses_authenticated_user(monkeypatch) -> None:
    FakeBillingPaymentHistoryService.calls = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "BillingPaymentHistoryService", FakeBillingPaymentHistoryService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/billing/payments?page=2&page_size=50")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "page": 2,
        "page_size": 50,
        "pages": 0,
        "telegram_user_id": 431130422,
    }
    assert FakeBillingPaymentHistoryService.calls == [
        ({"telegram_user_id": 431130422, "interface_locale": "uk"}, 2, 50)
    ]


def test_client_web_billing_payments_translates_missing_profile(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "BillingPaymentHistoryService", MissingProfileBillingPaymentHistoryService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/billing/payments")

    assert response.status_code == 404
    assert response.json() == {"detail": "User profile not found"}


def test_client_web_billing_payment_status_uses_authenticated_user(monkeypatch) -> None:
    FakeBillingPaymentStatusService.calls = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "BillingPaymentStatusService", FakeBillingPaymentStatusService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/billing/payments/7/status")

    assert response.status_code == 200
    assert response.json() == {"payment": {"id": 7}, "telegram_user_id": 431130422}
    assert FakeBillingPaymentStatusService.calls == [({"telegram_user_id": 431130422, "interface_locale": "uk"}, 7)]


def test_client_web_billing_payment_status_service_receives_runtime_billing_provider_factory(monkeypatch) -> None:
    FakeBillingPaymentStatusService.init_factories = []
    billing_provider_factory = object()
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "BillingPaymentStatusService", FakeBillingPaymentStatusService)
    runtime = FakeLearningService()
    runtime.billing_provider_factory = billing_provider_factory
    runtime._wire_client_web_runtime()

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(runtime))

    response = TestClient(app).get("/client-web/billing/payments/7/status")

    assert response.status_code == 200
    assert FakeBillingPaymentStatusService.init_factories[-1] is billing_provider_factory


def test_client_web_billing_payment_status_translates_not_found(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "BillingPaymentStatusService", MissingBillingPaymentStatusService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/billing/payments/7/status")

    assert response.status_code == 404
    assert response.json() == {"detail": "Billing payment not found"}


def test_client_web_billing_payment_status_translates_configuration_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "BillingPaymentStatusService", InvalidBillingPaymentStatusService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/billing/payments/7/status")

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid billing runtime settings"}


def test_client_web_teacher_student_uuid_path_is_validated(monkeypatch) -> None:
    FakeTeacherStudentService.meet_calls = []
    FakeTeacherStudentService.init_calls = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebTeacherStudentService", FakeTeacherStudentService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post("/client-web/students/not-a-valid-uuid-000000000000/meet-session")

    assert response.status_code == 422
    assert FakeTeacherStudentService.meet_calls == []
    assert len(FakeTeacherStudentService.init_calls) == 1


def test_client_web_teacher_student_service_receives_provider_adapters(monkeypatch) -> None:
    gateway = object()
    provider = object()
    FakeTeacherStudentService.meet_calls = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    runtime = FakeLearningService()
    runtime.client_web_teacher_student_service = FakeTeacherStudentService(
        runtime.db,
        runtime.time_service,
        gateway,
        lambda: provider,
    )
    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(runtime))

    response = TestClient(app).post("/client-web/students/11111111-1111-4111-8111-111111111111/meet-session")

    assert response.status_code == 200
    assert FakeTeacherStudentService.meet_calls == [
        ({"telegram_user_id": 431130422, "interface_locale": "uk"}, "11111111-1111-4111-8111-111111111111")
    ]


def test_client_web_teacher_student_group_translates_validation_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebTeacherStudentService", InvalidTeacherStudentValidationService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post("/client-web/students/groups", json={"title": " "})

    assert response.status_code == 400
    assert response.json() == {"detail": "group title is required"}


def test_client_web_teacher_student_alias_translates_validation_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebTeacherStudentService", InvalidTeacherStudentValidationService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).patch(
        "/client-web/students/11111111-1111-4111-8111-111111111111/alias",
        json={"teacher_alias": "a"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "teacher_alias must be at most 80 characters"}


def test_client_web_teacher_student_list_translates_forbidden_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebTeacherStudentService", ForbiddenTeacherStudentService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/students")

    assert response.status_code == 403
    assert response.json() == {"detail": "Teacher access is required"}


def test_client_web_teacher_student_level_translates_not_found_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebTeacherStudentService", MissingTeacherStudentService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).patch(
        "/client-web/students/11111111-1111-4111-8111-111111111111/level",
        json={"language_level": "A1"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Student not found"}


def test_client_web_teacher_student_meet_translates_conflict_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebTeacherStudentService", ConflictTeacherStudentService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post("/client-web/students/11111111-1111-4111-8111-111111111111/meet-session")

    assert response.status_code == 409
    assert response.json() == {"detail": "google_auth_required"}


def test_client_web_teacher_student_meet_translates_upstream_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebTeacherStudentService", UpstreamTeacherStudentService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post("/client-web/students/11111111-1111-4111-8111-111111111111/meet-session")

    assert response.status_code == 502
    assert response.json() == {"detail": "google_meet_creation_failed"}


def test_client_web_teacher_student_oauth_start_translates_configuration_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebTeacherStudentService", UnconfiguredTeacherStudentService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).get("/client-web/google/oauth/start")

    assert response.status_code == 503
    assert response.json() == {"detail": "Google OAuth is not configured"}


def test_client_web_learning_finish_closes_completed_summary(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)
    monkeypatch.setattr(client_web_router, "ClientWebLearningService", FakeClientWebLearningService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post("/client-web/learning/finish")

    assert response.status_code == 200
    assert response.json() == {"active_session": None, "telegram_user_id": 431130422}


def test_client_web_verify_otp_leaves_telegram_restore_to_auth_service(monkeypatch) -> None:
    FakeClientWebAuthService.sent_menus = []
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", FakeClientWebAuthService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post("/client-web/auth/verify-otp", json={"challenge_id": 1, "otp": "123456"})

    assert response.status_code == 200
    assert response.json()["user"]["telegram_user_id"] == 431130422
    assert response.cookies.get("cronolex_client_session") == "session-token"
    assert FakeClientWebAuthService.sent_menus == []


def test_client_web_verify_otp_translates_rate_limit_error(monkeypatch) -> None:
    monkeypatch.setattr(client_web_router, "ClientWebAuthService", RateLimitedClientWebAuthService)

    app = FastAPI()
    app.include_router(client_web_router.build_client_web_router(FakeLearningService()))

    response = TestClient(app).post("/client-web/auth/verify-otp", json={"challenge_id": 7, "otp": "123456"})

    assert response.status_code == 429
    assert response.json() == {"detail": "Too many attempts"}
    assert response.cookies.get("cronolex_client_session") is None
