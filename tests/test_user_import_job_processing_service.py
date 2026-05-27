from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.user_import.services.job_processing_service import UserImportJobProcessingService


class FakeTaskLogRepository(list[dict[str, Any]]):
    def __init__(self) -> None:
        super().__init__()
        self.updates: list[tuple[int, dict[str, Any]]] = []

    def create(self, **kwargs: Any) -> dict[str, Any]:
        task_log = {"id": len(self) + 1, **kwargs}
        self.append(task_log)
        return task_log

    def create_for_user_uuid(self, **kwargs: Any) -> dict[str, Any]:
        task_log = {"id": len(self) + 1, **kwargs}
        self.append(task_log)
        return task_log

    def update(self, task_log_id: int, **kwargs: Any) -> None:
        self.updates.append((task_log_id, kwargs))
        self[task_log_id - 1].update(kwargs)


class FakeErrorLogRepository:
    def __init__(self, errors: list[tuple[str, str, dict[str, Any]]]) -> None:
        self.errors = errors

    def create(self, level: str, text: str, *, context_json: dict[str, Any]) -> None:
        self.errors.append((level, text, context_json))


class FakeJobProcessingDb:
    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items = items
        self.task_logs = FakeTaskLogRepository()
        self.completed_jobs: list[tuple[int, dict[str, Any]]] = []
        self.priority_words: list[tuple[str | int, int, datetime | None]] = []
        self.errors: list[tuple[str, str, dict[str, Any]]] = []
        self.error_logs = FakeErrorLogRepository(self.errors)

    @property
    def user_import_jobs(self) -> FakeJobProcessingDb:
        return self

    def list_items(self, job_id: int) -> list[dict[str, Any]]:
        return self.items

    @property
    def dictionary_lookup(self) -> FakeJobProcessingDb:
        return self

    def list_unfinished_items(self, job_id: int) -> list[dict[str, Any]]:
        return [item for item in self.items if item["status"] in {"pending", "collecting"}]

    def create_user_core_word_assignment(
        self,
        telegram_user_id: int,
        word_id: int,
        *,
        current_time: datetime | None = None,
    ) -> None:
        self.priority_words.append((telegram_user_id, word_id, current_time))

    def create_user_core_word_assignment_for_user_uuid(
        self,
        user_uuid: str,
        word_id: int,
        *,
        current_time: datetime | None = None,
    ) -> None:
        self.priority_words.append((user_uuid, word_id, current_time))

    def complete_user_vocabulary_import_job(self, job_id: int, **kwargs: Any) -> None:
        self.completed_jobs.append((job_id, kwargs))

    def complete(self, job_id: int, **kwargs: Any) -> None:
        self.completed_jobs.append((job_id, kwargs))

class FakePreparationService:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.calls: list[tuple[dict[str, Any], datetime, int | None]] = []
        self.should_fail = should_fail

    def prepare_import_job_items(self, job: dict[str, Any], current_time: datetime, *, task_log_id: int | None) -> None:
        self.calls.append((job, current_time, task_log_id))
        if self.should_fail:
            raise RuntimeError("raw <boom>")


class FakeJobTaskResultService:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str]] = []

    def build_import_job_task_result(self, job_id: int, *, import_job_status: str) -> dict[str, Any]:
        self.calls.append((job_id, import_job_status))
        return {"job_id": job_id, "status": import_job_status}


def build_job() -> dict[str, Any]:
    return {
        "id": 10,
        "user_uuid": "11111111-1111-4111-8111-111111111111",
        "telegram_user_id": 20,
        "source_type": "google_doc",
        "source_identifier": "doc",
    }


def build_service(
    db: FakeJobProcessingDb,
    *,
    preparation_service: FakePreparationService | None = None,
    result_service: FakeJobTaskResultService | None = None,
) -> UserImportJobProcessingService:
    return UserImportJobProcessingService(
        db,
        prepare_import_job_items=(preparation_service or FakePreparationService()).prepare_import_job_items,
        job_task_result_service=result_service or FakeJobTaskResultService(),
        build_task_error_context=lambda **kwargs: {"context": kwargs},
        sanitize_external_error_text=lambda value: value.replace("<", "[").replace(">", "]"),
    )


def test_process_claimed_job_completes_job_and_adds_existing_priority_words() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakeJobProcessingDb(
        [
            {"id": 1, "status": "found_existing", "existing_word_id": 100},
            {"id": 2, "status": "queued_for_details", "existing_word_id": None},
        ]
    )
    result_service = FakeJobTaskResultService()

    quota, budget = build_service(db, result_service=result_service).process_claimed_job(
        build_job(),
        current_time=current_time,
        wordnik_quota={"requests_used": 0},
        wordnik_budget=0,
        wordnik_hourly_limit=0,
    )

    assert quota == {"requests_used": 0}
    assert budget == 0
    assert db.priority_words == [("11111111-1111-4111-8111-111111111111", 100, current_time)]
    assert db.completed_jobs == [(10, {"status": "completed", "current_time": current_time})]
    assert db.task_logs[0]["user_uuid"] == UUID("11111111-1111-4111-8111-111111111111")
    assert db.task_logs.updates[-1][1]["status"] == "success"
    assert result_service.calls[-1] == (10, "completed")


def test_process_claimed_job_accepts_uuid_only_job() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakeJobProcessingDb([{"id": 1, "status": "found_existing", "existing_word_id": 100}])
    job = build_job()
    job.pop("telegram_user_id")

    build_service(db).process_claimed_job(
        job,
        current_time=current_time,
        wordnik_quota={},
        wordnik_budget=0,
        wordnik_hourly_limit=0,
    )

    assert db.priority_words == [("11111111-1111-4111-8111-111111111111", 100, current_time)]
    assert db.completed_jobs == [(10, {"status": "completed", "current_time": current_time})]


def test_process_claimed_job_pauses_when_items_remain_unfinished() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakeJobProcessingDb([{"id": 1, "status": "pending", "existing_word_id": None}])
    result_service = FakeJobTaskResultService()

    build_service(db, result_service=result_service).process_claimed_job(
        build_job(),
        current_time=current_time,
        wordnik_quota={},
        wordnik_budget=0,
        wordnik_hourly_limit=0,
    )

    assert db.completed_jobs == []
    assert db.task_logs.updates[-1][1]["status"] == "success"
    assert "unfinished_items=1" in db.task_logs.updates[-1][1]["description"]
    assert result_service.calls == [(10, "processing")]


def test_process_claimed_job_marks_failed_on_outer_exception() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakeJobProcessingDb([{"id": 1, "status": "queued_for_details", "existing_word_id": None}])
    result_service = FakeJobTaskResultService()

    build_service(
        db,
        preparation_service=FakePreparationService(should_fail=True),
        result_service=result_service,
    ).process_claimed_job(
        build_job(),
        current_time=current_time,
        wordnik_quota={},
        wordnik_budget=0,
        wordnik_hourly_limit=0,
    )

    assert db.errors[0][0] == "fatal"
    assert "raw [boom]" in db.errors[0][1]
    assert db.errors[0][2]["context"]["import_job_id"] == 10
    assert db.completed_jobs == [(10, {"status": "failed", "current_time": current_time, "last_error": "raw [boom]"})]
    assert db.task_logs.updates[-1][1]["status"] == "fatal"
    assert db.task_logs.updates[-1][1]["error_text"] == "raw [boom]"
    assert result_service.calls == [(10, "failed")]
