from __future__ import annotations

import copy
from datetime import datetime
from typing import Any
from uuid import UUID

from app.user_import.services.preparation_service import UserImportPreparationService


class FakePendingWords(dict[str, dict[str, Any]]):
    def __init__(self, db: FakePreparationDb) -> None:
        super().__init__()
        self.db = db

    def find_by_word(self, word: str) -> dict[str, Any] | None:
        return copy.deepcopy(self.get(word.lower()))

    def create(self, **kwargs: Any) -> dict[str, Any]:
        row = {
            "id": self.db._pending_word_seq,
            "created": kwargs["current_time"],
            "updated": kwargs["current_time"],
            **kwargs,
        }
        self.db._pending_word_seq += 1
        self[str(kwargs["word"]).lower()] = row
        return copy.deepcopy(row)


class FakeUserProfiles:
    user_uuid = UUID("11111111-1111-4111-8111-111111111111")

    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        if telegram_user_id != 42:
            return None
        return {"user_id": str(self.user_uuid), "telegram_user_id": telegram_user_id}


class FakeUserDictionary(dict[str, dict[str, Any]]):
    def __init__(self) -> None:
        super().__init__()
        self.assignments: list[dict[str, Any]] = []
        self.created_entries: list[dict[str, Any]] = []
        self._entry_seq = 100

    def find_entry_by_word_and_part_of_speech(self, word: str, part_of_speech: str) -> dict[str, Any] | None:
        row = self.get(f"{word.lower()}::{part_of_speech}")
        return copy.deepcopy(row) if row is not None else None

    def create_entry(self, **kwargs: Any) -> dict[str, Any]:
        entry = {
            "id": self._entry_seq,
            "word": kwargs["word"],
            "part_of_speech": kwargs["part_of_speech"],
            "status": kwargs["status"],
            **kwargs,
        }
        self._entry_seq += 1
        self[f"{entry['word'].lower()}::{entry['part_of_speech']}"] = entry
        self.created_entries.append(entry)
        return copy.deepcopy(entry)

    def create_assignment(self, **kwargs: Any) -> dict[str, Any]:
        assignment = {"id": len(self.assignments) + 1, **kwargs}
        self.assignments.append(assignment)
        return copy.deepcopy(assignment)

    def count_entries_created_by_user_since(self, user_uuid: UUID, *, since: datetime) -> int:
        return sum(
            1
            for entry in self.created_entries
            if entry.get("created_by_user_uuid") == user_uuid and entry.get("created", since) >= since
        )


class FakePreparationAccessPolicy:
    def __init__(self) -> None:
        self.user_uuid = FakeUserProfiles.user_uuid
        self.lookup_only = True
        self.can_create = True
        self.telegram_user_lookup_calls: list[int] = []

    def user_uuid_for_telegram_user(self, telegram_user_id: int) -> UUID | None:
        self.telegram_user_lookup_calls.append(telegram_user_id)
        if telegram_user_id != 42:
            return None
        return self.user_uuid

    def is_lookup_only_import(self, user_uuid: UUID, *, current_time: datetime) -> bool:
        return self.lookup_only

    def can_create_new_user_dictionary_entry(self, user_uuid: UUID | None, *, current_time: datetime) -> bool:
        return self.can_create


class FakePreparationDb:
    def __init__(self) -> None:
        self.dictionary_entries_by_word: dict[str, dict[str, Any] | list[dict[str, Any]]] = {}
        self.pending_words: FakePendingWords = FakePendingWords(self)
        self.user_dictionary = FakeUserDictionary()
        self.user_profiles = FakeUserProfiles()
        self.access_policy = FakePreparationAccessPolicy()
        self.import_jobs: list[dict[str, Any]] = []
        self.priority_words: list[tuple[str | int, int, datetime | None]] = []
        self._pending_word_seq = 1

    def add_import_job(
        self,
        *,
        source_type: str = "google_doc",
        lookup_word: str = "apple",
        item_overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        job = {
            "id": 1,
            "telegram_user_id": 42,
            "source_type": source_type,
            "source_identifier": "source",
            "items": [
                {
                    "id": 11,
                    "status": "pending",
                    "lookup_word": lookup_word,
                    "existing_word_id": None,
                    "pending_word_id": None,
                    "user_dictionary_entry_id": None,
                    "error_text": None,
                    "processed": None,
                    **(item_overrides or {}),
                }
            ],
        }
        self.import_jobs.append(job)
        return copy.deepcopy({key: value for key, value in job.items() if key != "items"})

    @property
    def user_import_jobs(self) -> FakePreparationDb:
        return self

    @property
    def user_import_items(self) -> FakePreparationDb:
        return self

    def list_items(self, job_id: int) -> list[dict[str, Any]]:
        for job in self.import_jobs:
            if job["id"] == job_id:
                return copy.deepcopy(job["items"])
        return []

    @property
    def dictionary_lookup(self) -> FakePreparationDb:
        return self

    def find_by_word(self, word: str) -> dict[str, Any] | None:
        row = self.dictionary_entries_by_word.get(word.lower())
        if isinstance(row, list):
            row = row[0] if row else None
        return copy.deepcopy(row)

    def list_by_word(self, word: str) -> list[dict[str, Any]]:
        rows = self.dictionary_entries_by_word.get(word.lower())
        if rows is None:
            return []
        if isinstance(rows, list):
            return copy.deepcopy(rows)
        return [copy.deepcopy(rows)]

    def find_by_word_and_part_of_speech(self, word: str, part_of_speech: str | None) -> dict[str, Any] | None:
        rows = self.dictionary_entries_by_word.get(word.lower())
        if isinstance(rows, list):
            row = next(
                (
                    candidate
                    for candidate in rows
                    if not part_of_speech
                    or not candidate.get("part_of_speech")
                    or candidate.get("part_of_speech") == part_of_speech
                ),
                None,
            )
        else:
            row = rows
        if row is None:
            row = self.pending_words.get(word.lower())
            if row is None:
                return None
        if part_of_speech and row.get("part_of_speech") and row.get("part_of_speech") != part_of_speech:
            return None
        return copy.deepcopy(row)

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

    def mark_existing_word(self, item_id: int, *, word_id: int, current_time: datetime) -> None:
        item = self._find_item(item_id)
        item["status"] = "found_existing"
        item["existing_word_id"] = word_id
        item["pending_word_id"] = None
        item["user_dictionary_entry_id"] = None
        item["processed"] = current_time

    def mark_pending_word(
        self,
        item_id: int,
        *,
        pending_word_id: int,
        status: str,
        error_text: str | None,
        current_time: datetime,
    ) -> None:
        item = self._find_item(item_id)
        item["status"] = status
        item["existing_word_id"] = None
        item["pending_word_id"] = pending_word_id
        item["user_dictionary_entry_id"] = None
        item["error_text"] = error_text
        item["processed"] = current_time

    def mark_rejected(self, item_id: int, *, error_text: str, current_time: datetime) -> None:
        item = self._find_item(item_id)
        item["status"] = "rejected"
        item["error_text"] = error_text
        item["processed"] = current_time

    def mark_user_dictionary_entry(
        self,
        item_id: int,
        *,
        user_dictionary_entry_id: int,
        status: str,
        error_text: str | None,
        current_time: datetime,
    ) -> None:
        item = self._find_item(item_id)
        item["status"] = status
        item["existing_word_id"] = None
        item["pending_word_id"] = None
        item["user_dictionary_entry_id"] = user_dictionary_entry_id
        item["error_text"] = error_text
        item["processed"] = current_time

    def _find_item(self, item_id: int) -> dict[str, Any]:
        for job in self.import_jobs:
            for item in job["items"]:
                if item["id"] == item_id:
                    return item
        raise AssertionError(f"missing item {item_id}")


def build_service(
    db: FakePreparationDb,
    access_policy: FakePreparationAccessPolicy | None = None,
) -> UserImportPreparationService:
    return UserImportPreparationService(db, access_policy or db.access_policy)


def grant_premium_import(db: FakePreparationDb) -> None:
    db.access_policy.lookup_only = False


def test_prepare_import_job_items_marks_existing_dictionary_word() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakePreparationDb()
    db.dictionary_entries_by_word["apple"] = {"id": 77, "word": "apple"}
    job = db.add_import_job(lookup_word="Apple")

    build_service(db).prepare_import_job_items(job, current_time, task_log_id=5)

    item = db.import_jobs[0]["items"][0]
    assert item["status"] == "found_existing"
    assert item["existing_word_id"] == 77
    assert item["processed"] == current_time
    assert db.priority_words == [(str(FakeUserProfiles.user_uuid), 77, current_time)]
    assert db.user_dictionary.assignments[0]["user_uuid"] == FakeUserProfiles.user_uuid
    assert db.user_dictionary.assignments[0]["word_source"] == "core"
    assert db.user_dictionary.assignments[0]["word_id"] == 77
    assert db.pending_words == {}


def test_prepare_import_job_items_uses_job_user_uuid_before_profile_lookup() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakePreparationDb()
    db.dictionary_entries_by_word["apple"] = {"id": 77, "word": "apple"}
    job_user_uuid = UUID("22222222-2222-4222-8222-222222222222")
    job = db.add_import_job(lookup_word="Apple")
    job["user_uuid"] = str(job_user_uuid)

    build_service(db).prepare_import_job_items(job, current_time, task_log_id=5)

    assert db.access_policy.telegram_user_lookup_calls == []
    assert db.priority_words == [(str(job_user_uuid), 77, current_time)]
    assert db.user_dictionary.assignments[0]["user_uuid"] == job_user_uuid


def test_prepare_lookup_only_import_adds_all_dictionary_matches_without_part_of_speech() -> None:
    current_time = datetime(2026, 5, 3, 10, 0, 0)
    db = FakePreparationDb()
    db.dictionary_entries_by_word["record"] = [
        {"id": 77, "word": "record", "part_of_speech": "noun"},
        {"id": 78, "word": "record", "part_of_speech": "verb"},
        {"id": 79, "word": "record", "part_of_speech": "adjective"},
    ]
    job = db.add_import_job(source_type="client_web_lookup", lookup_word="Record")

    build_service(db).prepare_import_job_items(job, current_time, task_log_id=5)

    item = db.import_jobs[0]["items"][0]
    assert item["status"] == "found_existing"
    assert item["existing_word_id"] == 77
    assert db.priority_words == [
        (str(FakeUserProfiles.user_uuid), 77, current_time),
        (str(FakeUserProfiles.user_uuid), 78, current_time),
        (str(FakeUserProfiles.user_uuid), 79, current_time),
    ]
    assert [assignment["word_id"] for assignment in db.user_dictionary.assignments] == [77, 78, 79]
    assert {assignment["status"] for assignment in db.user_dictionary.assignments} == {"available_for_rotation"}


def test_prepare_import_job_items_reuses_ready_user_dictionary_entry() -> None:
    current_time = datetime(2026, 5, 3, 10, 0, 0)
    db = FakePreparationDb()
    grant_premium_import(db)
    db.user_dictionary["extension cord::noun"] = {
        "id": 88,
        "word": "extension cord",
        "part_of_speech": "noun",
        "status": "ready_for_rotation",
    }
    job = db.add_import_job(
        lookup_word="extension cord",
        item_overrides={"validated_part_of_speech": "noun"},
    )

    build_service(db).prepare_import_job_items(job, current_time, task_log_id=5)

    item = db.import_jobs[0]["items"][0]
    assert item["status"] == "ready_for_rotation"
    assert item["existing_word_id"] is None
    assert item["pending_word_id"] is None
    assert item["user_dictionary_entry_id"] == 88
    assert db.user_dictionary.assignments[0]["user_uuid"] == FakeUserProfiles.user_uuid
    assert db.user_dictionary.assignments[0]["word_source"] == "user"
    assert db.user_dictionary.assignments[0]["word_id"] == 88
    assert db.user_dictionary.assignments[0]["status"] == "available_for_rotation"
    assert db.pending_words == {}


def test_prepare_import_job_items_waits_for_building_user_dictionary_entry() -> None:
    current_time = datetime(2026, 5, 3, 10, 0, 0)
    db = FakePreparationDb()
    grant_premium_import(db)
    db.user_dictionary["extension cord::noun"] = {
        "id": 88,
        "word": "extension cord",
        "part_of_speech": "noun",
        "status": "queued_for_audio",
    }
    job = db.add_import_job(
        lookup_word="extension cord",
        item_overrides={"validated_part_of_speech": "noun"},
    )

    build_service(db).prepare_import_job_items(job, current_time, task_log_id=5)

    item = db.import_jobs[0]["items"][0]
    assert item["status"] == "waiting_for_user_dictionary_entry"
    assert item["user_dictionary_entry_id"] == 88
    assert db.user_dictionary.assignments[0]["status"] == "waiting_for_entry"
    assert db.pending_words == {}


def test_prepare_import_job_items_creates_waiting_user_dictionary_entry_for_regular_import() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakePreparationDb()
    grant_premium_import(db)
    job = db.add_import_job(
        source_type="google_doc",
        lookup_word="apple",
        item_overrides={"validated_part_of_speech": "noun"},
    )

    build_service(db).prepare_import_job_items(job, current_time, task_log_id=5)

    item = db.import_jobs[0]["items"][0]
    entry = db.user_dictionary.created_entries[0]
    assert entry["word"] == "apple"
    assert entry["part_of_speech"] == "noun"
    assert entry["status"] == "queued_for_details"
    assert item["status"] == "waiting_for_user_dictionary_entry"
    assert item["pending_word_id"] is None
    assert item["user_dictionary_entry_id"] == entry["id"]
    assert db.user_dictionary.assignments[0]["word_source"] == "user"
    assert db.user_dictionary.assignments[0]["word_id"] == entry["id"]
    assert db.user_dictionary.assignments[0]["status"] == "waiting_for_entry"
    assert db.pending_words == {}


def test_prepare_import_job_items_rejects_new_word_without_validated_part_of_speech() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakePreparationDb()
    grant_premium_import(db)
    job = db.add_import_job(source_type="bound_google_doc", lookup_word="apple")

    build_service(db).prepare_import_job_items(job, current_time, task_log_id=None)

    item = db.import_jobs[0]["items"][0]
    assert item["status"] == "rejected"
    assert item["error_text"] == "part_of_speech is required for user dictionary import"
    assert db.pending_words == {}
    assert db.user_dictionary.created_entries == []


def test_prepare_lookup_only_import_rejects_words_missing_from_dictionary() -> None:
    current_time = datetime(2026, 5, 3, 10, 0, 0)
    db = FakePreparationDb()
    db.access_policy.lookup_only = True
    job = db.add_import_job(source_type="client_web_google_doc", lookup_word="missing word")

    build_service(db).prepare_import_job_items(job, current_time, task_log_id=None)

    item = db.import_jobs[0]["items"][0]
    assert item["status"] == "rejected"
    assert item["error_text"] == (
        "Smart import is not available on the free account. "
        "Upgrade your plan for deeper AI analysis of new words."
    )
    assert db.user_dictionary.created_entries == []
    assert db.user_dictionary.assignments == []


def test_prepare_import_job_items_defers_client_web_attribute_build() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakePreparationDb()
    grant_premium_import(db)
    job = db.add_import_job(source_type="client_web_txt", lookup_word="apple")

    build_service(db).prepare_import_job_items(job, current_time, task_log_id=None)

    item = db.import_jobs[0]["items"][0]
    assert item["status"] == "rejected"
    assert item["error_text"] == "part_of_speech is required for user dictionary import"


def test_prepare_import_job_items_uses_ai_validated_translation_and_part_of_speech() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakePreparationDb()
    grant_premium_import(db)
    job = db.add_import_job(
        source_type="client_web_txt",
        lookup_word="extension cord",
        item_overrides={
            "translation_hint": "удлинитель",
            "validated_part_of_speech": "noun",
            "validated_translation_uk": "подовжувач",
            "validated_translation_ru": "удлинитель",
        },
    )

    build_service(db).prepare_import_job_items(job, current_time, task_log_id=None)

    entry = db.user_dictionary.created_entries[0]
    assert entry["part_of_speech"] == "noun"
    assert entry["translation_uk"] == "подовжувач"
    assert entry["translation_ru"] == "удлинитель"
    assert entry["source_provider_status_json"]["import_validation"]["part_of_speech"] is True


def test_prepare_import_job_items_uses_ai_validated_lookup_word() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakePreparationDb()
    grant_premium_import(db)
    job = db.add_import_job(
        source_type="client_web_txt",
        lookup_word="enroll",
        item_overrides={
            "validated_lookup_word": "to enroll",
            "validated_part_of_speech": "verb",
            "validated_translation_uk": "записатися",
        },
    )

    build_service(db).prepare_import_job_items(job, current_time, task_log_id=None)

    entry = db.user_dictionary.created_entries[0]
    assert entry["word"] == "to enroll"
    assert entry["part_of_speech"] == "verb"
    assert entry["source_provider_status_json"]["import_validation"]["lookup_word"] is True


def test_prepare_import_job_items_matches_existing_dictionary_word_by_part_of_speech() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakePreparationDb()
    grant_premium_import(db)
    db.dictionary_entries_by_word["record"] = {"id": 77, "word": "record", "part_of_speech": "noun"}
    job = db.add_import_job(
        lookup_word="record",
        item_overrides={"validated_part_of_speech": "verb", "validated_translation_uk": "записувати"},
    )

    build_service(db).prepare_import_job_items(job, current_time, task_log_id=5)

    item = db.import_jobs[0]["items"][0]
    assert item["status"] == "waiting_for_user_dictionary_entry"
    assert item["existing_word_id"] is None
    assert db.user_dictionary.created_entries[0]["part_of_speech"] == "verb"


def test_prepare_import_job_items_rejects_new_word_when_custom_weekly_quota_is_exhausted() -> None:
    current_time = datetime(2026, 5, 6, 10, 0, 0)
    db = FakePreparationDb()
    grant_premium_import(db)
    db.access_policy.can_create = False
    for index in range(50):
        db.user_dictionary.created_entries.append(
            {
                "id": index + 1,
                "word": f"word {index}",
                "created_by_user_uuid": FakeUserProfiles.user_uuid,
                "created": datetime(2026, 5, 4, 8, 0, 0),
            }
        )
    job = db.add_import_job(
        lookup_word="fresh word",
        item_overrides={"validated_part_of_speech": "noun"},
    )

    build_service(db).prepare_import_job_items(job, current_time, task_log_id=None)

    item = db.import_jobs[0]["items"][0]
    assert item["status"] == "rejected"
    assert item["error_text"] == "weekly new word import quota exceeded"
