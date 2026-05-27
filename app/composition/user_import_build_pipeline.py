from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, time, timedelta
from typing import Any, Protocol
from uuid import UUID

from app.composition.audio_storage import build_audio_storage_provider
from app.composition.user_import_artifact_storage import (
    build_user_import_artifact_storage_provider,
)
from app.subscriptions.plans import IMPORT_MODE_LOOKUP_ONLY
from app.subscriptions.user_entitlements import UserEntitlementResolver
from app.user_import.providers import WORD_DETAILS_TASK_KEY, read_user_import_provider_task_setting
from app.user_import.services.audio_builder import UserImportAudioBuilderService
from app.user_import.services.collecting_resolver import UserImportCollectingResolver
from app.user_import.services.job_processing_service import UserImportJobProcessingService
from app.user_import.services.job_task_result_service import UserImportJobTaskResultService
from app.user_import.services.notification_service import UserImportNotificationService
from app.user_import.services.preparation_service import UserImportPreparationService
from app.user_import.services.task_error_context import build_user_import_task_error_context
from app.user_import.services.user_dictionary_build_service import UserDictionaryBuildService
from app.user_import.settings import USER_IMPORT_MAX_JOBS_PER_RUN


class UserImportPreparationUserDictionaryQuotaPort(Protocol):
    def count_entries_created_by_user_since(self, user_uuid: UUID, *, since: datetime) -> int: ...


class UserImportPreparationAccessPolicyAdapter:
    def __init__(self, db: Any) -> None:
        from app.data_access.user_dictionary import UserDictionaryRepository
        self.db = db
        self.entitlement_resolver = UserEntitlementResolver(db)
        self.user_dictionary_repo = getattr(db, "user_dictionary", None) or UserDictionaryRepository(db)

    def user_uuid_for_telegram_user(self, telegram_user_id: int) -> UUID | str | None:
        return self.entitlement_resolver.user_uuid_for_telegram_user(telegram_user_id)

    def is_lookup_only_import(self, user_uuid: UUID, *, current_time: datetime) -> bool:
        return (
            self.entitlement_resolver.resolve_for_user_uuid(
                user_uuid,
                current_time=current_time,
            ).import_mode
            == IMPORT_MODE_LOOKUP_ONLY
        )

    def can_create_new_user_dictionary_entry(self, user_uuid: UUID | None, *, current_time: datetime) -> bool:
        if user_uuid is None:
            return True
        subscription = self.entitlement_resolver.subscription_for_user_uuid(user_uuid)
        if subscription is None:
            return True
        cap = self.entitlement_resolver.resolve_subscription(
            subscription,
            current_time=current_time,
        ).new_import_words_per_week
        if cap is None:
            return True
        if cap <= 0:
            return False
        return self.user_dictionary_repo.count_entries_created_by_user_since(
            user_uuid,
            since=_monday_week_start(current_time),
        ) < cap


def _monday_week_start(current_time: datetime) -> datetime:
    week_start_date = current_time.date() - timedelta(days=current_time.weekday())
    return datetime.combine(week_start_date, time.min, tzinfo=current_time.tzinfo)


def configure_user_import_build_pipeline_runtime(
    service: Any,
    db: Any,
    resolve_helper: Callable[[str], Any],
) -> None:
    audio_storage_provider = build_audio_storage_provider(db.settings)
    if getattr(service, "user_import_artifact_storage_provider", None) is None:
        service.user_import_artifact_storage_provider = (
            build_user_import_artifact_storage_provider(db.settings)
        )
    service.user_import_preparation_service = UserImportPreparationService(
        db,
        UserImportPreparationAccessPolicyAdapter(db),
    )
    service.user_import_collecting_resolver = UserImportCollectingResolver(
        db.settings,
        resolve_pending_import_word=lambda **kwargs: resolve_helper(
            "resolve_pending_import_word"
        )(**kwargs),
        artifact_storage_provider=service.user_import_artifact_storage_provider,
        build_word_details_provider=lambda settings: resolve_helper("build_word_details_provider")(
            settings,
            read_user_import_provider_task_setting(db, WORD_DETAILS_TASK_KEY),
        ),
        language_level_id_by_title=lambda: {
            str(level["title"]): int(level["id"])
            for level in service.reference.language_levels()
            if level.get("title") and level.get("id") is not None
        },
    )
    service.user_import_job_task_result_service = UserImportJobTaskResultService(db)
    service.user_import_job_processing_service = UserImportJobProcessingService(
        db,
        prepare_import_job_items=service.user_import_preparation_service.prepare_import_job_items,
        job_task_result_service=service.user_import_job_task_result_service,
        build_task_error_context=build_user_import_task_error_context,
        sanitize_external_error_text=lambda value: resolve_helper("sanitize_external_error_text")(
            value
        ),
    )
    from app.data_access.user_profiles import UserProfileRepository
    user_profiles_repo = getattr(db, "user_profiles", None) or UserProfileRepository(db)

    service.user_import_notification_service = UserImportNotificationService(
        db,
        user_profiles_repo,
        build_user_import_publish_summary_screen=lambda telegram_user_id,
        locale,
        job_id,
        priority_count: service.user_import_summary_service.build_user_import_publish_summary_screen_for_user(
            telegram_user_id=telegram_user_id,
            locale=locale,
            job_id=job_id,
            priority_count=priority_count,
        ),
        build_user_import_summary_screen=lambda **kwargs: service.user_import_summary_service.build_user_import_summary_screen(
            **kwargs
        ),
    )
    service.user_import_audio_builder_service = UserImportAudioBuilderService(
        db,
        build_audio_provider=lambda settings, task_settings: resolve_helper(
            "build_word_audio_provider"
        )(settings, task_settings),
    )
    service.user_dictionary_build_service = UserDictionaryBuildService(
        db,
        audio_storage_provider=audio_storage_provider,
        user_audio_root=getattr(db.settings, "app_user_import_audio_dir"),
        resolver=service.user_import_collecting_resolver,
        audio_builder=service.user_import_audio_builder_service.build_audio,
        embedding_builder=lambda **kwargs: resolve_helper("ensure_user_import_embedding")(
            **kwargs
        ),
        error_masker=lambda value: resolve_helper("mask_provider_error_for_user")(value),
        max_jobs_per_run=USER_IMPORT_MAX_JOBS_PER_RUN,
    )
