from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.application.admin.ai_usage.action_otp import AdminAIUsageActionOtpVerifier
from app.application.admin.ai_usage.read_service import (
    AdminAIUsageReadDatabasePort,
    AdminAIUsageReadService,
)
from app.application.admin.auth.auth_service import AdminAuthDatabasePort, AdminAuthService
from app.application.admin.auth.gateways import AdminAuthTelegramGateway
from app.application.admin.billing.read_service import (
    AdminBillingReadDatabasePort,
    AdminBillingReadService,
)
from app.application.admin.bootstrap_service import AdminBootstrapService
from app.application.admin.dashboard.dashboard_service import (
    AdminDashboardDatabasePort,
    AdminDashboardService,
)
from app.application.admin.dictionary.action_service import (
    AdminDictionaryActionDatabasePort,
    AdminDictionaryActionService,
)
from app.application.admin.dictionary.dictionary_service import (
    AdminDictionaryDatabasePort,
    AdminDictionaryService,
)
from app.application.admin.entity.entity_service import AdminEntityService
from app.application.admin.exercise_texts.exercise_text_service import (
    AdminExerciseTextDatabasePort,
    AdminExerciseTextService,
)
from app.application.admin.exercise_texts.generation_service import (
    AdminExerciseTextGenerationDatabasePort,
    AdminExerciseTextGenerationService,
    AdminExerciseTextGenerationUsageDatabasePort,
)
from app.application.admin.exercise_texts.tts_service import (
    AdminExerciseTextTTSDatabasePort,
    AdminExerciseTextTTSService,
)
from app.application.admin.read.read_service import AdminReadDatabasePort, AdminReadService
from app.application.admin.settings.action_otp import AdminSettingsActionOtpVerifier
from app.application.admin.settings.settings_service import (
    AdminSettingsDatabasePort,
    AdminSettingsService,
)
from app.application.admin.user_dictionary.bulk import (
    AdminUserDictionaryBulkAction,
    AdminUserDictionaryBulkDatabasePort,
)
from app.application.admin.user_dictionary.promote import (
    AdminUserDictionaryPromoteAction,
    AdminUserDictionaryPromoteDatabasePort,
)
from app.application.admin.users.action_service import (
    AdminUserActionDatabasePort,
    AdminUserActionService,
)
from app.composition.audio_storage import build_audio_storage_provider
from app.data_access.acl_permissions import AclPermissionRepository
from app.data_access.user_learning_settings import UserLearningSettingsRepository
from app.external_providers.exercise_texts import (
    build_exercise_text_generation_provider,
    build_exercise_text_tts_provider,
)
from app.storage.audio import AudioStorageProvider
from app.telegram_gateway import TelegramGateway
from app.time_utils import TimeService


class AdminServiceDatabasePort(
    AdminAuthDatabasePort,
    AdminAIUsageReadDatabasePort,
    AdminBillingReadDatabasePort,
    AdminDashboardDatabasePort,
    AdminSettingsDatabasePort,
    AdminDictionaryDatabasePort,
    AdminExerciseTextDatabasePort,
    AdminExerciseTextGenerationDatabasePort,
    AdminExerciseTextGenerationUsageDatabasePort,
    AdminExerciseTextTTSDatabasePort,
    AdminReadDatabasePort,
    AdminUserActionDatabasePort,
    AdminDictionaryActionDatabasePort,
    AdminUserDictionaryPromoteDatabasePort,
    AdminUserDictionaryBulkDatabasePort,
    Protocol,
):
    pass


@dataclass(frozen=True)
class AdminServiceDependencies:
    admin_auth_service: AdminAuthService
    admin_ai_usage_read_service: AdminAIUsageReadService
    admin_billing_read_service: AdminBillingReadService
    admin_dashboard_service: AdminDashboardService
    admin_bootstrap_service: AdminBootstrapService
    admin_settings_service: AdminSettingsService
    admin_dictionary_service: AdminDictionaryService
    admin_exercise_text_service: AdminExerciseTextService
    admin_exercise_text_generation_service: AdminExerciseTextGenerationService
    admin_exercise_text_tts_service: AdminExerciseTextTTSService
    admin_read_service: AdminReadService
    admin_user_action_service: AdminUserActionService
    admin_dictionary_action_service: AdminDictionaryActionService
    admin_user_dictionary_promote_action: AdminUserDictionaryPromoteAction
    admin_user_dictionary_bulk_action: AdminUserDictionaryBulkAction
    admin_entity_service: AdminEntityService
    audio_storage_provider: AudioStorageProvider


def build_admin_service_dependencies(
    db: AdminServiceDatabasePort,
    time_service: TimeService,
    telegram_gateway: AdminAuthTelegramGateway,
) -> AdminServiceDependencies:
    user_learning_settings_repo = getattr(db, "user_learning_settings", None) or UserLearningSettingsRepository(db)
    acl_permissions_repo = getattr(db, "acl_permissions", None) or AclPermissionRepository(db)
    admin_auth_service = AdminAuthService(db, time_service, telegram_gateway)
    admin_ai_usage_action_otp_verifier = AdminAIUsageActionOtpVerifier(admin_auth_service)
    admin_settings_action_otp_verifier = AdminSettingsActionOtpVerifier(admin_auth_service)
    admin_user_action_service = AdminUserActionService(db, time_service)
    admin_dictionary_action_service = AdminDictionaryActionService(db, time_service)
    audio_storage_provider = build_audio_storage_provider(db.settings)
    admin_user_dictionary_promote_action = AdminUserDictionaryPromoteAction(
        db,
        time_service,
        audio_storage_provider=audio_storage_provider,
    )
    admin_user_dictionary_bulk_action = AdminUserDictionaryBulkAction(
        db,
        time_service,
        admin_user_dictionary_promote_action,
    )
    return AdminServiceDependencies(
        admin_auth_service=admin_auth_service,
        admin_ai_usage_read_service=AdminAIUsageReadService(
            db,
            time_service,
            action_otp_verifier=admin_ai_usage_action_otp_verifier,
        ),
        admin_billing_read_service=AdminBillingReadService(db),
        admin_dashboard_service=AdminDashboardService(db, time_service),
        admin_bootstrap_service=AdminBootstrapService(db.settings, user_learning_settings_repo, acl_permissions_repo),
        admin_settings_service=AdminSettingsService(
            db,
            time_service,
            audio_storage_provider=audio_storage_provider,
            action_otp_verifier=admin_settings_action_otp_verifier,
        ),
        admin_dictionary_service=AdminDictionaryService(
            db,
            time_service,
            audio_storage_provider=audio_storage_provider,
        ),
        admin_exercise_text_service=AdminExerciseTextService(db, time_service),
        admin_exercise_text_generation_service=AdminExerciseTextGenerationService(
            db,
            time_service,
            provider_factory=build_exercise_text_generation_provider,
        ),
        admin_exercise_text_tts_service=AdminExerciseTextTTSService(
            db,
            time_service,
            provider_factory=build_exercise_text_tts_provider,
            audio_storage_provider=audio_storage_provider,
        ),
        admin_read_service=AdminReadService(db),
        admin_user_action_service=admin_user_action_service,
        admin_dictionary_action_service=admin_dictionary_action_service,
        admin_user_dictionary_promote_action=admin_user_dictionary_promote_action,
        admin_user_dictionary_bulk_action=admin_user_dictionary_bulk_action,
        admin_entity_service=AdminEntityService(
            user_action_service=admin_user_action_service,
            dictionary_action_service=admin_dictionary_action_service,
        ),
        audio_storage_provider=audio_storage_provider,
    )


def build_admin_telegram_gateway(settings: object) -> AdminAuthTelegramGateway:
    return TelegramGateway(getattr(settings, "bot_token", ""))


def configure_admin_runtime(service: Any, db: AdminServiceDatabasePort) -> None:
    service.admin_service_dependencies = build_admin_service_dependencies(
        db,
        service.time_service,
        build_admin_telegram_gateway(db.settings),
    )
