from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.application.client_web.import_errors import (
    ClientWebImportNotFoundError,
)
from app.application.client_web.import_statuses import (
    IMPORT_STATUS_EXACT_LABELS,
    IMPORT_STATUS_LABELS,
    build_category_summary,
    build_status_summary,
    status_category,
    status_filter,
    validate_import_result_page_size,
)
from app.helpers.locale import resolve_user_locale

IMPORT_MODE_LOOKUP_ONLY = "lookup_only"


class ClientWebImportResultsTimeService(Protocol):
    def now(self) -> datetime: ...


class ClientWebImportResultsUserImportJobsPort(Protocol):
    def get_job_for_user(self, telegram_user_id: int, job_id: int) -> dict[str, Any] | None: ...

    def complete(
        self,
        job_id: int,
        *,
        status: str,
        current_time: datetime,
        last_error: str | None = None,
    ) -> Any: ...

    def list_items_for_user_by_category_paginated(
        self,
        telegram_user_id: int,
        job_id: int,
        *,
        page: int,
        page_size: int,
        status_category: str,
    ) -> dict[str, Any]: ...

    def list_item_category_counts(self, job_id: int, telegram_user_id: int) -> dict[str, Any]: ...

    def get_latest_job_for_user(self, telegram_user_id: int) -> dict[str, Any] | None: ...

    def list_all_items_for_user_by_category_paginated(
        self,
        telegram_user_id: int,
        *,
        page: int,
        page_size: int,
        status_category: str,
    ) -> dict[str, Any]: ...

    def list_user_item_category_counts(self, telegram_user_id: int) -> dict[str, Any]: ...

    def list_items(self, job_id: int) -> list[dict[str, Any]]: ...

    def list_unfinished_items(self, job_id: int) -> list[dict[str, Any]]: ...


class ClientWebImportResultsDatabasePort(Protocol):
    user_import_jobs: ClientWebImportResultsUserImportJobsPort


class ClientWebImportResultsPreparationServicePort(Protocol):
    def prepare_import_job_items(
        self,
        job: dict[str, Any],
        current_time: datetime,
        *,
        task_log_id: int | None,
    ) -> Any: ...


class ClientWebImportResultsRuntime(Protocol):
    db: ClientWebImportResultsDatabasePort
    time_service: ClientWebImportResultsTimeService
    user_import_preparation_service: ClientWebImportResultsPreparationServicePort


class ClientWebImportResultsImportModeResolver(Protocol):
    def __call__(self, user_uuid: str | None, *, current_time: datetime) -> str: ...


class ClientWebImportResultsService:
    def __init__(
        self,
        learning_service: ClientWebImportResultsRuntime,
        *,
        import_mode_for_user: ClientWebImportResultsImportModeResolver,
    ) -> None:
        self.learning_service = learning_service
        self.db: ClientWebImportResultsDatabasePort = learning_service.db
        self.import_mode_for_user = import_mode_for_user

    def list_results(
        self,
        user: dict[str, Any],
        *,
        job_id: int,
        page: int,
        page_size: int,
        status_category: str = "all",
    ) -> dict[str, Any]:
        validate_import_result_page_size(page_size)
        status_filter(status_category)
        telegram_user_id = int(user["telegram_user_id"])
        self.ensure_job_for_user(user, job_id)
        self._repair_lookup_only_pending_job(user, job_id=job_id)
        result = self.db.user_import_jobs.list_items_for_user_by_category_paginated(
            telegram_user_id,
            job_id,
            page=page,
            page_size=page_size,
            status_category=status_category,
        )
        category_counts = self.db.user_import_jobs.list_item_category_counts(job_id, telegram_user_id)
        locale = resolve_user_locale(user)
        return {
            **result,
            "status_category": status_category,
            "items": [self._serialize_item(item, locale) for item in result["items"]],
            "summary": build_category_summary(category_counts),
        }

    def ensure_job_for_user(self, user: dict[str, Any], job_id: int) -> None:
        telegram_user_id = int(user["telegram_user_id"])
        if self.db.user_import_jobs.get_job_for_user(telegram_user_id, job_id) is None:
            raise ClientWebImportNotFoundError("Import job not found")

    def list_user_results(
        self,
        user: dict[str, Any],
        *,
        page: int,
        page_size: int,
        status_category: str = "all",
    ) -> dict[str, Any]:
        validate_import_result_page_size(page_size)
        status_filter(status_category)
        telegram_user_id = int(user["telegram_user_id"])
        latest_job = self.db.user_import_jobs.get_latest_job_for_user(telegram_user_id)
        if latest_job is None:
            return {
                "items": [],
                "page": page,
                "page_size": page_size,
                "total": 0,
                "pages": 0,
                "status_category": status_category,
                "summary": build_status_summary({}),
            }
        job_id = int(latest_job["id"])
        self._repair_lookup_only_pending_job(user, job_id=job_id)
        result = self.db.user_import_jobs.list_all_items_for_user_by_category_paginated(
            telegram_user_id,
            page=page,
            page_size=page_size,
            status_category=status_category,
        )
        category_counts = self.db.user_import_jobs.list_user_item_category_counts(telegram_user_id)
        locale = resolve_user_locale(user)
        return {
            **result,
            "status_category": status_category,
            "items": [self._serialize_item(item, locale) for item in result["items"]],
            "summary": build_category_summary(category_counts),
        }

    def serialize_job(self, job: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": int(job["id"]),
            "status": str(job.get("status") or ""),
            "total_items": int(job.get("total_items") or 0),
            "successful_items": int(job.get("successful_items") or 0),
            "failed_items": int(job.get("failed_items") or 0),
        }

    def _repair_lookup_only_pending_job(self, user: dict[str, Any], *, job_id: int) -> None:
        current_time = self.learning_service.time_service.now()
        if self._import_mode_for_user(user, current_time=current_time) != IMPORT_MODE_LOOKUP_ONLY:
            return
        telegram_user_id = int(user["telegram_user_id"])
        job = self.db.user_import_jobs.get_job_for_user(telegram_user_id, job_id)
        if job is None:
            return
        items = self.db.user_import_jobs.list_items(job_id)
        if not any(item["status"] == "pending" for item in items):
            return
        self.learning_service.user_import_preparation_service.prepare_import_job_items(
            job,
            current_time,
            task_log_id=None,
        )
        if not self._list_unfinished_items(job_id):
            self.db.user_import_jobs.complete(job_id, status="completed", current_time=current_time)

    def _list_unfinished_items(self, job_id: int) -> list[dict[str, Any]]:
        return self.db.user_import_jobs.list_unfinished_items(job_id)

    def _import_mode_for_user(self, user: dict[str, Any], *, current_time: datetime) -> str:
        return self.import_mode_for_user(_user_uuid_from_user(user), current_time=current_time)

    def _serialize_item(self, item: dict[str, Any], locale: str) -> dict[str, Any]:
        status = str(item.get("status") or "")
        category = str(item.get("computed_status_category") or status_category(status))
        status_label = IMPORT_STATUS_LABELS.get(locale, IMPORT_STATUS_LABELS["uk"])[category]
        if category == "added":
            status_label = IMPORT_STATUS_EXACT_LABELS.get(locale, IMPORT_STATUS_EXACT_LABELS["uk"]).get(status, status_label)
        return {
            "id": int(item["id"]),
            "word": str(item.get("lookup_word") or item.get("raw_value") or ""),
            "validated_word": str(item.get("validated_lookup_word") or ""),
            "raw_value": str(item.get("raw_value") or ""),
            "translation_hint": str(item.get("translation_hint") or ""),
            "validated_part_of_speech": str(item.get("validated_part_of_speech") or ""),
            "validated_translation_uk": str(item.get("validated_translation_uk") or ""),
            "validated_translation_ru": str(item.get("validated_translation_ru") or ""),
            "validated_translation_pl": str(item.get("validated_translation_pl") or ""),
            "status": status,
            "status_category": category,
            "status_label": status_label,
            "error_text": str(item.get("error_text") or ""),
        }


def _user_uuid_from_user(user: dict[str, Any] | None) -> str | None:
    if user is None:
        return None
    raw_user_uuid = user.get("user_id") or user.get("user_uuid") or user.get("id")
    return str(raw_user_uuid) if raw_user_uuid else None
