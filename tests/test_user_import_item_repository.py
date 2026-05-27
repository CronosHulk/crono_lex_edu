from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from uuid import UUID

from app.data_access.user_import_items import IMPORTED_PENDING_STATUSES, UserImportItemRepository
from app.data_access.user_import_serialization import ACTIVE_IMPORT_ITEM_STATUSES
from app.models import UserVocabularyImportItem

USER_UUID = UUID("11111111-1111-4111-8111-111111111111")


class FakeScalarsResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(self, *, row_by_id=None, scalars_rows=None) -> None:
        self.row_by_id = row_by_id or {}
        self.scalars_rows = list(scalars_rows or [])

    def get(self, model, primary_key):
        return self.row_by_id.get(primary_key)

    def scalars(self, statement):
        return FakeScalarsResult(self.scalars_rows)


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def make_item(**overrides) -> UserVocabularyImportItem:
    values = {
        "id": 3,
        "import_job_id": 9,
        "user_uuid": USER_UUID,
        "raw_value": "Carry on",
        "lookup_word": "carry on",
        "status": "pending",
        "error_text": "old",
        "existing_word_id": None,
        "user_dictionary_entry_id": None,
    }
    values.update(overrides)
    return UserVocabularyImportItem(**values)


def test_mark_existing_word_sets_item_to_found_existing_and_ignores_missing() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    item = make_item()
    repository = UserImportItemRepository(FakeSessionManager(FakeSession(row_by_id={3: item})))

    repository.mark_existing_word(3, word_id=501, current_time=current_time)
    repository.mark_existing_word(999, word_id=501, current_time=current_time)

    assert item.status == "found_existing"
    assert item.existing_word_id == 501
    assert item.user_dictionary_entry_id is None
    assert item.error_text is None
    assert item.processed == current_time
    assert item.updated == current_time


def test_imported_pending_statuses_exclude_failed_user_dictionary_builds() -> None:
    assert "details_failed" not in IMPORTED_PENDING_STATUSES
    assert "audio_failed" not in IMPORTED_PENDING_STATUSES
    assert "queued_for_details" in IMPORTED_PENDING_STATUSES
    assert "queued_for_audio" in IMPORTED_PENDING_STATUSES


def test_active_import_statuses_exclude_failed_user_dictionary_builds() -> None:
    assert "details_failed" not in ACTIVE_IMPORT_ITEM_STATUSES
    assert "audio_failed" not in ACTIVE_IMPORT_ITEM_STATUSES
    assert "embedding_failed" not in ACTIVE_IMPORT_ITEM_STATUSES
    assert "queued_for_details" in ACTIVE_IMPORT_ITEM_STATUSES
    assert "ready_for_rotation" in ACTIVE_IMPORT_ITEM_STATUSES


def test_list_by_user_dictionary_entry_returns_matching_item_payloads() -> None:
    item = make_item(status="ready_for_rotation", user_dictionary_entry_id=88)
    repository = UserImportItemRepository(FakeSessionManager(FakeSession(scalars_rows=[item])))

    payload = repository.list_by_user_dictionary_entry(88)

    assert payload[0]["id"] == 3
    assert payload[0]["user_dictionary_entry_id"] == 88
    assert payload[0]["status"] == "ready_for_rotation"


def test_mark_user_dictionary_entry_sets_user_entry_reference_and_status() -> None:
    current_time = datetime(2026, 5, 3, 10, 0, 0)
    item = make_item(existing_word_id=501)
    repository = UserImportItemRepository(FakeSessionManager(FakeSession(row_by_id={3: item})))

    repository.mark_user_dictionary_entry(
        3,
        user_dictionary_entry_id=88,
        status="ready_for_rotation",
        error_text=None,
        current_time=current_time,
    )
    repository.mark_user_dictionary_entry(
        999,
        user_dictionary_entry_id=88,
        status="ready_for_rotation",
        error_text=None,
        current_time=current_time,
    )

    assert item.status == "ready_for_rotation"
    assert item.existing_word_id is None
    assert item.user_dictionary_entry_id == 88
    assert item.error_text is None
    assert item.processed == current_time
    assert item.updated == current_time


def test_mark_rejected_sets_error_text_and_ignores_missing() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    item = make_item()
    repository = UserImportItemRepository(FakeSessionManager(FakeSession(row_by_id={3: item})))

    repository.mark_rejected(3, error_text="bad word", current_time=current_time)
    repository.mark_rejected(999, error_text="bad word", current_time=current_time)

    assert item.status == "rejected"
    assert item.error_text == "bad word"
    assert item.processed == current_time
    assert item.updated == current_time


def test_sync_for_user_dictionary_entry_updates_all_matching_items() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    first = make_item(id=3, user_dictionary_entry_id=88)
    second = make_item(id=4, user_dictionary_entry_id=88)
    repository = UserImportItemRepository(FakeSessionManager(FakeSession(scalars_rows=[first, second])))

    repository.sync_for_user_dictionary_entry(
        88,
        status="details_failed",
        error_text="provider failed",
        current_time=current_time,
    )

    assert [item.status for item in [first, second]] == ["details_failed", "details_failed"]
    assert [item.error_text for item in [first, second]] == ["provider failed", "provider failed"]
    assert [item.processed for item in [first, second]] == [current_time, current_time]
