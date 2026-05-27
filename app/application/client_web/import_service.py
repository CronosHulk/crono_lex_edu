from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.application.client_web.import_errors import (
    ClientWebImportValidationError,
)
from app.application.client_web.import_sources import (
    GoogleDocTextFetcher,
    read_client_web_import_source,
)
from app.application.client_web.import_statuses import (
    IMPORT_RESULT_PAGE_SIZE,
)
from app.domain.user_import.text_parser import parse_user_vocabulary_text_result
from app.storage.user_import_artifacts import UserImportArtifactStorageProvider
from app.user_import.runtime_settings import (
    UserImportRuntimeSettingsValidationError,
    read_user_import_runtime_settings,
)
from app.user_import.services.google_doc_progress import (
    parse_google_doc_since_progress,
)


class ClientWebImportTimeService(Protocol):
    def now(self) -> datetime: ...


class ClientWebImportUserImportJobsPort(Protocol):
    def create_job(
        self,
        *,
        telegram_user_id: int,
        task_log_id: int | None,
        source_type: str,
        source_identifier: str,
        storage_path: str,
        items: list[dict[str, Any]],
        current_time: datetime,
    ) -> dict[str, Any]: ...

    def get_job_for_user(self, telegram_user_id: int, job_id: int) -> dict[str, Any] | None: ...


class ClientWebImportGoogleDocsPort(Protocol):
    def get_progress(self, telegram_user_id: int, doc_id: str) -> Any: ...

    def clear_binding(self, telegram_user_id: int, current_time: datetime) -> Any: ...


class ClientWebImportAppSettingsPort(Protocol):
    def get_value(self, key: str) -> Any: ...


class ClientWebImportDatabasePort(Protocol):
    user_import_jobs: ClientWebImportUserImportJobsPort
    user_import_google_docs: ClientWebImportGoogleDocsPort
    app_settings: ClientWebImportAppSettingsPort


class ClientWebImportRuntime(Protocol):
    db: ClientWebImportDatabasePort
    time_service: ClientWebImportTimeService


class ClientWebImportProcessingServicePort(Protocol):
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
    ) -> None: ...


class ClientWebImportResultsServicePort(Protocol):
    def list_results(
        self,
        user: dict[str, Any],
        *,
        job_id: int,
        page: int,
        page_size: int,
        status_category: str = "all",
    ) -> dict[str, Any]: ...

    def ensure_job_for_user(self, user: dict[str, Any], job_id: int) -> None: ...

    def list_user_results(
        self,
        user: dict[str, Any],
        *,
        page: int,
        page_size: int,
        status_category: str = "all",
    ) -> dict[str, Any]: ...

    def serialize_job(self, job: dict[str, Any]) -> dict[str, Any]: ...


class ClientWebImportTaskRunner(Protocol):
    def add_task(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any: ...


class ClientWebImportService:
    def __init__(
        self,
        learning_service: ClientWebImportRuntime,
        *,
        results_service: ClientWebImportResultsServicePort,
        processing_service: ClientWebImportProcessingServicePort,
        artifact_storage_provider: UserImportArtifactStorageProvider,
        google_doc_text_fetcher: GoogleDocTextFetcher | None = None,
    ) -> None:
        self.learning_service = learning_service
        self.db: ClientWebImportDatabasePort = learning_service.db
        self.google_doc_text_fetcher = google_doc_text_fetcher
        self.results_service = results_service
        self.processing_service = processing_service
        self.artifact_storage_provider = artifact_storage_provider

    def submit_import(
        self,
        user: dict[str, Any],
        *,
        source_url: str | None,
        text_content: str | None,
        file_name: str | None,
        background_tasks: ClientWebImportTaskRunner | None = None,
    ) -> dict[str, Any]:
        current_time = self.learning_service.time_service.now()
        source = read_client_web_import_source(
            source_url=source_url,
            text_content=text_content,
            file_name=file_name,
            google_doc_text_fetcher=self.google_doc_text_fetcher,
        )
        telegram_user_id = int(user["telegram_user_id"])
        google_doc_scope = None
        if source["source_type"] == "client_web_google_doc":
            progress = self.db.user_import_google_docs.get_progress(telegram_user_id, source["source_identifier"])
            max_import_entries = self._max_import_entries_per_submission()
            google_doc_scope = parse_google_doc_since_progress(
                source["text"],
                progress,
                parse_user_vocabulary_text_result,
                max_parsed_words=max_import_entries,
            )
            parse_result = google_doc_scope.parse_result
        else:
            parse_result = parse_user_vocabulary_text_result(
                source["text"],
                max_words=self._max_import_entries_per_submission(),
            )
        if not parse_result.parsed_words and not parse_result.invalid_fragments and source["source_type"] != "client_web_google_doc":
            raise ClientWebImportValidationError("Import source does not contain supported words or phrases")

        storage_path = self._write_snapshot(
            telegram_user_id=telegram_user_id,
            source=source,
            valid_items=[],
            rejected_items=[],
            current_time=current_time,
        )
        job = self.db.user_import_jobs.create_job(
            telegram_user_id=telegram_user_id,
            task_log_id=None,
            source_type=source["source_type"],
            source_identifier=source["source_identifier"],
            storage_path=str(storage_path),
            items=[],
            current_time=current_time,
        )
        job_id = int(job["id"])
        process_kwargs = {
            "user": dict(user),
            "job_id": job_id,
            "source": dict(source),
            "parsed_words": list(parse_result.parsed_words),
            "invalid_fragments": list(parse_result.invalid_fragments),
            "google_doc_scope": google_doc_scope,
            "current_time": current_time,
        }
        if background_tasks is None:
            self.processing_service.process_submitted_import_job(**process_kwargs)
        else:
            background_tasks.add_task(self.processing_service.process_submitted_import_job, **process_kwargs)
        refreshed_job = self.db.user_import_jobs.get_job_for_user(telegram_user_id, job_id) or job
        return {
            "job": self.results_service.serialize_job(refreshed_job),
            "results": self.results_service.list_results(
                user,
                job_id=job_id,
                page=1,
                page_size=IMPORT_RESULT_PAGE_SIZE,
                status_category="all",
            ),
        }

    def _max_import_entries_per_submission(self) -> int:
        runtime_settings = self._runtime_settings()
        return max(int(runtime_settings["max_import_entries_per_submission"]), 1)

    def _runtime_settings(self) -> dict[str, Any]:
        try:
            return read_user_import_runtime_settings(self.db)
        except UserImportRuntimeSettingsValidationError as error:
            raise ClientWebImportValidationError(str(error)) from error

    def clear_google_doc_binding(self, user: dict[str, Any]) -> dict[str, Any]:
        current_time = self.learning_service.time_service.now()
        self.db.user_import_google_docs.clear_binding(int(user["telegram_user_id"]), current_time)
        return {"status": "ok"}

    def list_results(
        self,
        user: dict[str, Any],
        *,
        job_id: int,
        page: int,
        page_size: int,
        status_category: str = "all",
    ) -> dict[str, Any]:
        return self.results_service.list_results(
            user,
            job_id=job_id,
            page=page,
            page_size=page_size,
            status_category=status_category,
        )

    def ensure_job_for_user(self, user: dict[str, Any], job_id: int) -> None:
        self.results_service.ensure_job_for_user(user, job_id)

    def list_user_results(
        self,
        user: dict[str, Any],
        *,
        page: int,
        page_size: int,
        status_category: str = "all",
    ) -> dict[str, Any]:
        return self.results_service.list_user_results(
            user,
            page=page,
            page_size=page_size,
            status_category=status_category,
        )

    def _write_snapshot(
        self,
        *,
        telegram_user_id: int,
        source: dict[str, str],
        valid_items: list[dict[str, str]],
        rejected_items: list[dict[str, str]],
        current_time: datetime,
    ) -> str:
        return self.artifact_storage_provider.write_json_snapshot(
            telegram_user_id,
            current_time,
            {
                "telegram_user_id": telegram_user_id,
                "source_type": source["source_type"],
                "source_identifier": source["source_identifier"],
                "submitted_at": current_time.isoformat(),
                "items": valid_items,
                "rejected_items": rejected_items,
            },
        )
