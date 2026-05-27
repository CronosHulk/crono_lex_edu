from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.composition.user_import_artifact_storage import (
    build_user_import_artifact_storage_provider,
)
from app.subscriptions.user_entitlements import UserEntitlementResolver
from app.user_import.runtime_settings import (
    DEFAULT_IMPORT_RUNTIME_SETTINGS,
    read_user_import_runtime_settings,
)
from app.user_import.services.bound_google_doc_sync_processor import (
    UserImportBoundGoogleDocSyncProcessor,
)
from app.user_import.services.candidate_filter_service import UserImportCandidateFilterService
from app.user_import.services.error_logging import log_user_import_pipeline_error
from app.user_import.services.intake_job_service import UserImportIntakeJobService
from app.user_import.services.intake_manual_bind_service import (
    UserImportIntakeManualBindService,
)
from app.user_import.services.intake_service import UserImportIntakeService
from app.user_import.services.validation_service import UserImportValidationService


def configure_user_import_intake_runtime(
    service: Any,
    db: Any,
    resolve_helper: Callable[[str], Any],
) -> None:
    from app.data_access.user_import_google_docs import UserImportGoogleDocRepository
    from app.data_access.user_profiles import UserProfileRepository
    user_import_google_docs_repo = getattr(db, "user_import_google_docs", None) or UserImportGoogleDocRepository(db)
    user_profiles_repo = getattr(db, "user_profiles", None) or UserProfileRepository(db)

    if getattr(service, "user_import_artifact_storage_provider", None) is None:
        service.user_import_artifact_storage_provider = (
            build_user_import_artifact_storage_provider(db.settings)
        )
    validation_service = UserImportValidationService(
        db,
        build_validation_provider=lambda settings, task_settings: resolve_helper("build_word_validation_provider")(
            settings, task_settings
        ),
    )
    max_import_entries_per_submission = _build_max_import_entries_per_submission(db)
    service.user_import_intake_job_service = UserImportIntakeJobService(
        db,
        max_import_entries_per_submission=max_import_entries_per_submission,
        build_import_snapshot=lambda **kwargs: resolve_helper("build_import_snapshot")(
            **kwargs
        ),
        artifact_storage_provider=service.user_import_artifact_storage_provider,
    )
    service.user_import_intake_manual_bind_service = UserImportIntakeManualBindService(
        db,
        user_import_google_docs_repo,
        user_profiles_repo,
        intake_job_service=service.user_import_intake_job_service,
        extract_google_doc_id=lambda value: resolve_helper("extract_google_doc_id")(value),
        build_google_doc_export_url=lambda value: resolve_helper("build_google_doc_export_url")(
            value
        ),
        fetch_google_doc_text=lambda value: resolve_helper("fetch_google_doc_text")(value),
        parse_user_vocabulary_text_result=lambda value: resolve_helper(
            "parse_user_vocabulary_text_result"
        )(
            value
        ),
        mask_google_doc_url=lambda value: resolve_helper("mask_google_doc_url")(value),
        build_invalid_import_notice=lambda locale, fragments: resolve_helper(
            "build_invalid_import_notice"
        )(
            locale,
            fragments,
        ),
        candidate_filter=UserImportCandidateFilterService(db),
        import_mode_for_user=_build_import_mode_for_user(db),
        max_import_entries_per_submission=max_import_entries_per_submission,
        validation_service=validation_service,
    )
    service.user_import_intake_service = UserImportIntakeService(
        db,
        intake_job_service=service.user_import_intake_job_service,
        manual_bind_service=service.user_import_intake_manual_bind_service,
    )
    service.user_import_bound_google_doc_sync_processor = UserImportBoundGoogleDocSyncProcessor(
        db,
        user_import_google_docs_repo,
        intake_job_service=service.user_import_intake_job_service,
        build_google_doc_export_url=lambda value: resolve_helper("build_google_doc_export_url")(
            value
        ),
        fetch_google_doc_text=lambda value: resolve_helper("fetch_google_doc_text")(value),
        parse_user_vocabulary_text_result=lambda value: resolve_helper(
            "parse_user_vocabulary_text_result"
        )(
            value
        ),
        sanitize_external_error_text=lambda value: resolve_helper("sanitize_external_error_text")(
            value
        ),
        candidate_filter=UserImportCandidateFilterService(db),
        import_mode_for_user=_build_import_mode_for_user(db),
        max_import_entries_per_submission=max_import_entries_per_submission,
        log_pipeline_error=_build_user_import_pipeline_error_logger(db),
        validation_service=validation_service,
    )


def _build_import_mode_for_user(db: Any) -> Callable[..., str | None]:
    entitlement_resolver = UserEntitlementResolver(db)

    def import_mode_for_user(user_uuid: str, *, current_time: Any) -> str | None:
        return entitlement_resolver.resolve_for_user_uuid(user_uuid, current_time=current_time).import_mode

    return import_mode_for_user


def _build_max_import_entries_per_submission(db: Any) -> Callable[[], int]:
    def max_import_entries_per_submission() -> int:
        try:
            runtime_settings = read_user_import_runtime_settings(db)
        except Exception:
            runtime_settings = DEFAULT_IMPORT_RUNTIME_SETTINGS
        return max(int(runtime_settings["max_import_entries_per_submission"]), 1)

    return max_import_entries_per_submission


def _build_user_import_pipeline_error_logger(db: Any) -> Callable[..., None]:
    def log_pipeline_error(**kwargs: Any) -> None:
        log_user_import_pipeline_error(db, **kwargs)

    return log_pipeline_error
