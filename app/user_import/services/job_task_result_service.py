from __future__ import annotations

from typing import Any, Protocol


class UserImportJobTaskResultJobsPort(Protocol):
    def list_items(self, job_id: int) -> list[dict[str, Any]]: ...


class UserImportJobTaskResultDatabasePort(Protocol):
    user_import_jobs: UserImportJobTaskResultJobsPort


class UserImportJobTaskResultService:
    def __init__(self, db: UserImportJobTaskResultDatabasePort) -> None:
        self.db = db

    def build_import_job_task_result(self, job_id: int, *, import_job_status: str) -> dict[str, Any]:
        items = self.db.user_import_jobs.list_items(job_id)
        counts: dict[str, int] = {}
        for item in items:
            status = str(item["status"])
            counts[status] = counts.get(status, 0) + 1
        return {
            "import_job_status": import_job_status,
            "total_items": len(items),
            "unfinished_items_count": len([item for item in items if item["status"] == "pending"]),
            "found_existing_count": counts.get("found_existing", 0),
            "waiting_for_user_dictionary_entry_count": counts.get("waiting_for_user_dictionary_entry", 0),
            "queued_for_details_count": counts.get("queued_for_details", 0),
            "queued_for_audio_count": counts.get("queued_for_audio", 0),
            "queued_for_embedding_count": counts.get("queued_for_embedding", 0),
            "ready_for_rotation_count": counts.get("ready_for_rotation", 0),
            "imported_count": counts.get("imported", 0),
            "rejected_count": counts.get("rejected", 0),
            "details_failed_count": counts.get("details_failed", 0),
            "audio_failed_count": counts.get("audio_failed", 0),
            "embedding_failed_count": counts.get("embedding_failed", 0),
            "failed_count": counts.get("failed", 0),
            "status_counts": counts,
            "processed_lookup_words": [item["lookup_word"] for item in items],
        }
