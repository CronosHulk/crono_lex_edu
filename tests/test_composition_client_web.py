from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.composition.client_web as client_web_composition
from app.application.client_web.learning_errors import (
    ClientWebLearningNotFoundError,
    ClientWebLearningValidationError,
)
from app.application.client_web.settings_service import ClientWebSettingsValidationError
from app.application.client_web.teacher_students_errors import (
    ClientWebTeacherStudentConfigurationError,
)
from app.composition.client_web_provider_adapters import (
    GoogleMeetProviderConfigurationError,
)
from app.subscriptions.plan_limits import PlanLimitSettingsValidationError


class _CaptureInit:
    calls: list[tuple[tuple[object, ...], dict[str, object]]]

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.calls.append((args, kwargs))


def test_configure_client_web_runtime_attaches_services_and_wires_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, tuple[tuple[object, ...], dict[str, object]]] = {}
    published_events: list[tuple[object, object]] = []
    streamed_calls: list[tuple[object, int, int]] = []
    auth_gateway_settings: list[object] = []
    learning_gateway_settings: list[object] = []
    teacher_gateway_settings: list[object] = []
    google_provider_settings: list[object] = []
    audio_storage_provider = object()
    artifact_storage_provider = object()
    logged_errors: list[dict[str, object]] = []

    db = SimpleNamespace(
        settings=SimpleNamespace(bot_token="token"),
        user_profiles=object(),
        subscriptions=object(),
        error_logs=SimpleNamespace(
            create=lambda level, detail, *, context_json=None: logged_errors.append(
                {"level": level, "detail": detail, "context_json": context_json}
            )
        ),
    )
    queue_post_upgrade_rescan = object()
    service = SimpleNamespace(
        time_service=object(),
        reference=object(),
        billing_payment_provider_factory=object(),
        user_import_bound_google_doc_sync_service=SimpleNamespace(
            queue_post_upgrade_rescan=queue_post_upgrade_rescan
        ),
    )

    def _capture(name: str):
        class _Captured(_CaptureInit):
            calls = []

            def __init__(self, *args: object, **kwargs: object) -> None:
                super().__init__(*args, **kwargs)
                captured[name] = (args, kwargs)

        return _Captured

    def fake_auth_gateway(settings: object) -> object:
        auth_gateway_settings.append(settings)
        return "auth-gateway"

    def fake_learning_gateway(settings: object) -> object:
        learning_gateway_settings.append(settings)
        return "learning-gateway"

    def fake_teacher_gateway(settings: object) -> object:
        teacher_gateway_settings.append(settings)
        return "teacher-gateway"

    def fake_google_provider(settings: object) -> object:
        google_provider_settings.append(settings)
        return "google-provider"

    def fake_fetch_google_doc_text_with_provider(*_args: object, **_kwargs: object) -> object:
        return object()

    def fake_build_word_validation_provider(*_args: object, **_kwargs: object) -> object:
        return object()

    def fake_publish_import_event(publish_service: object, event: object) -> None:
        published_events.append((publish_service, event))

    def fake_stream_import_events(
        stream_service: object,
        *,
        telegram_user_id: int,
        job_id: int,
    ):
        streamed_calls.append((stream_service, telegram_user_id, job_id))
        return iter(["event: connected\ndata: {}\n\n"])

    monkeypatch.setattr(client_web_composition, "ClientWebAuthService", _capture("auth"))
    monkeypatch.setattr(client_web_composition, "ClientWebLearningService", _capture("learning"))
    monkeypatch.setattr(
        client_web_composition,
        "ClientWebImportResultsService",
        _capture("import_results"),
    )
    monkeypatch.setattr(
        client_web_composition,
        "ClientWebImportProcessingService",
        _capture("import_processing"),
    )
    monkeypatch.setattr(client_web_composition, "ClientWebImportService", _capture("import"))
    monkeypatch.setattr(client_web_composition, "ClientWebSettingsService", _capture("settings"))
    monkeypatch.setattr(client_web_composition, "ClientWebPlanService", _capture("plan"))
    monkeypatch.setattr(client_web_composition, "BillingCheckoutService", _capture("checkout"))
    monkeypatch.setattr(client_web_composition, "BillingPaymentStatusService", _capture("status"))
    monkeypatch.setattr(client_web_composition, "BillingPaymentHistoryService", _capture("history"))
    monkeypatch.setattr(client_web_composition, "ClientWebTeacherStudentService", _capture("teacher"))
    monkeypatch.setattr(
        client_web_composition,
        "build_client_web_auth_telegram_gateway",
        fake_auth_gateway,
    )
    monkeypatch.setattr(
        client_web_composition,
        "build_web_learning_telegram_gateway",
        fake_learning_gateway,
    )
    monkeypatch.setattr(
        client_web_composition,
        "build_teacher_student_telegram_gateway",
        fake_teacher_gateway,
    )
    monkeypatch.setattr(
        client_web_composition,
        "build_google_calendar_meet_provider",
        fake_google_provider,
    )
    monkeypatch.setattr(
        client_web_composition,
        "fetch_google_doc_text_with_provider",
        fake_fetch_google_doc_text_with_provider,
    )
    monkeypatch.setattr(
        client_web_composition,
        "build_word_validation_provider",
        fake_build_word_validation_provider,
    )
    monkeypatch.setattr(client_web_composition, "publish_import_event", fake_publish_import_event)
    monkeypatch.setattr(client_web_composition, "stream_import_events", fake_stream_import_events)
    monkeypatch.setattr(
        client_web_composition,
        "build_audio_storage_provider",
        lambda _settings: audio_storage_provider,
    )
    monkeypatch.setattr(
        client_web_composition,
        "build_user_import_artifact_storage_provider",
        lambda _settings: artifact_storage_provider,
    )

    client_web_composition.configure_client_web_runtime(service, db)

    assert isinstance(service.client_web_auth_service, _CaptureInit)
    assert isinstance(service.client_web_learning_service, _CaptureInit)
    assert isinstance(service.client_web_import_results_service, _CaptureInit)
    assert isinstance(service.client_web_import_processing_service, _CaptureInit)
    assert isinstance(service.client_web_import_service, _CaptureInit)
    assert isinstance(service.client_web_settings_service, _CaptureInit)
    assert isinstance(service.client_web_plan_service, _CaptureInit)
    assert isinstance(service.client_web_billing_checkout_service, _CaptureInit)
    assert isinstance(service.client_web_billing_payment_status_service, _CaptureInit)
    assert isinstance(service.client_web_billing_payment_history_service, _CaptureInit)
    assert isinstance(service.client_web_teacher_student_service, _CaptureInit)
    assert callable(service.client_web_import_event_streamer)
    assert service.audio_storage_provider is audio_storage_provider
    assert service.user_import_artifact_storage_provider is artifact_storage_provider

    assert auth_gateway_settings == [db.settings]
    assert learning_gateway_settings == [db.settings]
    assert teacher_gateway_settings == [db.settings]

    learning_kwargs = captured["learning"][1]
    assert "words_service" in learning_kwargs
    assert isinstance(
        learning_kwargs["words_service"],
        client_web_composition.ClientWebLearningWordsService,
    )
    assert learning_kwargs["words_service"].db is db
    assert learning_kwargs["words_service"].time_service is service.time_service
    assert callable(learning_kwargs["words_service"].access_resolver)

    assert captured["checkout"][1]["billing_provider_factory"] is service.billing_payment_provider_factory
    assert captured["status"][1]["billing_provider_factory"] is service.billing_payment_provider_factory
    assert captured["status"][1]["billing_receipt_fiscal_provider_factory"] is (
        service.billing_payment_provider_factory
    )
    assert captured["plan"][1]["post_upgrade_rescan"] is queue_post_upgrade_rescan
    assert isinstance(
        captured["plan"][1]["account_provider"],
        client_web_composition._ClientWebPlanDataAccessProvider,
    )
    assert captured["status"][1]["post_upgrade_rescan"] is queue_post_upgrade_rescan
    assert "entitlement_provider" in captured["settings"][1]

    results_kwargs = captured["import_results"][1]
    assert callable(results_kwargs["import_mode_for_user"])

    processing_kwargs = captured["import_processing"][1]
    assert processing_kwargs["validation_service"].db is db
    assert processing_kwargs["validation_service"].build_validation_provider is fake_build_word_validation_provider
    assert processing_kwargs["candidate_filter"].db is db
    assert callable(processing_kwargs["import_mode_for_user"])
    assert processing_kwargs["import_mode_for_user"] is results_kwargs["import_mode_for_user"]
    assert callable(processing_kwargs["error_logger"])
    assert "build_validation_provider" not in processing_kwargs
    processing_kwargs["error_logger"]("boom", import_job_id=12)
    assert logged_errors == [{"level": "error", "detail": "boom", "context_json": {"import_job_id": 12}}]
    event = object()
    processing_kwargs["event_publisher"](event)
    assert published_events == [(service, event)]

    import_kwargs = captured["import"][1]
    assert import_kwargs["results_service"] is service.client_web_import_results_service
    assert import_kwargs["processing_service"] is service.client_web_import_processing_service
    assert import_kwargs["artifact_storage_provider"] is artifact_storage_provider
    assert import_kwargs["google_doc_text_fetcher"] is fake_fetch_google_doc_text_with_provider
    assert "build_validation_provider" not in import_kwargs
    assert "event_publisher" not in import_kwargs

    provider_factory = captured["teacher"][0][3]
    assert provider_factory() == "google-provider"
    assert google_provider_settings == [db.settings]

    stream = service.client_web_import_event_streamer(telegram_user_id=11, job_id=22)
    assert next(stream) == "event: connected\ndata: {}\n\n"
    assert streamed_calls == [(service, 11, 22)]


def test_configure_client_web_runtime_preserves_existing_audio_storage_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Noop:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

    existing_audio_storage_provider = object()
    default_audio_storage_provider = object()
    db = SimpleNamespace(
        settings=SimpleNamespace(bot_token="token"),
        user_profiles=object(),
        subscriptions=object(),
    )
    service = SimpleNamespace(
        time_service=object(),
        reference=object(),
        audio_storage_provider=existing_audio_storage_provider,
        user_import_artifact_storage_provider=object(),
        user_import_bound_google_doc_sync_service=SimpleNamespace(
            queue_post_upgrade_rescan=object()
        ),
    )

    monkeypatch.setattr(client_web_composition, "ClientWebAuthService", _Noop)
    monkeypatch.setattr(client_web_composition, "ClientWebLearningService", _Noop)
    monkeypatch.setattr(client_web_composition, "ClientWebImportResultsService", _Noop)
    monkeypatch.setattr(client_web_composition, "ClientWebImportProcessingService", _Noop)
    monkeypatch.setattr(client_web_composition, "ClientWebImportService", _Noop)
    monkeypatch.setattr(client_web_composition, "ClientWebSettingsService", _Noop)
    monkeypatch.setattr(client_web_composition, "ClientWebPlanService", _Noop)
    monkeypatch.setattr(client_web_composition, "BillingCheckoutService", _Noop)
    monkeypatch.setattr(client_web_composition, "BillingPaymentStatusService", _Noop)
    monkeypatch.setattr(client_web_composition, "BillingPaymentHistoryService", _Noop)
    monkeypatch.setattr(client_web_composition, "ClientWebTeacherStudentService", _Noop)
    monkeypatch.setattr(
        client_web_composition,
        "build_client_web_auth_telegram_gateway",
        lambda _settings: object(),
    )
    monkeypatch.setattr(
        client_web_composition,
        "build_web_learning_telegram_gateway",
        lambda _settings: object(),
    )
    monkeypatch.setattr(
        client_web_composition,
        "build_teacher_student_telegram_gateway",
        lambda _settings: object(),
    )
    monkeypatch.setattr(
        client_web_composition,
        "build_audio_storage_provider",
        lambda _settings: default_audio_storage_provider,
    )

    client_web_composition.configure_client_web_runtime(service, db)

    assert service.audio_storage_provider is existing_audio_storage_provider


def test_learning_words_access_resolver_maps_entitlements() -> None:
    resolved_calls: list[dict[str, object]] = []

    class _Resolver:
        def user_uuid_for_telegram_user(self, telegram_user_id: int) -> str:
            assert telegram_user_id == 42
            return "user-uuid"

        def resolve_for_user_uuid(self, user_uuid: str, *, current_time: object):
            resolved_calls.append({"user_uuid": user_uuid, "current_time": current_time})
            return SimpleNamespace(level_titles=["A1", "A2"])

    current_time = object()
    access_resolver = client_web_composition._build_client_web_learning_words_access_resolver(
        _Resolver()
    )

    access = access_resolver(42, current_time=current_time)

    assert access.user_uuid == "user-uuid"
    assert access.allowed_core_levels == {"A1", "A2"}
    assert access.include_user_words is False
    assert resolved_calls == [{"user_uuid": "user-uuid", "current_time": current_time}]


def test_learning_words_access_resolver_maps_missing_profile() -> None:
    class _Resolver:
        def user_uuid_for_telegram_user(self, telegram_user_id: int) -> None:
            return None

    access_resolver = client_web_composition._build_client_web_learning_words_access_resolver(
        _Resolver()
    )

    with pytest.raises(ClientWebLearningNotFoundError) as error:
        access_resolver(42, current_time=object())

    assert error.value.detail == "User profile not found"


def test_learning_words_access_resolver_maps_plan_limit_errors() -> None:
    class _Resolver:
        def user_uuid_for_telegram_user(self, telegram_user_id: int) -> str:
            return "user-uuid"

        def resolve_for_user_uuid(self, user_uuid: str, *, current_time: object):
            raise PlanLimitSettingsValidationError("bad limits")

    access_resolver = client_web_composition._build_client_web_learning_words_access_resolver(
        _Resolver()
    )

    with pytest.raises(ClientWebLearningValidationError) as error:
        access_resolver(42, current_time=object())

    assert error.value.detail == "bad limits"


def test_settings_entitlement_provider_resolves_profile_and_maps_plan_limit_errors() -> None:
    resolved_calls: list[dict[str, object]] = []

    class _Resolver:
        def resolve_for_user_uuid(self, user_uuid: str | None, *, current_time: object):
            resolved_calls.append({"user_uuid": user_uuid, "current_time": current_time})
            return SimpleNamespace(import_mode="lookup_only", reminders_per_day=1)

    current_time = object()
    provider = client_web_composition._ClientWebSettingsEntitlementProvider(_Resolver())

    entitlements = provider.resolve_for_profile({"user_uuid": "user-uuid"}, current_time=current_time)

    assert entitlements.import_mode == "lookup_only"
    assert resolved_calls == [{"user_uuid": "user-uuid", "current_time": current_time}]
    assert provider.user_uuid_from_profile({"user_id": "profile-uuid"}) == "profile-uuid"

    class _FailingResolver:
        def resolve_for_user_uuid(self, user_uuid: str | None, *, current_time: object):
            raise PlanLimitSettingsValidationError("bad limits")

    failing_provider = client_web_composition._ClientWebSettingsEntitlementProvider(_FailingResolver())
    with pytest.raises(ClientWebSettingsValidationError) as error:
        failing_provider.resolve_for_profile({"user_uuid": "user-uuid"}, current_time=current_time)

    assert error.value.detail == "bad limits"


def test_plan_account_provider_resolves_profile_subscription_and_billing_projection() -> None:
    current_time = object()
    subscription = {"plan_key": "free"}
    projection = {
        "plan_key": "premium",
        "start": "start",
        "end": "end",
        "purchase_ids": [1],
    }
    db = SimpleNamespace(
        user_profiles=SimpleNamespace(
            get_profile=lambda telegram_user_id: {
                "telegram_user_id": telegram_user_id,
                "user_id": "profile-user-uuid",
            }
        ),
        subscriptions=SimpleNamespace(
            get_by_user_uuid=lambda user_uuid: {"user_uuid": user_uuid, **subscription},
            set_plan_for_user=lambda user_uuid, *, plan_key, current_time: {
                "user_uuid": user_uuid,
                "plan_key": plan_key,
                "current_time": current_time,
            },
        ),
        billing=SimpleNamespace(
            get_subscription_projection_for_user=lambda user_uuid, *, current_time: projection
        ),
    )
    provider = client_web_composition._build_client_web_plan_account_provider(db)

    assert provider.user_uuid_for_user({"telegram_user_id": 42}) == "profile-user-uuid"
    assert provider.user_uuid_for_user({"telegram_user_id": 42, "user_uuid": "request-user-uuid"}) == "request-user-uuid"
    assert provider.subscription_for_user_uuid("profile-user-uuid") == {
        "user_uuid": "profile-user-uuid",
        "plan_key": "free",
    }
    assert provider.set_plan_for_user("profile-user-uuid", plan_key="premium", current_time=current_time) == {
        "user_uuid": "profile-user-uuid",
        "plan_key": "premium",
        "current_time": current_time,
    }
    assert provider.billing_subscription_projection(
        "profile-user-uuid",
        fallback_subscription=subscription,
        current_time=current_time,
    ) == {
        "plan_key": "premium",
        "start": "start",
        "end": "end",
        "status": "active",
    }


def test_configure_client_web_runtime_maps_google_provider_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Noop:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

    captured: dict[str, tuple[tuple[object, ...], dict[str, object]]] = {}
    db = SimpleNamespace(
        settings=SimpleNamespace(bot_token="token"),
        user_profiles=object(),
        subscriptions=object(),
    )
    service = SimpleNamespace(
        time_service=object(),
        reference=object(),
        user_import_artifact_storage_provider=object(),
        user_import_bound_google_doc_sync_service=SimpleNamespace(
            queue_post_upgrade_rescan=object()
        ),
    )

    class _CaptureTeacher:
        def __init__(self, *args: object, **kwargs: object) -> None:
            captured["teacher"] = (args, kwargs)

    def fail_google_provider(_settings: object) -> object:
        raise GoogleMeetProviderConfigurationError("missing config")

    monkeypatch.setattr(client_web_composition, "ClientWebAuthService", _Noop)
    monkeypatch.setattr(client_web_composition, "ClientWebLearningService", _Noop)
    monkeypatch.setattr(client_web_composition, "ClientWebImportResultsService", _Noop)
    monkeypatch.setattr(client_web_composition, "ClientWebImportProcessingService", _Noop)
    monkeypatch.setattr(client_web_composition, "ClientWebImportService", _Noop)
    monkeypatch.setattr(client_web_composition, "ClientWebSettingsService", _Noop)
    monkeypatch.setattr(client_web_composition, "ClientWebPlanService", _Noop)
    monkeypatch.setattr(client_web_composition, "BillingCheckoutService", _Noop)
    monkeypatch.setattr(client_web_composition, "BillingPaymentStatusService", _Noop)
    monkeypatch.setattr(client_web_composition, "BillingPaymentHistoryService", _Noop)
    monkeypatch.setattr(client_web_composition, "ClientWebTeacherStudentService", _CaptureTeacher)
    monkeypatch.setattr(
        client_web_composition,
        "build_client_web_auth_telegram_gateway",
        lambda _settings: object(),
    )
    monkeypatch.setattr(
        client_web_composition,
        "build_web_learning_telegram_gateway",
        lambda _settings: object(),
    )
    monkeypatch.setattr(
        client_web_composition,
        "build_teacher_student_telegram_gateway",
        lambda _settings: object(),
    )
    monkeypatch.setattr(
        client_web_composition,
        "build_google_calendar_meet_provider",
        fail_google_provider,
    )

    client_web_composition.configure_client_web_runtime(service, db)

    provider_factory = captured["teacher"][0][3]
    with pytest.raises(ClientWebTeacherStudentConfigurationError) as error:
        provider_factory()
    assert str(error.value) == "Google OAuth is not configured"
