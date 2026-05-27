from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from app.contracts import DocumentAttachmentModel, ScreenModel
from app.i18n import translate
from app.storage.user_import_artifacts import UserImportArtifactStorageProvider
from app.user_import.services.document_service import (
    UserImportDocumentDictionaryLookupPort,
    UserImportDocumentService,
)
from app.user_import.services.summary_screen_service import UserImportSummaryScreenService
from app.user_import.services.technical_details_service import (
    UserImportTechnicalDetailsService,
    UserImportTechnicalDetailsTaskLogsPort,
)


class UserImportSummaryJobsPort(Protocol):
    def get_job_for_user(
        self,
        telegram_user_id: int,
        job_id: int,
    ) -> dict[str, Any] | None: ...

    def list_items_for_user(
        self,
        telegram_user_id: int,
        job_id: int,
    ) -> list[dict[str, Any]]: ...


class UserImportSummaryDatabasePort(Protocol):
    @property
    def user_import_jobs(self) -> UserImportSummaryJobsPort: ...

    @property
    def dictionary_lookup(self) -> UserImportDocumentDictionaryLookupPort: ...

    @property
    def task_logs(self) -> UserImportTechnicalDetailsTaskLogsPort: ...


class _UserImportSummaryDatabasePortWrapper:
    def __init__(self, db: Any) -> None:
        self.db = db
        user_import_jobs = getattr(db, "user_import_jobs", None)
        if user_import_jobs is None and callable(getattr(db, "session", None)):
            from app.data_access.user_import_jobs import UserImportJobRepository
            user_import_jobs = UserImportJobRepository(db)
        self.user_import_jobs = user_import_jobs

        dictionary_lookup = getattr(db, "dictionary_lookup", None)
        if dictionary_lookup is None and callable(getattr(db, "session", None)):
            from app.data_access.dictionary_lookup import DictionaryLookupRepository
            dictionary_lookup = DictionaryLookupRepository(db)
        self.dictionary_lookup = dictionary_lookup

        task_logs = getattr(db, "task_logs", None)
        if task_logs is None and callable(getattr(db, "session", None)):
            from app.data_access.task_logs import TaskLogRepository
            task_logs = TaskLogRepository(db)
        self.task_logs = task_logs

    def __getattr__(self, name: str) -> Any:
        return getattr(self.db, name)


class UserImportSummaryService:
    def __init__(
        self,
        db: UserImportSummaryDatabasePort,
        *,
        build_import_screen: Callable[[int, str, str | None], ScreenModel],
        build_import_url: Callable[[int], str] | None = None,
        get_intake_snapshot: Callable[[dict[str, Any]], dict[str, Any]],
        artifact_storage_provider: UserImportArtifactStorageProvider,
    ) -> None:
        wrapped_db = _UserImportSummaryDatabasePortWrapper(db)
        self.db = wrapped_db
        self.build_import_screen = build_import_screen
        self.build_import_url = build_import_url
        self.get_intake_snapshot = get_intake_snapshot
        self.document_service = UserImportDocumentService(
            wrapped_db,
            artifact_storage_provider=artifact_storage_provider,
        )
        self.screen_service = UserImportSummaryScreenService(build_import_url=build_import_url)
        self.technical_details_service = UserImportTechnicalDetailsService(wrapped_db)

    def build_user_import_document_screen_for_user(
        self,
        *,
        telegram_user_id: int,
        locale: str,
        job_id: int,
        slice_name: str,
    ) -> ScreenModel:
        job = self.db.user_import_jobs.get_job_for_user(telegram_user_id, job_id)
        items = self.db.user_import_jobs.list_items_for_user(telegram_user_id, job_id)
        if job is None or not items:
            return self.build_import_screen(
                telegram_user_id,
                locale,
                translate(locale, "import_words_invalid_url"),
            )
        intake_snapshot = self.get_intake_snapshot(job)
        if slice_name == "queued":
            documents = [self.build_user_import_queued_document(locale=locale, job=job, items=items, intake_snapshot=intake_snapshot)]
        elif slice_name == "existing":
            documents = [self.build_user_import_existing_document(locale=locale, job=job, items=items, intake_snapshot=intake_snapshot)]
        else:
            documents = []
        return self.screen_service.build_user_import_document_screen(
            job_id=job_id,
            slice_name=slice_name,
            documents=documents,
        )

    def build_user_import_intake_slice_screen(
        self,
        *,
        telegram_user_id: int,
        locale: str,
        job_id: int,
        slice_name: str,
    ) -> ScreenModel:
        job = self.db.user_import_jobs.get_job_for_user(telegram_user_id, job_id)
        if job is None:
            return self.build_import_screen(
                telegram_user_id,
                locale,
                translate(locale, "import_words_invalid_url"),
            )
        intake_snapshot = self.get_intake_snapshot(job)
        return self.screen_service.build_user_import_intake_slice_screen(
            locale=locale,
            job_id=job_id,
            slice_name=slice_name,
            intake_snapshot=intake_snapshot,
        )

    def build_user_import_queued_document(
        self,
        *,
        locale: str,
        job: dict[str, Any],
        items: list[dict[str, Any]],
        intake_snapshot: dict[str, Any] | None = None,
    ) -> DocumentAttachmentModel | None:
        return self.document_service.build_queued_document(
            locale=locale,
            job=job,
            items=items,
            intake_snapshot=intake_snapshot,
        )

    def build_user_import_existing_document(
        self,
        *,
        locale: str,
        job: dict[str, Any],
        items: list[dict[str, Any]],
        intake_snapshot: dict[str, Any] | None = None,
    ) -> DocumentAttachmentModel | None:
        return self.document_service.build_existing_document(
            locale=locale,
            job=job,
            items=items,
            intake_snapshot=intake_snapshot,
        )

    def build_user_import_summary_documents(
        self,
        *,
        locale: str,
        job: dict[str, Any],
        items: list[dict[str, Any]],
        intake_snapshot: dict[str, Any] | None = None,
    ) -> list[DocumentAttachmentModel]:
        return self.document_service.build_summary_documents(
            locale=locale,
            job=job,
            items=items,
            intake_snapshot=intake_snapshot,
        )

    def build_user_import_published_document(
        self,
        *,
        locale: str,
        job: dict[str, Any],
        items: list[dict[str, Any]],
    ) -> DocumentAttachmentModel | None:
        return self.document_service.build_published_document(locale=locale, job=job, items=items)

    def build_user_import_summary_screen(
        self,
        *,
        locale: str,
        job_id: int,
        items: list[dict[str, Any]],
        job_status: str,
        last_error: str | None = None,
        notice: str | None = None,
        technical_details: str | None = None,
        intake_snapshot: dict[str, Any] | None = None,
        documents: list[DocumentAttachmentModel] | None = None,
        telegram_user_id: int | None = None,
    ) -> ScreenModel:
        return self.screen_service.build_user_import_summary_screen(
            locale=locale,
            job_id=job_id,
            items=items,
            job_status=job_status,
            last_error=last_error,
            notice=notice,
            technical_details=technical_details,
            intake_snapshot=intake_snapshot,
            documents=documents,
            telegram_user_id=telegram_user_id,
        )

    def build_user_import_queued_items_screen(
        self,
        *,
        telegram_user_id: int,
        locale: str,
        job_id: int,
    ) -> ScreenModel:
        return self.build_user_import_document_screen_for_user(
            telegram_user_id=telegram_user_id,
            locale=locale,
            job_id=job_id,
            slice_name="queued",
        )

    def build_user_import_existing_items_screen(
        self,
        *,
        telegram_user_id: int,
        locale: str,
        job_id: int,
    ) -> ScreenModel:
        return self.build_user_import_document_screen_for_user(
            telegram_user_id=telegram_user_id,
            locale=locale,
            job_id=job_id,
            slice_name="existing",
        )

    def build_user_import_failed_items_screen(
        self,
        *,
        telegram_user_id: int,
        locale: str,
        job_id: int,
    ) -> ScreenModel:
        job = self.db.user_import_jobs.get_job_for_user(telegram_user_id, job_id)
        items = self.db.user_import_jobs.list_items_for_user(telegram_user_id, job_id)
        if job is None or not items:
            return self.build_import_screen(
                telegram_user_id,
                locale,
                translate(locale, "import_words_invalid_url"),
            )
        intake_snapshot = self.get_intake_snapshot(job)
        technical_details = self.build_user_import_technical_details(locale=locale, job=job)
        return self.screen_service.build_user_import_failed_items_screen(
            locale=locale,
            job_id=job_id,
            items=items,
            intake_snapshot=intake_snapshot,
            technical_details=technical_details,
        )

    def build_user_import_summary_screen_for_user(
        self,
        *,
        telegram_user_id: int,
        locale: str,
        job_id: int,
        notice: str | None = None,
    ) -> ScreenModel:
        job = self.db.user_import_jobs.get_job_for_user(telegram_user_id, job_id)
        items = self.db.user_import_jobs.list_items_for_user(telegram_user_id, job_id)
        if job is None or not items:
            return self.build_import_screen(
                telegram_user_id,
                locale,
                translate(locale, "import_words_invalid_url"),
            )
        intake_snapshot = self.get_intake_snapshot(job)
        documents = self.build_user_import_summary_documents(
            locale=locale,
            job=job,
            items=items,
            intake_snapshot=intake_snapshot,
        )
        return self.build_user_import_summary_screen(
            locale=locale,
            job_id=job_id,
            items=items,
            job_status=str(job["status"]),
            last_error=job.get("last_error"),
            notice=notice,
            technical_details=self.build_user_import_technical_details(locale=locale, job=job),
            intake_snapshot=intake_snapshot,
            documents=documents,
            telegram_user_id=telegram_user_id,
        )

    def build_user_import_publish_summary_screen_for_user(
        self,
        *,
        telegram_user_id: int,
        locale: str,
        job_id: int,
        priority_count: int,
    ) -> ScreenModel:
        job = self.db.user_import_jobs.get_job_for_user(telegram_user_id, job_id)
        items = self.db.user_import_jobs.list_items_for_user(telegram_user_id, job_id)
        if job is None or not items:
            return self.build_import_screen(
                telegram_user_id,
                locale,
                translate(locale, "import_words_invalid_url"),
            )
        documents: list[DocumentAttachmentModel] = []
        published_document = self.build_user_import_published_document(locale=locale, job=job, items=items)
        if published_document is not None:
            documents.append(published_document)
        return self.screen_service.build_user_import_publish_summary_screen(
            locale=locale,
            job_id=job_id,
            items=items,
            priority_count=priority_count,
            documents=documents,
        )

    def build_user_import_technical_details(self, *, locale: str, job: dict[str, Any]) -> str | None:
        return self.technical_details_service.build_technical_details(locale=locale, job=job)

    def resolve_user_import_existing_translation(self, locale: str, lookup_word: str) -> str:
        return self.document_service.resolve_existing_translation(locale, lookup_word)
