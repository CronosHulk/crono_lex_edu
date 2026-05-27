from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

from app.data_access.user_import_jobs import UserImportJobRepository, normalize_filter_values
from app.models import User, UserVocabularyImportItem, UserVocabularyImportJob
from app.storage.audio import FileSystemAudioStorageProvider

USER_UUID = UUID("00000000-0000-0000-0000-000000000042")


class FakeAudioStorageProvider:
    def delete_if_under_roots(self, audio_path, audio_roots) -> bool:
        return False


def fake_user() -> User:
    return User(uuid=USER_UUID, telegram_user_id=42, status="active")


def fake_row_by_id(*, rows: dict | None = None, include_user: bool = True) -> dict:
    row_by_id = dict(rows or {})
    if include_user:
        row_by_id[(User, 42)] = fake_user()
    return row_by_id


class FakeScalarsResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeExecuteResult:
    def __init__(self, row) -> None:
        self.row = row

    def one(self):
        return self.row

    def all(self):
        return list(self.row)


class FakeSession:
    def __init__(self, *, row_by_id=None, scalars_rows=None, scalars_results=None, scalar_values=None, execute_row=None) -> None:
        self.row_by_id = row_by_id or {}
        self.scalars_rows = list(scalars_rows or [])
        self.scalars_results = list(scalars_results or [])
        self.scalar_values = list(scalar_values or [])
        self.execute_row = execute_row or (0, 0, 0)
        self.added = []
        self._next_id = 100

    def get(self, model, primary_key):
        return self.row_by_id.get((model, primary_key), self.row_by_id.get(primary_key))

    def scalars(self, statement):
        if self.scalars_results:
            return FakeScalarsResult(self.scalars_results.pop(0))
        return FakeScalarsResult(self.scalars_rows)

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else 0

    def execute(self, statement):
        return FakeExecuteResult(self.execute_row)

    def add(self, row) -> None:
        self.added.append(row)

    def flush(self) -> None:
        for row in self.added:
            if getattr(row, "id", None) is None:
                row.id = self._next_id
                self._next_id += 1


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def test_normalize_filter_values_handles_empty_value() -> None:
    assert normalize_filter_values(None) == []


def test_get_existing_lookup_words_normalizes_matches() -> None:
    session = FakeSession(row_by_id=fake_row_by_id(), scalars_rows=["Apple", "CARRY on"])
    repository = UserImportJobRepository(FakeSessionManager(session))

    assert repository.get_existing_lookup_words(telegram_user_id=42, lookup_words=[" apple ", "", "Carry On"]) == {
        "apple",
        "carry on",
    }


def test_get_existing_lookup_words_returns_empty_for_blank_input() -> None:
    repository = UserImportJobRepository(FakeSessionManager(FakeSession(scalars_rows=["ignored"])))

    assert repository.get_existing_lookup_words(telegram_user_id=42, lookup_words=["", "   "]) == set()


def test_create_job_persists_job_and_items() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    session = FakeSession(row_by_id=fake_row_by_id())
    repository = UserImportJobRepository(FakeSessionManager(session))

    payload = repository.create_job(
        telegram_user_id=42,
        source_type="google_doc",
        source_identifier="doc-1",
        storage_path="runtime/imports/doc.json",
        items=[
            {"raw_value": "Apple", "lookup_word": "apple"},
            {
                "raw_value": "Carry on",
                "lookup_word": "carry on",
                "translation_hint": "продовжувати",
                "validated_lookup_word": "to carry on",
                "validated_part_of_speech": "phrasal verb",
                "validated_translation_uk": "продовжувати",
            },
        ],
        current_time=current_time,
        task_log_id=7,
    )

    assert payload["id"] == 100
    assert payload["total_items"] == 2
    assert isinstance(session.added[0], UserVocabularyImportJob)
    assert [item.lookup_word for item in session.added[1:]] == ["apple", "carry on"]
    assert [item.import_job_id for item in session.added[1:]] == [100, 100]
    assert session.added[2].translation_hint == "продовжувати"
    assert session.added[2].validated_lookup_word == "to carry on"
    assert session.added[2].validated_part_of_speech == "phrasal verb"


def test_append_items_adds_rows_and_updates_job_total() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    row = UserVocabularyImportJob(id=9, user_uuid=USER_UUID, total_items=1)
    session = FakeSession(row_by_id=fake_row_by_id(rows={9: row}))
    repository = UserImportJobRepository(FakeSessionManager(session))

    repository.append_items(
        9,
        42,
        [
            {"raw_value": "Apple", "lookup_word": "apple"},
            {"raw_value": "Broken", "lookup_word": "broken", "status": "rejected", "error_text": "bad"},
        ],
        current_time,
        task_log_id=7,
    )

    assert row.total_items == 3
    assert row.updated == current_time
    assert [item.lookup_word for item in session.added] == ["apple", "broken"]
    assert [item.import_job_id for item in session.added] == [9, 9]
    assert session.added[0].task_log_id == 7
    assert session.added[1].processed == current_time


def test_delete_all_import_data_includes_google_doc_progress_and_bindings() -> None:
    session = FakeSession(scalar_values=[3, 2, 4, 6, 7, 8, 9, 5])
    repository = UserImportJobRepository(FakeSessionManager(session))

    assert repository.delete_all_import_data(audio_storage_provider=FakeAudioStorageProvider()) == {
        "deleted_import_items": 3,
        "deleted_import_jobs": 2,
        "deleted_google_doc_progress": 4,
        "cleared_google_doc_bindings": 5,
        "deleted_user_dictionary_entries": 6,
        "deleted_user_dictionary_embeddings": 7,
        "deleted_user_word_assignments": 8,
        "deleted_user_learning_session_words": 9,
        "deleted_user_audio_files": 0,
    }


def test_delete_all_import_data_deletes_user_audio_files_under_allowed_root(tmp_path: Path) -> None:
    audio_root = tmp_path / "word_base" / "user"
    audio_file = audio_root / "noun" / "apple.mp3"
    outside_file = tmp_path / "word_base" / "base" / "noun" / "keep.mp3"
    audio_file.parent.mkdir(parents=True)
    outside_file.parent.mkdir(parents=True)
    audio_file.write_bytes(b"user-audio")
    outside_file.write_bytes(b"core-audio")
    session = FakeSession(
        scalars_results=[["word_base/user/noun/apple.mp3", "word_base/base/noun/keep.mp3"]],
        scalar_values=[0, 0, 0, 1, 1, 0, 0, 0],
    )
    repository = UserImportJobRepository(FakeSessionManager(session))
    audio_storage_provider = FileSystemAudioStorageProvider(project_root=tmp_path)

    result = repository.delete_all_import_data(
        audio_storage_provider=audio_storage_provider,
        user_audio_roots=[audio_root],
    )

    assert result["deleted_user_audio_files"] == 1
    assert not audio_file.exists()
    assert outside_file.exists()


def test_claim_queued_marks_rows_processing() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    claimed_until = current_time + timedelta(minutes=30)
    row = UserVocabularyImportJob(id=9, user_uuid=USER_UUID, status="queued", summary_sent=False)
    repository = UserImportJobRepository(FakeSessionManager(FakeSession(execute_row=[(row, 42)])))

    payload = repository.claim_queued(current_time=current_time, claimed_until=claimed_until, limit=1)

    assert payload[0]["id"] == 9
    assert payload[0]["telegram_user_id"] == 42
    assert payload[0]["status"] == "processing"
    assert payload[0]["processing_claimed_until"] == claimed_until
    assert row.status == "processing"
    assert row.processing_claimed_until == claimed_until
    assert row.updated == current_time


def test_list_completed_pending_summary_returns_jobs() -> None:
    row = UserVocabularyImportJob(id=9, user_uuid=USER_UUID, status="completed", summary_sent=False)
    repository = UserImportJobRepository(FakeSessionManager(FakeSession(execute_row=[(row, 42)])))

    payload = repository.list_completed_pending_summary()

    assert payload[0]["id"] == 9
    assert payload[0]["telegram_user_id"] == 42
    assert payload[0]["status"] == "completed"


def test_mark_processing_updates_existing_row_and_ignores_missing_row() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    row = UserVocabularyImportJob(id=9, user_uuid=USER_UUID, status="queued", last_error="old")
    repository = UserImportJobRepository(FakeSessionManager(FakeSession(row_by_id={9: row})))

    repository.mark_processing(9, current_time)
    repository.mark_processing(999, current_time)

    assert row.status == "processing"
    assert row.processing_claimed_until == current_time
    assert row.last_error is None


def test_complete_updates_job_counts_and_status() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    row = UserVocabularyImportJob(id=9, user_uuid=USER_UUID, status="processing")
    session = FakeSession(row_by_id={9: row}, execute_row=(4, 3, 1))
    repository = UserImportJobRepository(FakeSessionManager(session))

    repository.complete(9, status="completed", current_time=current_time, last_error=None)

    assert row.total_items == 4
    assert row.processed_items == 4
    assert row.successful_items == 3
    assert row.failed_items == 1
    assert row.status == "completed"
    assert row.completed == current_time
    assert row.processing_claimed_until is None


def test_complete_ignores_missing_job() -> None:
    repository = UserImportJobRepository(FakeSessionManager(FakeSession()))

    repository.complete(999, status="completed", current_time=datetime(2026, 4, 26, 10, 0, 0))


def test_list_unfinished_items_returns_item_payloads() -> None:
    item = UserVocabularyImportItem(
        id=3,
        import_job_id=9,
        user_uuid=USER_UUID,
        raw_value="Apple",
        lookup_word="apple",
        status="pending",
        error_text="wait",
    )
    repository = UserImportJobRepository(FakeSessionManager(FakeSession(scalars_rows=[item])))

    payload = repository.list_unfinished_items(9)

    assert payload[0]["id"] == 3
    assert payload[0]["lookup_word"] == "apple"
    assert payload[0]["error_text"] == "wait"


def test_mark_summary_flags_update_rows() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    row = UserVocabularyImportJob(id=9, user_uuid=USER_UUID, status="completed")
    repository = UserImportJobRepository(FakeSessionManager(FakeSession(row_by_id={9: row})))

    repository.mark_summary_sent(9, current_time)
    repository.mark_publish_summary_sent(9, current_time)

    assert row.summary_sent is True
    assert row.publish_summary_sent is True
    assert row.updated == current_time


def test_summary_flags_ignore_missing_rows() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    repository = UserImportJobRepository(FakeSessionManager(FakeSession()))

    repository.mark_summary_sent(999, current_time)
    repository.mark_publish_summary_sent(999, current_time)


def test_list_completed_pending_publish_summary_returns_jobs() -> None:
    row = UserVocabularyImportJob(id=9, user_uuid=USER_UUID, status="completed", publish_summary_sent=False)
    repository = UserImportJobRepository(FakeSessionManager(FakeSession(execute_row=[(row, 42)])))

    payload = repository.list_completed_pending_publish_summary()

    assert payload[0]["id"] == 9
    assert payload[0]["telegram_user_id"] == 42
    assert payload[0]["status"] == "completed"


def test_list_items_and_get_job_return_payloads() -> None:
    job = UserVocabularyImportJob(id=9, user_uuid=USER_UUID, status="completed")
    item = UserVocabularyImportItem(
        id=3,
        import_job_id=9,
        user_uuid=USER_UUID,
        raw_value="Apple",
        lookup_word="apple",
        status="imported",
    )
    repository = UserImportJobRepository(FakeSessionManager(FakeSession(row_by_id={9: job}, scalars_rows=[item])))

    assert repository.get_job(9)["id"] == 9
    assert repository.get_job(999) is None
    assert repository.list_items(9)[0]["status"] == "imported"


def test_list_admin_jobs_returns_paginated_payload() -> None:
    row = UserVocabularyImportJob(id=9, user_uuid=USER_UUID, status="completed", source_type="google_doc")
    session = FakeSession(scalars_rows=[row], scalar_values=[1])
    repository = UserImportJobRepository(FakeSessionManager(session))

    payload = repository.list_admin_jobs(
        page=1,
        page_size=50,
        status="completed, failed",
        source_type=["google_doc"],
        user_id=str(USER_UUID),
        search="doc",
    )

    assert payload["items"][0]["id"] == 9
    assert payload["total"] == 1
    assert payload["pages"] == 1


def test_get_admin_job_filter_metadata_returns_distinct_options() -> None:
    session = FakeSession(scalars_results=[["completed", None], ["google_doc"]])
    repository = UserImportJobRepository(FakeSessionManager(session))

    payload = repository.get_admin_job_filter_metadata()

    assert payload["entity"] == "import_jobs"
    assert payload["filters"][1]["options"] == [{"value": "completed", "label": "completed"}]
    assert payload["filters"][2]["options"] == [{"value": "google_doc", "label": "google_doc"}]


def test_list_items_for_user_returns_user_scoped_items() -> None:
    item = UserVocabularyImportItem(
        id=3,
        import_job_id=9,
        user_uuid=USER_UUID,
        raw_value="Apple",
        lookup_word="apple",
        status="pending",
    )
    repository = UserImportJobRepository(FakeSessionManager(FakeSession(row_by_id=fake_row_by_id(), scalars_rows=[item])))

    payload = repository.list_items_for_user(telegram_user_id=42, job_id=9)

    assert payload[0]["id"] == 3
    assert payload[0]["lookup_word"] == "apple"


def test_list_all_items_for_user_paginated_returns_newest_items() -> None:
    item = UserVocabularyImportItem(
        id=3,
        import_job_id=9,
        user_uuid=USER_UUID,
        raw_value="Apple",
        lookup_word="apple",
        status="pending",
    )
    session = FakeSession(row_by_id=fake_row_by_id(), scalars_rows=[item], scalar_values=[1])
    repository = UserImportJobRepository(FakeSessionManager(session))

    payload = repository.list_all_items_for_user_paginated(telegram_user_id=42, page=1, page_size=20, status={"pending"})

    assert payload["items"][0]["id"] == 3
    assert payload["total"] == 1
    assert payload["pages"] == 1


def test_list_user_item_status_counts_returns_counts() -> None:
    repository = UserImportJobRepository(
        FakeSessionManager(FakeSession(row_by_id=fake_row_by_id(), execute_row=[("pending", 2), ("imported", 1)]))
    )

    assert repository.list_user_item_status_counts(telegram_user_id=42) == {"pending": 2, "imported": 1}


def test_list_admin_items_returns_paginated_payload() -> None:
    item = UserVocabularyImportItem(
        id=3,
        import_job_id=9,
        user_uuid=USER_UUID,
        raw_value="Apple",
        lookup_word="apple",
        status="imported",
        error_text=None,
    )
    session = FakeSession(scalars_rows=[item], scalar_values=[1])
    repository = UserImportJobRepository(FakeSessionManager(session))

    payload = repository.list_admin_items(
        page=1,
        page_size=50,
        status=["imported"],
        import_job_id=9,
        user_id=str(USER_UUID),
        search="apple",
    )

    assert payload["items"][0]["id"] == 3
    assert payload["items"][0]["lookup_word"] == "apple"
    assert payload["total"] == 1


def test_get_admin_item_filter_metadata_returns_distinct_options() -> None:
    session = FakeSession(scalars_rows=["imported", None])
    repository = UserImportJobRepository(FakeSessionManager(session))

    payload = repository.get_admin_item_filter_metadata()

    assert payload["entity"] == "import_items"
    options = payload["filters"][1]["options"]
    assert {"value": "imported", "label": "imported"} in options
    assert {"value": "ready_for_rotation", "label": "ready_for_rotation"} in options
    assert {"value": "details_failed", "label": "details_failed"} in options


def test_get_job_for_user_returns_matching_job_or_none() -> None:
    job = UserVocabularyImportJob(id=9, user_uuid=USER_UUID, status="completed")
    session = FakeSession(row_by_id=fake_row_by_id(), scalar_values=[job, None])
    repository = UserImportJobRepository(FakeSessionManager(session))

    assert repository.get_job_for_user(telegram_user_id=42, job_id=9)["id"] == 9
    assert repository.get_job_for_user(telegram_user_id=42, job_id=999) is None


def test_get_latest_job_for_user_returns_newest_job_or_none() -> None:
    job = UserVocabularyImportJob(id=10, user_uuid=USER_UUID, status="completed")
    session = FakeSession(row_by_id=fake_row_by_id(), scalar_values=[job, None])
    repository = UserImportJobRepository(FakeSessionManager(session))

    assert repository.get_latest_job_for_user(telegram_user_id=42)["id"] == 10
    assert repository.get_latest_job_for_user(telegram_user_id=777) is None
