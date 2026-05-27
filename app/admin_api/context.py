from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Request

from app.application.admin.ai_usage.read_service import AdminAIUsageReadService
from app.application.admin.auth.auth_service import AdminAuthService
from app.application.admin.billing.read_service import AdminBillingReadService
from app.application.admin.bootstrap_service import AdminBootstrapService
from app.application.admin.dashboard.dashboard_service import AdminDashboardService
from app.application.admin.dictionary.action_service import AdminDictionaryActionService
from app.application.admin.dictionary.dictionary_service import AdminDictionaryService
from app.application.admin.dictionary.read_service import AdminDictionaryReadService
from app.application.admin.entity.entity_service import AdminEntityService
from app.application.admin.exercise_texts.exercise_text_service import AdminExerciseTextService
from app.application.admin.exercise_texts.generation_service import (
    AdminExerciseTextGenerationService,
)
from app.application.admin.exercise_texts.tts_service import AdminExerciseTextTTSService
from app.application.admin.imports.read_service import AdminImportReadService
from app.application.admin.logs.read_service import AdminLogReadService
from app.application.admin.read.read_service import AdminReadService
from app.application.admin.settings.settings_service import AdminSettingsService
from app.application.admin.user_dictionary.bulk import AdminUserDictionaryBulkAction
from app.application.admin.user_dictionary.promote import AdminUserDictionaryPromoteAction
from app.application.admin.user_dictionary.read_service import AdminUserDictionaryReadService
from app.application.admin.users.action_service import AdminUserActionService
from app.application.admin.users.read_service import AdminUserReadService
from app.storage.audio import AudioStorageProvider


@dataclass(frozen=True)
class AdminRouterContext:
    current_admin_user: Callable[[Request], dict]
    admin_ai_usage_read_service: Callable[[], AdminAIUsageReadService]
    admin_auth_service: Callable[[], AdminAuthService]
    admin_billing_read_service: Callable[[], AdminBillingReadService]
    admin_bootstrap_service: Callable[[], AdminBootstrapService]
    admin_dashboard_service: Callable[[], AdminDashboardService]
    admin_dictionary_action_service: Callable[[], AdminDictionaryActionService]
    admin_dictionary_read_service: Callable[[], AdminDictionaryReadService]
    admin_dictionary_service: Callable[[], AdminDictionaryService]
    admin_entity_service: Callable[[], AdminEntityService]
    admin_exercise_text_service: Callable[[], AdminExerciseTextService]
    admin_exercise_text_generation_service: Callable[[], AdminExerciseTextGenerationService]
    admin_exercise_text_tts_service: Callable[[], AdminExerciseTextTTSService]
    admin_import_read_service: Callable[[], AdminImportReadService]
    admin_log_read_service: Callable[[], AdminLogReadService]
    admin_read_service: Callable[[], AdminReadService]
    admin_settings_service: Callable[[], AdminSettingsService]
    admin_user_dictionary_bulk_action: Callable[[], AdminUserDictionaryBulkAction]
    admin_user_dictionary_promote_action: Callable[[], AdminUserDictionaryPromoteAction]
    admin_user_dictionary_read_service: Callable[[], AdminUserDictionaryReadService]
    admin_user_action_service: Callable[[], AdminUserActionService]
    admin_user_read_service: Callable[[], AdminUserReadService]
    audio_storage_provider: Callable[[], AudioStorageProvider]
