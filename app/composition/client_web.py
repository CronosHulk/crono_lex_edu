from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any

from app.application.client_web.auth_service import ClientWebAuthService
from app.application.client_web.import_errors import (
    ClientWebImportValidationError,
)
from app.application.client_web.import_processing_service import (
    ClientWebImportProcessingService,
)
from app.application.client_web.import_results_service import ClientWebImportResultsService
from app.application.client_web.import_service import ClientWebImportService
from app.application.client_web.learning_errors import (
    ClientWebLearningNotFoundError,
    ClientWebLearningValidationError,
)
from app.application.client_web.learning_service import ClientWebLearningService
from app.application.client_web.learning_words_service import (
    ClientWebLearningWordsAccess,
    ClientWebLearningWordsService,
)
from app.application.client_web.plan_service import (
    ClientWebPlanAccountProvider,
    ClientWebPlanService,
)
from app.application.client_web.settings_service import (
    ClientWebSettingsService,
    ClientWebSettingsValidationError,
)
from app.application.client_web.teacher_students_errors import (
    ClientWebTeacherStudentConfigurationError,
)
from app.application.client_web.teacher_students_service import (
    ClientWebTeacherStudentGoogleMeetProvider,
    ClientWebTeacherStudentService,
)
from app.billing.services.checkout_service import BillingCheckoutService
from app.billing.services.history_service import BillingPaymentHistoryService
from app.billing.services.status_service import BillingPaymentStatusService
from app.composition.audio_storage import build_audio_storage_provider
from app.composition.client_web_import_events import (
    publish_import_event,
    stream_import_events,
)
from app.composition.client_web_provider_adapters import (
    GoogleMeetProviderConfigurationError,
    build_client_web_auth_telegram_gateway,
    build_google_calendar_meet_provider,
    build_teacher_student_telegram_gateway,
    build_web_learning_telegram_gateway,
)
from app.composition.user_import_artifact_storage import (
    build_user_import_artifact_storage_provider,
)
from app.composition.user_import_provider_adapters import (
    build_word_validation_provider,
    fetch_google_doc_text_with_provider,
)
from app.subscriptions.plan_limits import PlanLimitSettingsValidationError
from app.subscriptions.plans import IMPORT_MODE_AI_NEW_WORDS
from app.subscriptions.user_entitlements import UserEntitlementResolver, read_user_uuid
from app.user_import.services.candidate_filter_service import (
    UserImportCandidateFilterService,
)
from app.user_import.services.validation_service import UserImportValidationService


def configure_client_web_runtime(service: Any, db: Any) -> None:
    queue_post_upgrade_rescan = (
        service.user_import_bound_google_doc_sync_service.queue_post_upgrade_rescan
    )
    billing_provider_factory = getattr(service, "billing_payment_provider_factory", None)
    if getattr(service, "audio_storage_provider", None) is None:
        service.audio_storage_provider = build_audio_storage_provider(db.settings)
    if getattr(service, "user_import_artifact_storage_provider", None) is None:
        service.user_import_artifact_storage_provider = (
            build_user_import_artifact_storage_provider(db.settings)
        )

    service.client_web_auth_service = ClientWebAuthService(
        db,
        service.time_service,
        build_client_web_auth_telegram_gateway(db.settings),
    )
    learning_entitlement_resolver = UserEntitlementResolver(db)
    service.client_web_learning_words_service = ClientWebLearningWordsService(
        db,
        service.time_service,
        access_resolver=_build_client_web_learning_words_access_resolver(
            learning_entitlement_resolver,
        ),
    )
    service.client_web_learning_service = ClientWebLearningService(
        service,
        build_web_learning_telegram_gateway(db.settings),
        words_service=service.client_web_learning_words_service,
    )
    entitlement_resolver = UserEntitlementResolver(db)
    import_mode_for_user = _build_client_web_import_mode_for_user(
        entitlement_resolver,
    )
    service.client_web_import_results_service = ClientWebImportResultsService(
        service,
        import_mode_for_user=import_mode_for_user,
    )
    service.client_web_import_processing_service = ClientWebImportProcessingService(
        service,
        validation_service=UserImportValidationService(
            db,
            build_validation_provider=build_word_validation_provider,
        ),
        import_mode_for_user=import_mode_for_user,
        candidate_filter=UserImportCandidateFilterService(db),
        error_logger=_build_client_web_import_processing_error_logger(db),
        event_publisher=lambda event: publish_import_event(service, event),
    )
    service.client_web_import_service = ClientWebImportService(
        service,
        results_service=service.client_web_import_results_service,
        processing_service=service.client_web_import_processing_service,
        artifact_storage_provider=service.user_import_artifact_storage_provider,
        google_doc_text_fetcher=fetch_google_doc_text_with_provider,
    )
    service.client_web_settings_service = ClientWebSettingsService(
        db,
        service.reference,
        service.time_service,
        entitlement_provider=_build_client_web_settings_entitlement_provider(db),
    )
    service.client_web_plan_service = ClientWebPlanService(
        db,
        service.time_service,
        account_provider=_build_client_web_plan_account_provider(db),
        post_upgrade_rescan=queue_post_upgrade_rescan,
    )
    service.client_web_billing_checkout_service = BillingCheckoutService(
        db,
        service.time_service,
        billing_provider_factory=billing_provider_factory,
        post_upgrade_rescan=queue_post_upgrade_rescan,
    )
    service.client_web_billing_payment_status_service = BillingPaymentStatusService(
        db,
        service.time_service,
        billing_provider_factory=billing_provider_factory,
        billing_receipt_fiscal_provider_factory=billing_provider_factory,
        post_upgrade_rescan=queue_post_upgrade_rescan,
    )
    service.client_web_billing_payment_history_service = BillingPaymentHistoryService(db)
    service.client_web_teacher_student_service = ClientWebTeacherStudentService(
        db,
        service.time_service,
        build_teacher_student_telegram_gateway(db.settings),
        _build_teacher_student_google_provider_factory(db.settings),
    )
    service.client_web_import_event_streamer = _build_client_web_import_event_streamer(service)


def _build_teacher_student_google_provider_factory(settings: Any):
    def _build_provider() -> ClientWebTeacherStudentGoogleMeetProvider:
        try:
            return build_google_calendar_meet_provider(settings)
        except GoogleMeetProviderConfigurationError as error:
            raise ClientWebTeacherStudentConfigurationError(
                "Google OAuth is not configured"
            ) from error

    return _build_provider


def _build_client_web_import_mode_for_user(entitlement_resolver: UserEntitlementResolver):
    def _import_mode_for_user(user_uuid: str | None, *, current_time: datetime) -> str:
        if user_uuid is None:
            return IMPORT_MODE_AI_NEW_WORDS
        try:
            return entitlement_resolver.resolve_for_user_uuid(
                user_uuid,
                current_time=current_time,
            ).import_mode
        except PlanLimitSettingsValidationError as error:
            raise ClientWebImportValidationError(str(error)) from error

    return _import_mode_for_user


class _ClientWebSettingsEntitlementProvider:
    def __init__(self, entitlement_resolver: UserEntitlementResolver) -> None:
        self.entitlement_resolver = entitlement_resolver

    def resolve_for_profile(self, profile: dict[str, Any] | None, *, current_time: datetime) -> Any:
        try:
            return self.entitlement_resolver.resolve_for_user_uuid(
                read_user_uuid(profile),
                current_time=current_time,
            )
        except PlanLimitSettingsValidationError as error:
            raise ClientWebSettingsValidationError(str(error)) from error

    def user_uuid_from_profile(self, profile: dict[str, Any] | None) -> str | None:
        return read_user_uuid(profile)


def _build_client_web_settings_entitlement_provider(db: Any) -> _ClientWebSettingsEntitlementProvider:
    return _ClientWebSettingsEntitlementProvider(UserEntitlementResolver(db))


class _ClientWebPlanDataAccessProvider:
    def __init__(self, db: Any) -> None:
        from app.data_access.billing import BillingRepository
        from app.data_access.subscriptions import SubscriptionRepository
        from app.data_access.user_profiles import UserProfileRepository
        self.user_profiles = getattr(db, "user_profiles", None) or UserProfileRepository(db)
        self.subscriptions = getattr(db, "subscriptions", None) or SubscriptionRepository(db)
        self.billing = getattr(db, "billing", None) or BillingRepository(db)

    def user_uuid_for_user(self, user: dict[str, Any]) -> str | None:
        user_uuid = read_user_uuid(user)
        if not user_uuid:
            profile = self.user_profiles.get_profile(int(user["telegram_user_id"]))
            user_uuid = read_user_uuid(profile)
        return str(user_uuid) if user_uuid else None

    def subscription_for_user_uuid(self, user_uuid: str) -> Any | None:
        return self.subscriptions.get_by_user_uuid(user_uuid)

    def set_plan_for_user(self, user_uuid: str, *, plan_key: str, current_time: datetime) -> Any:
        return self.subscriptions.set_plan_for_user(
            user_uuid,
            plan_key=plan_key,
            current_time=current_time,
        )

    def billing_subscription_projection(
        self,
        user_uuid: str | None,
        *,
        fallback_subscription: Any | None,
        current_time: datetime,
    ) -> Any | None:
        if not user_uuid:
            return fallback_subscription
        projection = self.billing.get_subscription_projection_for_user(
            user_uuid,
            current_time=current_time,
        )
        if projection is None:
            return fallback_subscription
        return {
            "plan_key": projection.get("plan_key"),
            "start": projection.get("start"),
            "end": projection.get("end"),
            "status": "active",
        }


def _build_client_web_plan_account_provider(db: Any) -> ClientWebPlanAccountProvider:
    return _ClientWebPlanDataAccessProvider(db)


def _build_client_web_learning_words_access_resolver(entitlement_resolver: UserEntitlementResolver):
    def _access_resolver(
        telegram_user_id: int,
        *,
        current_time: datetime,
    ) -> ClientWebLearningWordsAccess:
        user_uuid = entitlement_resolver.user_uuid_for_telegram_user(telegram_user_id)
        if user_uuid is None:
            raise ClientWebLearningNotFoundError("User profile not found")
        try:
            entitlements = entitlement_resolver.resolve_for_user_uuid(
                user_uuid,
                current_time=current_time,
            )
        except PlanLimitSettingsValidationError as error:
            raise ClientWebLearningValidationError(str(error)) from error
        allowed_core_levels = (
            set(entitlements.level_titles)
            if entitlements.level_titles is not None
            else None
        )
        return ClientWebLearningWordsAccess(
            user_uuid=str(user_uuid),
            allowed_core_levels=allowed_core_levels,
            include_user_words=entitlements.level_titles is None,
        )

    return _access_resolver


def _build_client_web_import_processing_error_logger(db: Any):
    from app.data_access.error_logs import ErrorLogRepository
    error_logs_repo = getattr(db, "error_logs", None) or ErrorLogRepository(db)
    def _log_error(detail: str, *, import_job_id: int) -> None:
        error_logs_repo.create("error", detail, context_json={"import_job_id": import_job_id})

    return _log_error


def _build_client_web_import_event_streamer(service: Any):
    def _streamer(*, telegram_user_id: int, job_id: int) -> Iterator[str]:
        return stream_import_events(
            service,
            telegram_user_id=telegram_user_id,
            job_id=job_id,
        )

    return _streamer
