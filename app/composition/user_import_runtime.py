from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.application.scheduled_runtime.import_notification_service import (
    ClientImportNotificationService,
)
from app.application.scheduled_runtime.user_import_service import (
    UserImportScheduledRuntimeService,
)
from app.user_import.services.bound_google_doc_sync_service import (
    UserImportBoundGoogleDocSyncService,
)
from app.user_import.services.retry_schedule import build_user_import_next_retry_at
from app.user_import.services.runtime_service import UserImportRuntimeService
from app.user_import.services.task_error_context import build_user_import_task_error_context
from app.user_import.settings import USER_IMPORT_MAX_DOC_SYNCS_PER_RUN


def configure_user_import_runtime(
    service: Any,
    db: Any,
    resolve_helper: Callable[[str], Any],
) -> None:
    from app.data_access.user_import_google_docs import UserImportGoogleDocRepository
    user_import_google_docs_repo = getattr(db, "user_import_google_docs", None) or UserImportGoogleDocRepository(db)

    service.user_import_bound_google_doc_sync_service = UserImportBoundGoogleDocSyncService(
        db,
        user_import_google_docs_repo,
        service.user_import_bound_google_doc_sync_processor,
        build_task_error_context=build_user_import_task_error_context,
        build_next_retry_at=build_user_import_next_retry_at,
        max_doc_syncs_per_run=USER_IMPORT_MAX_DOC_SYNCS_PER_RUN,
        prepare_import_job_items=service.user_import_preparation_service.prepare_import_job_items,
    )
    service.user_import_runtime_service = UserImportRuntimeService(
        db,
        service.time_service,
        job_processing_service=service.user_import_job_processing_service,
        user_dictionary_build_service=service.user_dictionary_build_service,
        notification_service=service.user_import_notification_service,
        bound_google_doc_sync_service=service.user_import_bound_google_doc_sync_service,
        sync_provider_pricing_snapshots=lambda db, current_time: resolve_helper(
            "sync_due_provider_pricing_snapshots"
        )(db, current_time),
    )
    service.user_import_scheduled_runtime_service = UserImportScheduledRuntimeService(
        service.user_import_runtime_service,
        dispatch_lock=service.dispatch_lock,
    )
    service.client_import_notification_service = ClientImportNotificationService(
        service.user_import_scheduled_runtime_service,
        admin_restore_source=service.client_admin_restore_service,
        billing_notification_source=service.billing_notification_runtime_service,
    )
