from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, Protocol

from app.contracts import ImportDispatchNotificationModel
from app.time_utils import TimeService
from app.user_import.runtime_settings import read_user_import_runtime_settings
from app.user_import.services.bound_google_doc_sync_service import (
    UserImportBoundGoogleDocSyncService,
)
from app.user_import.services.job_processing_service import UserImportJobProcessingService
from app.user_import.services.notification_service import UserImportNotificationService
from app.user_import.services.user_dictionary_build_service import UserDictionaryBuildService
from app.user_import.settings import (
    USER_IMPORT_AUDIO_SCHEDULE_STATE_KEY,
    USER_IMPORT_DETAILS_SCHEDULE_STATE_KEY,
    USER_IMPORT_MAX_JOBS_PER_RUN,
    USER_IMPORT_PROCESSING_CLAIM_MINUTES,
)


class UserImportRuntimeJobsPort(Protocol):
    def claim_queued(
        self,
        *,
        current_time: datetime,
        claimed_until: datetime,
        limit: int | None = None,
    ) -> list[dict[str, Any]]: ...


class UserImportRuntimeStatePort(Protocol):
    def get(self, key: str) -> dict[str, Any] | None: ...

    def set(
        self,
        key: str,
        value_json: dict[str, Any],
        current_time: datetime,
    ) -> None: ...


class UserImportRuntimeDatabasePort(Protocol):
    @property
    def user_import_jobs(self) -> UserImportRuntimeJobsPort: ...

    @property
    def app_runtime_state(self) -> UserImportRuntimeStatePort: ...


SyncProviderPricingSnapshots = Callable[[Any, datetime], dict[str, Any]]


class UserImportRuntimeService:
    def __init__(
        self,
        db: UserImportRuntimeDatabasePort,
        time_service: TimeService,
        *,
        job_processing_service: UserImportJobProcessingService,
        user_dictionary_build_service: UserDictionaryBuildService,
        notification_service: UserImportNotificationService,
        bound_google_doc_sync_service: UserImportBoundGoogleDocSyncService,
        sync_provider_pricing_snapshots: SyncProviderPricingSnapshots,
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.job_processing_service = job_processing_service
        self.user_dictionary_build_service = user_dictionary_build_service
        self.notification_service = notification_service
        self.bound_google_doc_sync_service = bound_google_doc_sync_service
        self.sync_provider_pricing_snapshots = sync_provider_pricing_snapshots

    def process_due_user_vocabulary_imports(self) -> list[ImportDispatchNotificationModel]:
        return self.process_due_user_vocabulary_imports_at(
            current_time=self.time_service.now(),
            emit_notifications=True,
            include_bound_sync=False,
        )

    def process_due_user_import_embeddings_now(self) -> dict[str, int]:
        return self.user_dictionary_build_service.process_due_embedding_builds(
            current_time=self.time_service.now(),
            force=False,
        )

    def process_user_import_attribute_queue_now(self, current_time: datetime) -> None:
        self.user_dictionary_build_service.process_due_details_builds(
            current_time=current_time,
            force=True,
        )

    def process_due_post_upgrade_rescans(self) -> list[ImportDispatchNotificationModel]:
        current_time = self.time_service.now()
        claimed_until = current_time + timedelta(minutes=USER_IMPORT_PROCESSING_CLAIM_MINUTES)
        self.bound_google_doc_sync_service.enqueue_post_upgrade_rescans(current_time, claimed_until)
        return []

    def process_due_bound_google_doc_syncs(self) -> list[ImportDispatchNotificationModel]:
        current_time = self.time_service.now()
        claimed_until = current_time + timedelta(minutes=USER_IMPORT_PROCESSING_CLAIM_MINUTES)
        self.bound_google_doc_sync_service.enqueue_due_bound_google_doc_imports(
            current_time, claimed_until
        )
        return []

    def process_due_import_scheduler_tick(self) -> list[ImportDispatchNotificationModel]:
        current_time = self.time_service.now()
        claimed_until = current_time + timedelta(minutes=USER_IMPORT_PROCESSING_CLAIM_MINUTES)
        self.bound_google_doc_sync_service.enqueue_post_upgrade_rescans(current_time, claimed_until)
        self.bound_google_doc_sync_service.enqueue_due_bound_google_doc_imports(
            current_time, claimed_until
        )
        return self.process_due_user_vocabulary_imports_at(
            current_time=current_time,
            emit_notifications=True,
            include_bound_sync=False,
            dedupe_scheduled_details=True,
        )

    def process_due_user_vocabulary_imports_at(
        self,
        *,
        current_time: datetime,
        emit_notifications: bool,
        include_bound_sync: bool,
        dedupe_scheduled_details: bool = False,
    ) -> list[ImportDispatchNotificationModel]:
        claimed_until = current_time + timedelta(minutes=USER_IMPORT_PROCESSING_CLAIM_MINUTES)
        notifications: list[ImportDispatchNotificationModel] = []
        runtime_settings = read_user_import_runtime_settings(self.db)
        enrich_after_google_doc_import_enabled = bool(
            runtime_settings["enrich_after_google_doc_import_enabled"]
        )
        self.sync_provider_pricing_snapshots(self.db, current_time)
        wordnik_quota = {"requests_used": 0, "last_request_at": None, "cooldown_until": None}
        wordnik_budget = 0

        details_phase_should_report = self.user_dictionary_build_service.should_run_details_phase(
            current_time
        )
        details_phase_can_run = (
            self._claim_scheduled_details_run(current_time)
            if dedupe_scheduled_details and details_phase_should_report
            else True
        )
        user_details_summary = {"queued_for_audio_count": 0, "details_failed_count": 0}
        if details_phase_can_run:
            user_details_summary = self.user_dictionary_build_service.process_due_details_builds(
                current_time=current_time,
            )
        user_details_summary["phase_ran"] = details_phase_should_report and details_phase_can_run
        if include_bound_sync:
            self.bound_google_doc_sync_service.enqueue_due_bound_google_doc_imports(
                current_time, claimed_until
            )

        for job in self.db.user_import_jobs.claim_queued(
            current_time=current_time,
            claimed_until=claimed_until,
            limit=USER_IMPORT_MAX_JOBS_PER_RUN,
        ):
            wordnik_quota, wordnik_budget = self.job_processing_service.process_claimed_job(
                job,
                current_time=current_time,
                wordnik_quota=wordnik_quota,
                wordnik_budget=wordnik_budget,
                wordnik_hourly_limit=0,
            )

        if enrich_after_google_doc_import_enabled:
            self.user_dictionary_build_service.process_due_details_builds(
                current_time=current_time,
                force=True,
            )
        audio_phase_should_report = self.user_dictionary_build_service.should_run_audio_phase(
            current_time
        )
        audio_phase_can_run = (
            self._claim_scheduled_phase_run(
                USER_IMPORT_AUDIO_SCHEDULE_STATE_KEY,
                current_time,
                hour=int(runtime_settings["audio_build_hour"]),
                weekdays=runtime_settings.get("audio_build_weekdays"),
            )
            if dedupe_scheduled_details and audio_phase_should_report
            else True
        )
        audio_summary = {
            "ready_for_rotation_count": 0,
            "queued_for_embedding_count": 0,
            "audio_failed_count": 0,
        }
        if audio_phase_can_run:
            audio_summary = self.user_dictionary_build_service.process_due_audio_builds(
                current_time=current_time,
            )
        audio_phase_ran = audio_phase_should_report and audio_phase_can_run
        if emit_notifications:
            notifications.extend(
                self.notification_service.dispatch_admin_details_completion_notifications(
                    user_details_summary, current_time
                )
            )
            notifications.extend(
                self.notification_service.dispatch_due_user_import_publish_notifications(
                    current_time
                )
            )
            if audio_phase_ran:
                notifications.extend(
                    self.notification_service.dispatch_admin_audio_completion_notifications(
                        audio_summary
                    )
                )
            notifications.extend(
                self.notification_service.dispatch_due_user_import_summary_notifications(
                    current_time
                )
            )
        return notifications

    def _claim_scheduled_details_run(self, current_time: datetime) -> bool:
        runtime_settings = read_user_import_runtime_settings(self.db)
        return self._claim_scheduled_phase_run(
            USER_IMPORT_DETAILS_SCHEDULE_STATE_KEY,
            current_time,
            hour=int(runtime_settings["attribute_build_hour"]),
            weekdays=runtime_settings.get("attribute_build_weekdays"),
        )

    def _claim_scheduled_phase_run(
        self,
        state_key: str,
        current_time: datetime,
        *,
        hour: int,
        weekdays: object,
    ) -> bool:
        schedule_key = ":".join(
            [
                current_time.date().isoformat(),
                str(hour),
                ",".join(str(value) for value in weekdays) if isinstance(weekdays, list) else "all",
            ]
        )
        state_row = self.db.app_runtime_state.get(state_key)
        state = dict(state_row.get("value_json") or {}) if state_row is not None else {}
        if state.get("last_schedule_key") == schedule_key:
            return False
        self.db.app_runtime_state.set(
            state_key,
            value_json={
                "last_schedule_key": schedule_key,
                "last_run_at": current_time.isoformat(),
            },
            current_time=current_time,
        )
        return True
