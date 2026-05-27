from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, NamedTuple

from app.contracts import ScreenModel, TelegramUserContext
from app.domain.user_import.text_parser import (
    ParsedImportWord,
    parse_user_vocabulary_text_result,
)
from app.storage.user_import_artifacts import UserImportArtifactRef
from app.user_import.services.bound_google_doc_sync_processor import (
    UserImportBoundGoogleDocSyncProcessor,
)
from app.user_import.services.google_doc_progress import line_hash
from app.user_import.services.intake_job_service import UserImportIntakeJobService
from app.user_import.services.intake_manual_bind_service import (
    UserImportIntakeManualBindService,
)
from app.user_import.services.intake_service import UserImportIntakeService
from app.user_import.services.validation_service import UserImportValidationOutcome
from app.validators.user_import_provider_results import (
    AIImportValidationResult,
)


class FakeGoogleDocs:
    def __init__(self) -> None:
        self.binding_calls: list[dict[str, Any]] = []
        self.progress_calls: list[dict[str, Any]] = []
        self.success_calls: list[dict[str, Any]] = []
        self.clear_progress_calls: list[dict[str, Any]] = []
        self.progress: dict[str, Any] | None = None

    def set_binding(self, telegram_user_id: int, doc_id: str, current_time: datetime) -> None:
        self.binding_calls.append(
            {"telegram_user_id": telegram_user_id, "doc_id": doc_id, "current_time": current_time}
        )

    def get_progress(self, telegram_user_id: int, doc_id: str) -> dict[str, Any] | None:
        return self.progress

    def mark_progress(self, telegram_user_id: int, doc_id: str, **kwargs: Any) -> None:
        self.progress_calls.append({"telegram_user_id": telegram_user_id, "doc_id": doc_id, **kwargs})

    def clear_progress(self, telegram_user_id: int, doc_id: str, **kwargs: Any) -> None:
        self.clear_progress_calls.append({"telegram_user_id": telegram_user_id, "doc_id": doc_id, **kwargs})
        self.progress = None

    def mark_sync_success(self, telegram_user_id: int, *, current_time: datetime) -> None:
        self.success_calls.append({"telegram_user_id": telegram_user_id, "current_time": current_time})


class FakeImportJobs:
    def __init__(self) -> None:
        self.created_jobs: list[dict[str, Any]] = []
        self.existing_lookup_words: set[str] = set()

    def get_existing_lookup_words(self, telegram_user_id: int, lookup_words: list[str]) -> set[str]:
        return set(self.existing_lookup_words)

    def create_job(self, **kwargs: Any) -> dict[str, Any]:
        job = {"id": 900, "summary_sent": False, **kwargs}
        self.created_jobs.append(job)
        return job

    def get_job_for_user(self, telegram_user_id: int, job_id: int) -> dict[str, Any] | None:
        for job in self.created_jobs:
            if job["id"] == job_id and job["telegram_user_id"] == telegram_user_id:
                return dict(job)
        return None

    def list_items(self, job_id: int) -> list[dict[str, Any]]:
        for job in self.created_jobs:
            if job["id"] == job_id:
                return list(job["items"])
        return []

    def complete(self, job_id: int, *, status: str, current_time: datetime, last_error: str | None = None) -> None:
        for job in self.created_jobs:
            if job["id"] != job_id:
                continue
            job["status"] = status
            job["completed"] = current_time
            job["last_error"] = last_error

    def mark_summary_sent(self, job_id: int, current_time: datetime) -> None:
        for job in self.created_jobs:
            if job["id"] == job_id:
                job["summary_sent"] = True
                job["updated"] = current_time


class FakeTaskLogs:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.create_calls: list[dict[str, Any]] = []
        self.update_calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> dict[str, Any]:
        row = {"id": len(self.rows) + 1, **kwargs}
        self.rows.append(row)
        self.create_calls.append(dict(row))
        return dict(row)

    def update(self, task_log_id: int, **kwargs: Any) -> dict[str, Any] | None:
        self.update_calls.append({"task_log_id": task_log_id, **kwargs})
        for row in self.rows:
            if row["id"] != task_log_id:
                continue
            row.update(kwargs)
            return dict(row)
        return None


class FakeUserProfiles:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        return {"telegram_user_id": telegram_user_id, "user_uuid": "11111111-1111-4111-8111-111111111111"}

    def save_user_event(self, **kwargs: Any) -> None:
        self.events.append(kwargs)


class FakeValidationService:
    def __init__(self) -> None:
        self.usage_calls: list[dict[str, Any]] = []

    def validate_words(self, parsed_words: list[ParsedImportWord]) -> UserImportValidationOutcome:
        valid_words = [
            ParsedImportWord(
                raw_value="Extension cord",
                lookup_word="extension cord",
                translation_hint="удлинитель",
                validated_lookup_word=None,
                validated_part_of_speech="noun",
                validated_translation_uk="подовжувач",
            )
        ]
        return UserImportValidationOutcome(
            valid_words=valid_words,
            rejected_items=[
                {
                    "raw_value": "annoying boss",
                    "lookup_word": "annoying boss",
                    "status": "rejected",
                    "error_text": "Random descriptive collocation",
                }
            ],
            validation_result=AIImportValidationResult(
                accepted_lookup_words={"extension cord"},
                rejected_lookup_words={"annoying boss": "Random descriptive collocation"},
                provider_payload={},
            ),
        )

    def record_usage(self, validation_result: AIImportValidationResult | None, **kwargs: Any) -> None:
        self.usage_calls.append({"validation_result": validation_result, **kwargs})


class RecordingValidationService:
    def __init__(self) -> None:
        self.validated_batches: list[list[str]] = []
        self.usage_calls: list[dict[str, Any]] = []

    def validate_words(self, parsed_words: list[ParsedImportWord]) -> UserImportValidationOutcome:
        lookup_words = [item.lookup_word for item in parsed_words]
        self.validated_batches.append(lookup_words)
        return UserImportValidationOutcome(
            valid_words=[
                ParsedImportWord(
                    raw_value=item.raw_value,
                    lookup_word=item.lookup_word,
                    translation_hint=item.translation_hint,
                    validated_part_of_speech="noun",
                )
                for item in parsed_words
            ],
            rejected_items=[],
            validation_result=AIImportValidationResult(
                accepted_lookup_words=set(lookup_words),
                rejected_lookup_words={},
                provider_payload={},
            ),
        )

    def record_usage(self, validation_result: AIImportValidationResult | None, **kwargs: Any) -> None:
        self.usage_calls.append({"validation_result": validation_result, **kwargs})


class RejectingValidationService:
    def __init__(self) -> None:
        self.usage_calls: list[dict[str, Any]] = []

    def validate_words(self, parsed_words: list[ParsedImportWord]) -> UserImportValidationOutcome:
        lookup_words = {item.lookup_word for item in parsed_words}
        return UserImportValidationOutcome(
            valid_words=[],
            rejected_items=[
                {
                    "raw_value": item.raw_value,
                    "lookup_word": item.lookup_word,
                    "status": "rejected",
                    "error_text": "Rejected",
                }
                for item in parsed_words
            ],
            validation_result=AIImportValidationResult(
                accepted_lookup_words=set(),
                rejected_lookup_words={lookup_word: "Rejected" for lookup_word in lookup_words},
                provider_payload={},
            ),
        )

    def record_usage(self, validation_result: AIImportValidationResult | None, **kwargs: Any) -> None:
        self.usage_calls.append({"validation_result": validation_result, **kwargs})


class FakeCandidateFilter:
    def __init__(self, db: Any) -> None:
        self.db = db

    def list_assigned_lookup_words(self, user_uuid: str | None) -> set[str]:
        if not user_uuid:
            return set()
        return {
            " ".join(str(value or "").strip().lower().split())
            for value in self.db.user_dictionary.list_assigned_lookup_words_for_user(user_uuid)
        }

    def filter_already_assigned_words(self, parsed_words: list[Any], *, user_uuid: str | None) -> Any:
        assigned_lookup_words = self.list_assigned_lookup_words(user_uuid)
        eligible_words = []
        skipped_existing_words = []
        for item in parsed_words:
            lookup_word = " ".join(str(getattr(item, "lookup_word", "") or "").strip().lower().split())
            if lookup_word in assigned_lookup_words:
                skipped_existing_words.append(item)
            else:
                eligible_words.append(item)
        return SimpleNamespace(
            eligible_words=eligible_words,
            skipped_existing_words=skipped_existing_words,
            assigned_lookup_words=assigned_lookup_words,
        )


class FakeDb:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(app_user_import_max_words_per_bind=10, app_user_import_storage_dir="runtime/imports")
        self.user_import_jobs = FakeImportJobs()
        self.task_logs = FakeTaskLogs()
        self.user_dictionary = SimpleNamespace(list_assigned_lookup_words_for_user=lambda user_uuid: set())
        self.subscriptions = SimpleNamespace(
            get_by_user_uuid=lambda user_uuid: {"plan_key": "premium", "trial_start": None, "trial_end": None}
        )


class FakeArtifactStorageProvider:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.json_snapshots: list[dict[str, Any]] = []

    def write_json_snapshot(
        self,
        telegram_user_id: int,
        current_time: datetime,
        payload: dict[str, Any],
    ) -> str:
        self.json_snapshots.append(
            {
                "telegram_user_id": telegram_user_id,
                "current_time": current_time,
                "payload": payload,
            }
        )
        return str(self.path)

    def write_text_sibling(
        self,
        base_path: str,
        suffix: str,
        content: str,
    ) -> UserImportArtifactRef:
        raise AssertionError("intake job service should not write text artifacts")


class BuiltUserImportServices(NamedTuple):
    intake_service: UserImportIntakeService
    manual_bind_service: UserImportIntakeManualBindService
    intake_job_service: UserImportIntakeJobService
    sync_processor: UserImportBoundGoogleDocSyncProcessor
    db: FakeDb
    google_docs: FakeGoogleDocs


def build_services(tmp_path: Path, validation_service: Any) -> BuiltUserImportServices:
    db = FakeDb()
    google_docs = FakeGoogleDocs()
    artifact_storage_provider = FakeArtifactStorageProvider(tmp_path / "import.json")

    def build_google_doc_export_url(value: str) -> str:
        return value

    def fetch_google_doc_text(value: str) -> str:
        return "Extension cord - удлинитель\nannoying boss - бесящий босс"

    def sanitize_external_error_text(value: str) -> str:
        return value

    intake_job_service = UserImportIntakeJobService(
        db,  # type: ignore[arg-type]
        max_import_entries_per_submission=lambda: 100,
        build_import_snapshot=lambda **kwargs: kwargs,
        artifact_storage_provider=artifact_storage_provider,
    )
    manual_bind_service = UserImportIntakeManualBindService(
        db,  # type: ignore[arg-type]
        google_docs,
        FakeUserProfiles(),
        intake_job_service=intake_job_service,
        extract_google_doc_id=lambda value: value,
        build_google_doc_export_url=build_google_doc_export_url,
        fetch_google_doc_text=fetch_google_doc_text,
        parse_user_vocabulary_text_result=parse_user_vocabulary_text_result,
        mask_google_doc_url=lambda value: value,
        build_invalid_import_notice=lambda locale, fragments: "\n".join(fragments) if fragments else None,
        candidate_filter=FakeCandidateFilter(db),
        import_mode_for_user=lambda user_uuid, *, current_time: "ai_validation",
        max_import_entries_per_submission=lambda: 100,
        validation_service=validation_service,
    )
    intake_service = UserImportIntakeService(
        db,  # type: ignore[arg-type]
        intake_job_service=intake_job_service,
        manual_bind_service=manual_bind_service,
    )
    sync_processor = UserImportBoundGoogleDocSyncProcessor(
        db,  # type: ignore[arg-type]
        google_docs,
        intake_job_service=intake_job_service,
        build_google_doc_export_url=build_google_doc_export_url,
        fetch_google_doc_text=fetch_google_doc_text,
        parse_user_vocabulary_text_result=parse_user_vocabulary_text_result,
        sanitize_external_error_text=sanitize_external_error_text,
        candidate_filter=FakeCandidateFilter(db),
        import_mode_for_user=lambda user_uuid, *, current_time: "ai_validation",
        max_import_entries_per_submission=lambda: 100,
        log_pipeline_error=lambda **kwargs: None,
        validation_service=validation_service,
    )
    return BuiltUserImportServices(intake_service, manual_bind_service, intake_job_service, sync_processor, db, google_docs)


def parsed_word(value: str) -> ParsedImportWord:
    return ParsedImportWord(raw_value=value, lookup_word=value)


def test_submit_user_vocabulary_import_runs_manual_bind_success_flow(tmp_path: Path) -> None:
    validation_service = FakeValidationService()
    services = build_services(tmp_path, validation_service)
    current_time = datetime(2026, 4, 26, 2, 0, 0)
    import_screen_calls: list[dict[str, Any]] = []
    prepare_calls: list[dict[str, Any]] = []
    summary_calls: list[dict[str, Any]] = []

    def build_user_import_screen(
        telegram_user_id: int,
        locale: str,
        notice: str | None = None,
    ) -> ScreenModel:
        import_screen_calls.append(
            {"telegram_user_id": telegram_user_id, "locale": locale, "notice": notice}
        )
        return ScreenModel(screen_id="import", text=notice or "")

    def prepare_import_job_items(
        job: dict[str, Any],
        prepared_at: datetime,
        *,
        task_log_id: int | None = None,
    ) -> None:
        prepare_calls.append(
            {"job_id": job["id"], "prepared_at": prepared_at, "task_log_id": task_log_id}
        )
        for item in job["items"]:
            item["status"] = "queued_for_attributes"

    def build_user_import_summary_screen_for_user(
        telegram_user_id: int,
        locale: str,
        job_id: int,
        notice: str | None = None,
    ) -> ScreenModel:
        summary_calls.append(
            {
                "telegram_user_id": telegram_user_id,
                "locale": locale,
                "job_id": job_id,
                "notice": notice,
            }
        )
        return ScreenModel(screen_id=f"summary:{job_id}", text=notice or "")

    screen = services.intake_service.submit_user_vocabulary_import(
        user=TelegramUserContext(telegram_user_id=42, language_code="uk", raw_telegram_json="{}"),
        locale="uk",
        source_url="doc-id",
        current_time=current_time,
        build_user_import_screen=build_user_import_screen,
        prepare_import_job_items=prepare_import_job_items,
        build_user_import_summary_screen_for_user=build_user_import_summary_screen_for_user,
    )

    assert screen.screen_id == "summary:900"
    assert import_screen_calls == []
    assert services.google_docs.binding_calls == [
        {"telegram_user_id": 42, "doc_id": "doc-id", "current_time": current_time}
    ]
    assert services.google_docs.success_calls == [{"telegram_user_id": 42, "current_time": current_time}]

    assert len(services.db.task_logs.create_calls) == 1
    created_task_log = services.db.task_logs.create_calls[0]
    assert created_task_log["task_type"] == "bound_google_doc_sync"
    assert created_task_log["status"] == "processing"
    assert created_task_log["source_identifier"] == "doc-id"
    assert created_task_log["result_json"]["queued_lookup_words"] == ["extension cord"]
    assert created_task_log["result_json"]["invalid_fragments"] == [
        "annoying boss: Random descriptive collocation"
    ]

    assert prepare_calls == [{"job_id": 900, "prepared_at": current_time, "task_log_id": 1}]
    assert len(services.db.task_logs.update_calls) == 1
    updated_task_log = services.db.task_logs.update_calls[0]
    assert updated_task_log["status"] == "success"
    assert updated_task_log["import_job_id"] == 900
    assert updated_task_log["result_json"]["created_import_job_id"] == 900
    assert updated_task_log["result_json"]["queued_new_words_count"] == 1
    assert updated_task_log["result_json"]["queued_lookup_words"] == ["extension cord"]
    assert services.db.task_logs.rows[0]["status"] == "success"

    created_job = services.db.user_import_jobs.created_jobs[0]
    assert created_job["id"] == 900
    assert created_job["task_log_id"] == 1
    assert created_job["source_type"] == "bound_google_doc"
    assert created_job["source_identifier"] == "doc-id"
    assert created_job["items"][0]["lookup_word"] == "extension cord"
    assert created_job["items"][0]["status"] == "queued_for_attributes"
    assert created_job["status"] == "completed"
    assert created_job["summary_sent"] is True

    usage_call = validation_service.usage_calls[0]
    assert usage_call["task_scope"] == "telegram"
    assert usage_call["source_type"] == "bound_google_doc"
    assert usage_call["source_identifier"] == "doc-id"
    assert usage_call["import_job_id"] == 900
    assert usage_call["task_log_id"] == 1
    assert summary_calls[0]["job_id"] == 900


def test_submit_user_vocabulary_import_records_validation_when_no_words_survive(
    tmp_path: Path,
) -> None:
    validation_service = RejectingValidationService()
    services = build_services(tmp_path, validation_service)
    current_time = datetime(2026, 4, 26, 2, 0, 0)
    summary_calls: list[dict[str, Any]] = []

    screen = services.intake_service.submit_user_vocabulary_import(
        user=TelegramUserContext(telegram_user_id=42, language_code="uk", raw_telegram_json="{}"),
        locale="uk",
        source_url="doc-id",
        current_time=current_time,
        build_user_import_screen=lambda telegram_user_id, locale, notice=None: ScreenModel(
            screen_id="import",
            text=notice or "",
        ),
        prepare_import_job_items=lambda *args, **kwargs: None,
        build_user_import_summary_screen_for_user=lambda *args, **kwargs: summary_calls.append(
            {"args": args, "kwargs": kwargs}
        )
        or ScreenModel(screen_id="summary", text=""),
    )

    assert screen.screen_id == "import"
    assert screen.metadata["force_resend"] is True
    assert services.google_docs.binding_calls == [
        {"telegram_user_id": 42, "doc_id": "doc-id", "current_time": current_time}
    ]
    assert services.db.task_logs.rows == []
    assert services.db.user_import_jobs.created_jobs == []
    assert summary_calls == []
    usage_call = validation_service.usage_calls[0]
    assert usage_call["task_scope"] == "telegram"
    assert usage_call["import_job_id"] is None
    assert usage_call["task_log_id"] is None


def test_process_bound_google_doc_sync_row_rejects_ai_invalid_items_before_queue(tmp_path: Path) -> None:
    validation_service = FakeValidationService()
    services = build_services(tmp_path, validation_service)
    processor = services.sync_processor
    current_time = datetime(2026, 4, 26, 2, 0, 0)

    result = processor.process_bound_google_doc_sync_row(
        {"telegram_user_id": 42, "source_identifier": "doc-id"},
        current_time,
        task_log_id=5,
    )

    created_job = services.db.user_import_jobs.created_jobs[0]
    assert [item["lookup_word"] for item in created_job["items"]] == ["extension cord"]
    assert created_job["items"][0]["validated_part_of_speech"] == "noun"
    assert created_job["items"][0]["validated_translation_uk"] == "подовжувач"
    assert result["queued_new_words_count"] == 1
    assert result["invalid_fragments"] == ["annoying boss: Random descriptive collocation"]
    assert validation_service.usage_calls[0]["task_scope"] == "bound_google_doc_sync"
    assert validation_service.usage_calls[0]["import_job_id"] == 900
    assert services.google_docs.success_calls == [{"telegram_user_id": 42, "current_time": current_time}]


def test_bound_google_doc_sync_skips_assigned_words_before_ai_validation(tmp_path: Path) -> None:
    validation_service = RecordingValidationService()
    services = build_services(tmp_path, validation_service)
    processor = services.sync_processor
    db = services.db
    db.user_dictionary = SimpleNamespace(list_assigned_lookup_words_for_user=lambda user_uuid: {"extension cord"})
    current_time = datetime(2026, 4, 26, 2, 0, 0)

    result = processor.process_bound_google_doc_sync_row(
        {
            "telegram_user_id": 42,
            "user_uuid": "11111111-1111-4111-8111-111111111111",
            "source_identifier": "doc-id",
        },
        current_time,
        task_log_id=5,
    )

    assert validation_service.validated_batches == [["annoying boss"]]
    assert db.user_import_jobs.created_jobs[0]["items"][0]["lookup_word"] == "annoying boss"
    assert result["existing_lookup_words"] == ["extension cord"]


def test_bound_google_doc_sync_does_not_validate_when_progress_is_at_end(tmp_path: Path) -> None:
    validation_service = RecordingValidationService()
    services = build_services(tmp_path, validation_service)
    processor = services.sync_processor
    db = services.db
    google_docs = services.google_docs
    google_docs.progress = {
        "last_processed_line": 2,
        "last_processed_line_hash": line_hash("annoying boss - бесящий босс"),
        "last_processed_lookup_word": None,
    }
    current_time = datetime(2026, 4, 26, 2, 0, 0)

    result = processor.process_bound_google_doc_sync_row(
        {
            "telegram_user_id": 42,
            "user_uuid": "11111111-1111-4111-8111-111111111111",
            "source_identifier": "doc-id",
        },
        current_time,
        task_log_id=5,
    )

    assert validation_service.validated_batches == []
    assert validation_service.usage_calls == []
    assert db.user_import_jobs.created_jobs == []
    assert result["queued_new_words_count"] == 0
    assert result["created_import_job_id"] is None
    assert google_docs.success_calls == [{"telegram_user_id": 42, "current_time": current_time}]


def test_bound_google_doc_sync_does_not_validate_when_all_words_are_assigned(tmp_path: Path) -> None:
    validation_service = RecordingValidationService()
    services = build_services(tmp_path, validation_service)
    processor = services.sync_processor
    db = services.db
    google_docs = services.google_docs
    db.user_dictionary = SimpleNamespace(
        list_assigned_lookup_words_for_user=lambda user_uuid: {"extension cord", "annoying boss"}
    )
    current_time = datetime(2026, 4, 26, 2, 0, 0)

    result = processor.process_bound_google_doc_sync_row(
        {
            "telegram_user_id": 42,
            "user_uuid": "11111111-1111-4111-8111-111111111111",
            "source_identifier": "doc-id",
        },
        current_time,
        task_log_id=5,
    )

    assert validation_service.validated_batches == []
    assert validation_service.usage_calls == []
    assert db.user_import_jobs.created_jobs == []
    assert result["queued_new_words_count"] == 0
    assert result["existing_lookup_words"] == ["annoying boss", "extension cord"]
    assert google_docs.success_calls == [{"telegram_user_id": 42, "current_time": current_time}]


def test_create_user_import_job_normalizes_existing_lookup_words(tmp_path: Path) -> None:
    services = build_services(tmp_path, FakeValidationService())
    service = services.intake_service
    db = services.db
    db.user_import_jobs.existing_lookup_words = {"hello"}

    created_count, skipped_count, job_id = service.create_user_import_job_from_words(
        telegram_user_id=42,
        source_identifier="doc-id",
        parsed_words=[parsed_word("Hello")],
        current_time=datetime(2026, 4, 26, 2, 0, 0),
    )

    assert created_count == 0
    assert skipped_count == 1
    assert job_id is None
    assert db.user_import_jobs.created_jobs == []


def test_process_bound_google_doc_sync_row_uses_rescan_limit_and_resets_progress(tmp_path: Path) -> None:
    validation_service = RecordingValidationService()
    services = build_services(tmp_path, validation_service)
    processor = services.sync_processor
    db = services.db
    google_docs = services.google_docs
    google_docs.progress = {
        "last_processed_line": 20,
        "last_processed_line_hash": "old-hash",
        "last_processed_lookup_word": "old word",
    }
    processor.fetch_google_doc_text = lambda value: "\n".join(
        f"word {chr(97 + index // 26)}{chr(97 + index % 26)}" for index in range(150)
    )
    current_time = datetime(2026, 4, 26, 2, 0, 0)

    result = processor.process_bound_google_doc_sync_row(
        {
            "telegram_user_id": 42,
            "user_uuid": "11111111-1111-4111-8111-111111111111",
            "source_identifier": "doc-id",
        },
        current_time,
        task_log_id=5,
        max_import_entries=150,
        task_scope="post_upgrade_google_doc_rescan",
        restart_from_beginning=True,
    )

    assert result["queued_new_words_count"] == 150
    assert len(db.user_import_jobs.created_jobs[0]["items"]) == 150
    assert google_docs.clear_progress_calls == [
        {"telegram_user_id": 42, "doc_id": "doc-id", "current_time": current_time}
    ]
    assert google_docs.progress_calls[0]["last_processed_line"] == 150
