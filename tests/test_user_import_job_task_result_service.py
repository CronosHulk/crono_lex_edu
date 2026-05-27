from __future__ import annotations

from typing import Any

from app.user_import.services.job_task_result_service import UserImportJobTaskResultService


class FakeJobTaskResultDb:
    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items = items
        self.requested_job_ids: list[int] = []

    @property
    def user_import_jobs(self) -> FakeJobTaskResultDb:
        return self

    def list_items(self, job_id: int) -> list[dict[str, Any]]:
        self.requested_job_ids.append(job_id)
        return self.items


def test_build_import_job_task_result_counts_statuses_and_lookup_words() -> None:
    db = FakeJobTaskResultDb(
        [
            {"status": "pending", "lookup_word": "alpha"},
            {"status": "waiting_for_user_dictionary_entry", "lookup_word": "bravo"},
            {"status": "found_existing", "lookup_word": "charlie"},
            {"status": "queued_for_details", "lookup_word": "delta"},
            {"status": "queued_for_audio", "lookup_word": "echo"},
            {"status": "queued_for_embedding", "lookup_word": "foxtrot"},
            {"status": "ready_for_rotation", "lookup_word": "golf"},
            {"status": "imported", "lookup_word": "kilo"},
            {"status": "rejected", "lookup_word": "lima"},
            {"status": "details_failed", "lookup_word": "mike"},
            {"status": "audio_failed", "lookup_word": "november"},
            {"status": "embedding_failed", "lookup_word": "osprey"},
            {"status": "failed", "lookup_word": "november"},
        ]
    )

    result = UserImportJobTaskResultService(db).build_import_job_task_result(42, import_job_status="processing")

    assert db.requested_job_ids == [42]
    assert result == {
        "import_job_status": "processing",
        "total_items": 13,
        "unfinished_items_count": 1,
        "found_existing_count": 1,
        "waiting_for_user_dictionary_entry_count": 1,
        "queued_for_details_count": 1,
        "queued_for_audio_count": 1,
        "queued_for_embedding_count": 1,
        "ready_for_rotation_count": 1,
        "imported_count": 1,
        "rejected_count": 1,
        "details_failed_count": 1,
        "audio_failed_count": 1,
        "embedding_failed_count": 1,
        "failed_count": 1,
        "status_counts": {
            "pending": 1,
            "waiting_for_user_dictionary_entry": 1,
            "found_existing": 1,
            "queued_for_details": 1,
            "queued_for_audio": 1,
            "queued_for_embedding": 1,
            "ready_for_rotation": 1,
            "imported": 1,
            "rejected": 1,
            "details_failed": 1,
            "audio_failed": 1,
            "embedding_failed": 1,
            "failed": 1,
        },
        "processed_lookup_words": [
            "alpha",
            "bravo",
            "charlie",
            "delta",
            "echo",
            "foxtrot",
            "golf",
            "kilo",
            "lima",
            "mike",
            "november",
            "osprey",
            "november",
        ],
    }


def test_build_import_job_task_result_handles_empty_items() -> None:
    result = UserImportJobTaskResultService(FakeJobTaskResultDb([])).build_import_job_task_result(
        7,
        import_job_status="failed",
    )

    assert result == {
        "import_job_status": "failed",
        "total_items": 0,
        "unfinished_items_count": 0,
        "found_existing_count": 0,
        "waiting_for_user_dictionary_entry_count": 0,
        "queued_for_details_count": 0,
        "queued_for_audio_count": 0,
        "queued_for_embedding_count": 0,
        "ready_for_rotation_count": 0,
        "imported_count": 0,
        "rejected_count": 0,
        "details_failed_count": 0,
        "audio_failed_count": 0,
        "embedding_failed_count": 0,
        "failed_count": 0,
        "status_counts": {},
        "processed_lookup_words": [],
    }
