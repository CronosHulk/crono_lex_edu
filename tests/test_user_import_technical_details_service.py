from __future__ import annotations

from typing import Any

from app.user_import.services.technical_details_service import UserImportTechnicalDetailsService


class FakeTaskLogRepository(dict[int, dict[str, Any]]):
    def __init__(self) -> None:
        super().__init__()
        self.processing_logs: dict[int, dict[str, Any] | None] = {}

    def get(self, task_log_id: int) -> dict[str, Any] | None:
        return super().get(task_log_id)

    def get_latest_for_import_job(self, job_id: int, *, task_type: str) -> dict[str, Any] | None:
        assert task_type == "user_vocabulary_import_job_process"
        return self.processing_logs.get(job_id)


class FakeTechnicalDetailsDb:
    def __init__(self) -> None:
        self.task_logs = FakeTaskLogRepository()

    @property
    def processing_logs(self) -> dict[int, dict[str, Any] | None]:
        return self.task_logs.processing_logs


def test_build_technical_details_returns_none_without_context() -> None:
    db = FakeTechnicalDetailsDb()

    details = UserImportTechnicalDetailsService(db).build_technical_details(
        locale="uk",
        job={"id": 7},
    )

    assert details is None


def test_build_technical_details_escapes_source_and_includes_origin_counts() -> None:
    db = FakeTechnicalDetailsDb()
    db.task_logs[3] = {
        "id": 3,
        "status": "success",
        "result_json": {"invalid_fragments_count": 2, "skipped_duplicates_count": 1},
    }

    details = UserImportTechnicalDetailsService(db).build_technical_details(
        locale="uk",
        job={"id": 7, "task_log_id": 3, "source_identifier": "<doc>"},
    )

    assert details is not None
    assert "&lt;doc&gt;" in details
    assert "#3" in details
    assert "2 елементи" in details
    assert "1 елемент" in details


def test_build_technical_details_includes_processing_error_only_for_failed_statuses() -> None:
    db = FakeTechnicalDetailsDb()
    db.processing_logs[7] = {"id": 8, "status": "error", "error_text": "<broken>"}

    details = UserImportTechnicalDetailsService(db).build_technical_details(
        locale="uk",
        job={"id": 7},
    )

    assert details is not None
    assert "#8" in details
    assert "&lt;broken&gt;" in details


def test_build_technical_details_skips_processing_error_for_success_status() -> None:
    db = FakeTechnicalDetailsDb()
    db.processing_logs[7] = {"id": 8, "status": "success", "error_text": "<ignored>"}

    details = UserImportTechnicalDetailsService(db).build_technical_details(
        locale="uk",
        job={"id": 7},
    )

    assert details is not None
    assert "#8" in details
    assert "&lt;ignored&gt;" not in details
