from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.application.client_web.import_errors import (
    ClientWebImportValidationError,
)
from app.application.client_web.import_events import ClientWebImportEvent
from app.helpers.external_error_text import format_external_error
from app.subscriptions.plans import IMPORT_MODE_LOOKUP_ONLY
from app.subscriptions.user_entitlements import read_user_uuid
from app.user_import.runtime_settings import (
    UserImportRuntimeSettingsValidationError,
    read_user_import_runtime_settings,
)
from app.user_import.services.google_doc_progress import (
    progress_checkpoint_for_scope,
)


def _noop_import_event_publisher(_event: ClientWebImportEvent) -> None:
    return None


def _noop_processing_error_logger(_detail: str, *, import_job_id: int) -> None:
    return None


class ClientWebImportProcessingUserImportJobsPort(Protocol):
    def mark_processing(self, job_id: int, current_time: datetime) -> Any: ...

    def complete(
        self,
        job_id: int,
        *,
        status: str,
        current_time: datetime,
        last_error: str | None = None,
    ) -> Any: ...

    def append_items(
        self,
        job_id: int,
        telegram_user_id: int,
        items: list[dict[str, Any]],
        current_time: datetime,
    ) -> Any: ...

    def get_job_for_user(self, telegram_user_id: int, job_id: int) -> dict[str, Any] | None: ...


class ClientWebImportProcessingGoogleDocsPort(Protocol):
    def set_binding(self, telegram_user_id: int, doc_id: str, current_time: datetime) -> Any: ...

    def mark_sync_success(self, telegram_user_id: int, *, current_time: datetime) -> Any: ...

    def mark_progress(
        self,
        telegram_user_id: int,
        doc_id: str,
        *,
        current_time: datetime,
        last_processed_line: Any,
        last_processed_line_hash: Any,
        last_processed_lookup_word: Any,
    ) -> Any: ...


class ClientWebImportProcessingAppSettingsPort(Protocol):
    def get_value(self, key: str) -> Any: ...


class ClientWebImportProcessingDatabasePort(Protocol):
    user_import_jobs: ClientWebImportProcessingUserImportJobsPort
    user_import_google_docs: ClientWebImportProcessingGoogleDocsPort
    app_settings: ClientWebImportProcessingAppSettingsPort


class ClientWebImportProcessingPreparationServicePort(Protocol):
    def prepare_import_job_items(
        self,
        job: dict[str, Any],
        current_time: datetime,
        *,
        task_log_id: int | None,
    ) -> Any: ...


class ClientWebImportProcessingScheduledRuntimeServicePort(Protocol):
    def process_user_import_attribute_queue_now(self, telegram_user_id: int, current_time: datetime) -> Any: ...


class ClientWebImportProcessingRuntime(Protocol):
    db: ClientWebImportProcessingDatabasePort
    user_import_preparation_service: ClientWebImportProcessingPreparationServicePort
    user_import_scheduled_runtime_service: ClientWebImportProcessingScheduledRuntimeServicePort


class ClientWebImportProcessingValidationServicePort(Protocol):
    def validate_words(self, candidates: list[Any]) -> Any: ...

    def record_usage(
        self,
        validation_result: Any,
        *,
        task_scope: str,
        actor_user_uuid: str,
        source_type: str | None,
        source_identifier: str | None,
        import_job_id: int | None,
        task_log_id: int | None,
        batch_key: str,
        current_time: datetime,
    ) -> None: ...


class ClientWebImportProcessingCandidateFilterPort(Protocol):
    def filter_already_assigned_words(
        self,
        parsed_words: list[Any],
        *,
        user_uuid: str | None,
    ) -> Any: ...


class ClientWebImportProcessingImportModeResolver(Protocol):
    def __call__(self, user_uuid: str | None, *, current_time: datetime) -> str: ...


class ClientWebImportProcessingErrorLogger(Protocol):
    def __call__(self, detail: str, *, import_job_id: int) -> None: ...


class ClientWebImportProcessingService:
    def __init__(
        self,
        learning_service: ClientWebImportProcessingRuntime,
        *,
        validation_service: ClientWebImportProcessingValidationServicePort,
        import_mode_for_user: ClientWebImportProcessingImportModeResolver,
        candidate_filter: ClientWebImportProcessingCandidateFilterPort,
        error_logger: ClientWebImportProcessingErrorLogger | None = None,
        event_publisher: Callable[[ClientWebImportEvent], None] | None = None,
    ) -> None:
        self.learning_service = learning_service
        self.db: ClientWebImportProcessingDatabasePort = learning_service.db
        self.validation_service = validation_service
        self.import_mode_for_user = import_mode_for_user
        self.candidate_filter = candidate_filter
        self.error_logger = error_logger or _noop_processing_error_logger
        self.event_publisher = event_publisher or _noop_import_event_publisher

    def process_submitted_import_job(
        self,
        *,
        user: dict[str, Any],
        job_id: int,
        source: dict[str, str],
        parsed_words: list[Any],
        invalid_fragments: list[str],
        google_doc_scope: Any,
        current_time: datetime,
    ) -> None:
        telegram_user_id = int(user["telegram_user_id"])
        self.db.user_import_jobs.mark_processing(job_id, current_time)
        self._publish_import_event(
            telegram_user_id=telegram_user_id,
            job_id=job_id,
            event="processing",
            status="processing",
        )
        try:
            import_mode = self._import_mode_for_user(user, current_time=current_time)
            user_uuid = read_user_uuid(user)
            candidate_filter_result = self.candidate_filter.filter_already_assigned_words(
                parsed_words,
                user_uuid=user_uuid,
            )
            existing_items = self._items_from_existing_words(candidate_filter_result.skipped_existing_words)
            self._append_and_prepare_items(
                job_id=job_id,
                telegram_user_id=telegram_user_id,
                items=existing_items,
                current_time=current_time,
            )
            self._publish_import_event(
                telegram_user_id=telegram_user_id,
                job_id=job_id,
                event="items_changed",
                item_count=len(existing_items),
            )
            parsed_words = candidate_filter_result.eligible_words
            if import_mode == IMPORT_MODE_LOOKUP_ONLY:
                batch_items = self._items_from_parsed_words(parsed_words)
                self._append_and_prepare_items(
                    job_id=job_id,
                    telegram_user_id=telegram_user_id,
                    items=batch_items,
                    current_time=current_time,
                )
                self._publish_import_event(
                    telegram_user_id=telegram_user_id,
                    job_id=job_id,
                    event="items_changed",
                    item_count=len(batch_items),
                )
            else:
                for candidate_batch in self._candidate_batches(parsed_words):
                    validation_outcome = self.validation_service.validate_words(candidate_batch)
                    batch_items = self._items_from_validation_outcome(validation_outcome)
                    self._append_and_prepare_items(
                        job_id=job_id,
                        telegram_user_id=telegram_user_id,
                        items=batch_items,
                        current_time=current_time,
                    )
                    self._publish_import_event(
                        telegram_user_id=telegram_user_id,
                        job_id=job_id,
                        event="items_changed",
                        item_count=len(batch_items),
                    )
                    self.validation_service.record_usage(
                        validation_outcome.validation_result,
                        task_scope="client_web",
                        actor_user_uuid=str(user.get("user_id") or ""),
                        source_type=source.get("source_type"),
                        source_identifier=source.get("source_identifier"),
                        import_job_id=job_id,
                        task_log_id=None,
                        batch_key=f"import_job:{job_id}:word_validation",
                        current_time=current_time,
                    )
            rejected_items = [
                {
                    "raw_value": fragment,
                    "lookup_word": fragment,
                    "status": "rejected",
                    "error_text": "Item does not match the import format or safety policy",
                }
                for fragment in invalid_fragments
            ]
            self._append_and_prepare_items(
                job_id=job_id,
                telegram_user_id=telegram_user_id,
                items=rejected_items,
                current_time=current_time,
            )
            self._publish_import_event(
                telegram_user_id=telegram_user_id,
                job_id=job_id,
                event="items_changed",
                item_count=len(rejected_items),
            )
            self.db.user_import_jobs.complete(job_id, status="completed", current_time=current_time)
            if source["source_type"] == "client_web_google_doc":
                self.db.user_import_google_docs.set_binding(telegram_user_id, source["source_identifier"], current_time)
                self._mark_google_doc_progress(
                    telegram_user_id=telegram_user_id,
                    doc_id=source["source_identifier"],
                    scope=google_doc_scope,
                    existing_lookup_words={
                        *(
                            str(getattr(item, "lookup_word", "") or "")
                            for item in candidate_filter_result.skipped_existing_words
                        ),
                        *getattr(google_doc_scope, "skipped_lookup_words", []),
                    },
                    current_time=current_time,
                )
                self.db.user_import_google_docs.mark_sync_success(telegram_user_id, current_time=current_time)
                if self._should_enrich_google_doc_import_immediately():
                    self._process_attribute_queue_now(telegram_user_id, current_time)
            self._publish_import_event(
                telegram_user_id=telegram_user_id,
                job_id=job_id,
                event="completed",
                status="completed",
            )
        except Exception as error:
            detail = format_external_error(error, fallback="Client web import processing failed")
            self.error_logger(detail, import_job_id=job_id)
            self.db.user_import_jobs.complete(job_id, status="failed", current_time=current_time, last_error=detail)
            self._publish_import_event(
                telegram_user_id=telegram_user_id,
                job_id=job_id,
                event="failed",
                status="failed",
            )

    def _should_enrich_google_doc_import_immediately(self) -> bool:
        runtime_settings = self._runtime_settings()
        return bool(runtime_settings["enrich_after_google_doc_import_enabled"])

    def _process_attribute_queue_now(self, telegram_user_id: int, current_time: datetime) -> None:
        self.learning_service.user_import_scheduled_runtime_service.process_user_import_attribute_queue_now(
            telegram_user_id,
            current_time,
        )

    def _publish_import_event(
        self,
        *,
        telegram_user_id: int,
        job_id: int,
        event: str,
        status: str | None = None,
        item_count: int | None = None,
    ) -> None:
        if event == "items_changed" and not item_count:
            return
        self.event_publisher(
            ClientWebImportEvent(
                telegram_user_id=telegram_user_id,
                job_id=job_id,
                event=event,
                status=status,
                item_count=item_count,
            ),
        )

    def _candidate_batches(self, parsed_words: list[Any]) -> list[list[Any]]:
        runtime_settings = self._runtime_settings()
        batch_size = max(int(runtime_settings["validation_batch_size"]), 1)
        return [parsed_words[index : index + batch_size] for index in range(0, len(parsed_words), batch_size)]

    def _runtime_settings(self) -> dict[str, Any]:
        try:
            return read_user_import_runtime_settings(self.db)
        except UserImportRuntimeSettingsValidationError as error:
            raise ClientWebImportValidationError(str(error)) from error

    def _import_mode_for_user(self, user: dict[str, Any], *, current_time: datetime) -> str:
        user_uuid = read_user_uuid(user)
        return self.import_mode_for_user(user_uuid, current_time=current_time)

    def _items_from_parsed_words(self, parsed_words: list[Any]) -> list[dict[str, Any]]:
        return [
            {
                "raw_value": item.raw_value,
                "lookup_word": item.lookup_word,
                "translation_hint": item.translation_hint,
                "status": "pending",
            }
            for item in parsed_words
        ]

    def _items_from_existing_words(self, parsed_words: list[Any]) -> list[dict[str, Any]]:
        return [
            {
                "raw_value": getattr(item, "raw_value", ""),
                "lookup_word": getattr(item, "lookup_word", ""),
                "translation_hint": getattr(item, "translation_hint", None),
                "status": "found_existing",
            }
            for item in parsed_words
        ]

    def _items_from_validation_outcome(self, validation_outcome: Any) -> list[dict[str, Any]]:
        valid_items = [
            {
                "raw_value": item.raw_value,
                "lookup_word": item.lookup_word,
                "translation_hint": item.translation_hint,
                "validated_lookup_word": item.validated_lookup_word,
                "validated_part_of_speech": item.validated_part_of_speech,
                "validated_translation_uk": item.validated_translation_uk,
                "validated_translation_ru": item.validated_translation_ru,
                "validated_translation_pl": item.validated_translation_pl,
                "status": "pending",
            }
            for item in validation_outcome.valid_words
        ]
        return [*valid_items, *validation_outcome.rejected_items]

    def _append_and_prepare_items(
        self,
        *,
        job_id: int,
        telegram_user_id: int,
        items: list[dict[str, Any]],
        current_time: datetime,
    ) -> None:
        if not items:
            return
        self.db.user_import_jobs.append_items(
            job_id,
            telegram_user_id,
            items,
            current_time,
        )
        job = self.db.user_import_jobs.get_job_for_user(telegram_user_id, job_id)
        if job is None:
            return
        self.learning_service.user_import_preparation_service.prepare_import_job_items(
            job,
            current_time,
            task_log_id=None,
        )

    def _mark_google_doc_progress(
        self,
        *,
        telegram_user_id: int,
        doc_id: str,
        scope: Any,
        existing_lookup_words: set[str] | None = None,
        current_time: datetime,
    ) -> None:
        if scope is None:
            return
        checkpoint = progress_checkpoint_for_scope(
            scope,
            existing_lookup_words=existing_lookup_words or set(),
            max_new_words=max(len(scope.parsed_words), 1),
        )
        self.db.user_import_google_docs.mark_progress(
            telegram_user_id,
            doc_id,
            current_time=current_time,
            last_processed_line=checkpoint["last_processed_line"],
            last_processed_line_hash=checkpoint["last_processed_line_hash"],
            last_processed_lookup_word=checkpoint["last_processed_lookup_word"],
        )
