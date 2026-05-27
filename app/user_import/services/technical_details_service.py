from __future__ import annotations

import html
from typing import Any, Protocol

from app.i18n import translate
from app.user_import.services.helpers import (
    format_import_count_text,
    format_import_task_status,
)


class UserImportTechnicalDetailsTaskLogsPort(Protocol):
    def get(self, task_log_id: int) -> dict[str, Any] | None: ...

    def get_latest_for_import_job(
        self,
        import_job_id: int,
        *,
        task_type: str | None = None,
    ) -> dict[str, Any] | None: ...


class UserImportTechnicalDetailsDatabasePort(Protocol):
    @property
    def task_logs(self) -> UserImportTechnicalDetailsTaskLogsPort: ...


class UserImportTechnicalDetailsService:
    def __init__(self, db: UserImportTechnicalDetailsDatabasePort) -> None:
        self.db = db

    def build_technical_details(self, *, locale: str, job: dict[str, Any]) -> str | None:
        details = [translate(locale, "import_words_summary_technical_title")]
        source_identifier = str(job.get("source_identifier") or "").strip()
        if source_identifier:
            details.append(
                translate(
                    locale,
                    "import_words_summary_source_identifier_line",
                    source=html.escape(source_identifier),
                )
            )

        origin_task_log = None
        task_log_id = job.get("task_log_id")
        if task_log_id is not None:
            origin_task_log = self.db.task_logs.get(int(task_log_id))
        processing_task_log = self.db.task_logs.get_latest_for_import_job(
            int(job["id"]),
            task_type="user_vocabulary_import_job_process",
        )

        if origin_task_log is not None:
            details.append(
                translate(
                    locale,
                    "import_words_summary_origin_task_line",
                    task_id=int(origin_task_log["id"]),
                    status=format_import_task_status(locale, str(origin_task_log.get("status"))),
                )
            )
            origin_result = origin_task_log.get("result_json") or {}
            invalid_fragments_count = int(origin_result.get("invalid_fragments_count") or 0)
            if invalid_fragments_count > 0:
                details.append(
                    translate(
                        locale,
                        "import_words_summary_invalid_fragments_line",
                        count_text=format_import_count_text(locale, invalid_fragments_count),
                    )
                )
            skipped_duplicates_count = int(origin_result.get("skipped_duplicates_count") or 0)
            if skipped_duplicates_count > 0:
                details.append(
                    translate(
                        locale,
                        "import_words_summary_skipped_duplicates_line",
                        count_text=format_import_count_text(locale, skipped_duplicates_count),
                    )
                )

        if processing_task_log is not None:
            details.append(
                translate(
                    locale,
                    "import_words_summary_processing_task_line",
                    task_id=int(processing_task_log["id"]),
                    status=format_import_task_status(locale, str(processing_task_log.get("status"))),
                )
            )
            if processing_task_log.get("status") in {"error", "fatal"}:
                error_text = str(processing_task_log.get("error_text") or "").strip()
                if error_text:
                    details.append(
                        translate(
                            locale,
                            "import_words_summary_task_error_line",
                            error=html.escape(error_text),
                        )
                    )

        if len(details) == 1:
            return None
        return "\n".join(details)
