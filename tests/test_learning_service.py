from __future__ import annotations

import copy
from datetime import datetime, timedelta
from pathlib import Path

from app.application.client_learning.content import build_fill_in_gap_example
from app.composition.root import build_learning_runtime
from app.contracts import TelegramUserContext
from app.time_utils import TimeService
from app.user_import.runtime_settings import (
    DEFAULT_IMPORT_RUNTIME_SETTINGS,
)


def identity_quiz_queue_randomizer(queue: list[int]) -> list[int]:
    return list(queue)


def build_service(
    db: FakeDatabase,
    time_service: object | None = None,
    *,
    quiz_queue_randomizer=identity_quiz_queue_randomizer,
) -> object:
    return build_learning_runtime(
        db,
        time_service or TimeService("Europe/Kyiv"),
        quiz_queue_randomizer=quiz_queue_randomizer,
    )


def build_alpha_word(index: int) -> str:
    value = index
    chars: list[str] = []
    while value > 0:
        value, remainder = divmod(value - 1, 26)
        chars.append(chr(ord("a") + remainder))
    return "word" + "".join(reversed(chars))


class FixedTimeService:
    def __init__(self, current_time: datetime) -> None:
        self._current_time = current_time

    def now(self) -> datetime:
        return self._current_time

    def format_datetime(self, value: datetime | None) -> str:
        if value is None:
            return "-"
        return value.strftime("%Y-%m-%d %H:%M:%S")


class CapturingUserImportRuntimeService:
    def __init__(self) -> None:
        self.calls: list[datetime] = []
        self.due_import_calls = 0

    def process_user_import_attribute_queue_now(self, current_time: datetime) -> None:
        self.calls.append(current_time)

    def process_due_user_vocabulary_imports(self) -> list[str]:
        self.due_import_calls += 1
        return ["processed"]


class FakeTaskLogRepository(list[dict[str, object]]):
    def __init__(self, db: FakeDatabase) -> None:
        super().__init__()
        self.db = db

    def create(self, **kwargs):
        row = {
            "id": self.db._task_log_seq,
            "task_type": kwargs["task_type"],
            "status": kwargs["status"],
            "telegram_user_id": kwargs.get("telegram_user_id"),
            "source_type": kwargs.get("source_type"),
            "source_identifier": kwargs.get("source_identifier"),
            "import_job_id": kwargs.get("import_job_id"),
            "description": kwargs.get("description"),
            "error_text": kwargs.get("error_text"),
            "result_json": copy.deepcopy(kwargs.get("result_json") or {}),
            "started": kwargs["current_time"],
            "finished": kwargs["current_time"] if kwargs["status"] in {"success", "error", "fatal"} else None,
            "created": kwargs["current_time"],
            "updated": kwargs["current_time"],
        }
        self.db._task_log_seq += 1
        self.append(row)
        return copy.deepcopy(row)

    def update(self, task_log_id, **kwargs):
        for row in self:
            if row["id"] != task_log_id:
                continue
            row["status"] = kwargs["status"]
            row["description"] = kwargs.get("description")
            row["error_text"] = kwargs.get("error_text")
            row["result_json"] = copy.deepcopy(kwargs.get("result_json") or {})
            row["import_job_id"] = kwargs.get("import_job_id")
            row["updated"] = kwargs["current_time"]
            row["finished"] = kwargs["current_time"] if kwargs["status"] in {"success", "error", "fatal"} else None
            return copy.deepcopy(row)
        return None

    def get(self, task_log_id: int):
        for row in self:
            if row["id"] == task_log_id:
                return copy.deepcopy(row)
        return None

    def get_latest_for_import_job(self, import_job_id: int, *, task_type: str | None = None):
        matches = [
            row
            for row in self
            if row.get("import_job_id") == import_job_id and (task_type is None or row.get("task_type") == task_type)
        ]
        if not matches:
            return None
        matches.sort(key=lambda row: (row["created"], row["id"]), reverse=True)
        return copy.deepcopy(matches[0])


class FakeBotMessageLogRepository:
    def __init__(self, db: FakeDatabase) -> None:
        self.db = db

    def create(
        self,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
        screen_id: str,
        delete_after,
        current_time,
    ):
        payload = {
            "telegram_user_id": telegram_user_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "screen_id": screen_id,
            "delete_after": delete_after,
            "current_time": current_time,
        }
        self.db.created_bot_messages.append(payload)
        return {"id": 901, **payload}

    def claim_due_cleanup(self, current_time, retry_before):
        return [
            {
                "id": 901,
                "telegram_user_id": 1,
                "chat_id": 99,
                "message_id": 501,
                "screen_id": "menu",
                "current_time": current_time,
                "retry_before": retry_before,
            }
        ]

    def get_latest_for_message(self, telegram_user_id: int, chat_id: int, message_id: int):
        for row in reversed(self.db.created_bot_messages):
            if (
                row["telegram_user_id"] == telegram_user_id
                and row["chat_id"] == chat_id
                and row["message_id"] == message_id
            ):
                return {"id": 901, **row}
        return None

    def list_active(self, telegram_user_id: int, chat_id: int):
        return [
            {"id": 901 + index, **row}
            for index, row in enumerate(self.db.created_bot_messages)
            if row["telegram_user_id"] == telegram_user_id and row["chat_id"] == chat_id
        ]

    def save_cleanup_result(self, message_log_id: int, *, is_deleted: bool, current_time, error_text=None) -> None:
        self.db.cleanup_results.append(
            {
                "message_log_id": message_log_id,
                "is_deleted": is_deleted,
                "current_time": current_time,
                "error_text": error_text,
            }
        )


class FakeAdminAuthRepository:
    def __init__(self, db: FakeDatabase) -> None:
        self.db = db

    def create_magic_link(self, **kwargs):
        row = {"id": len(self.db.admin_magic_links) + 1, **kwargs}
        self.db.admin_magic_links.append(copy.deepcopy(row))
        return copy.deepcopy(row)

    def schedule_bot_restore(self, **kwargs):
        self.db.restores.append(copy.deepcopy(kwargs))
        return {"id": len(self.db.restores), **kwargs}

    def claim_due_bot_restores(self, *, current_time, limit=50):
        return []

    def mark_bot_restore_failed(self, restore_id: int, *, error_text: str, current_time) -> None:
        self.db.restores.append(
            {
                "id": restore_id,
                "status": "failed",
                "error_text": error_text,
                "current_time": current_time,
            }
        )


class FakeLearningLevelRepository:
    def __init__(self, db: FakeDatabase) -> None:
        self.db = db

    def list_language_levels(self) -> list[dict[str, object]]:
        return self.db.list_language_levels()

    def save_language_level(self, telegram_user_id: int, level_title: str) -> None:
        self.db.save_language_level(telegram_user_id, level_title)

    def get_active(self, telegram_user_id: int, level_id: int):
        return self.db.get_active_level_run(telegram_user_id, level_id)

    def get_latest(self, telegram_user_id: int, level_id: int):
        return self.db.get_latest_level_run(telegram_user_id, level_id)

    def create(self, telegram_user_id: int, level_id: int):
        return self.db.create_level_run(telegram_user_id, level_id)

    def complete(self, level_run_id: int, current_time=None) -> None:
        self.db.complete_level_run(level_run_id, current_time)


class FakePendingWordRepository(dict[str, dict[str, object]]):
    def __init__(self, db: FakeDatabase) -> None:
        super().__init__()
        self.db = db

    def create(self, **kwargs):
        word_key = kwargs["word"].lower()
        row = self.get(word_key)
        if row is None:
            row = {
                "id": self.db._pending_word_seq,
                "created": kwargs.get("current_time"),
                "updated": kwargs.get("current_time"),
                **kwargs,
            }
            self.db._pending_word_seq += 1
            self[word_key] = row
        else:
            row.update(kwargs)
            row["updated"] = kwargs.get("current_time")
        return copy.deepcopy(row)

    def reject(
        self,
        pending_word_ids: list[int],
        *,
        rejected_reason: str,
        admin_telegram_user_id: int,
        current_time,
    ) -> None:
        pending_id_set = {int(value) for value in pending_word_ids}
        for row in self.values():
            if row["id"] not in pending_id_set:
                continue
            row["status"] = "rejected"
            row["rejected_reason"] = rejected_reason
            row["approved_by_telegram_user_id"] = admin_telegram_user_id
            row["approved"] = current_time
            row["updated"] = current_time

    def approve_for_audio(self, pending_word_ids: list[int], *, admin_telegram_user_id: int, current_time) -> None:
        pending_id_set = {int(value) for value in pending_word_ids}
        for row in self.values():
            if row["id"] not in pending_id_set:
                continue
            row["status"] = "approved"
            row["approved_by_telegram_user_id"] = admin_telegram_user_id
            row["approved"] = current_time
            row["rejected_reason"] = None
            row["updated"] = current_time

    def find_by_word(self, word: str):
        return copy.deepcopy(self.get(word.lower()))

    def list_for_review(self, *, limit: int):
        rows = [
            row for row in self.values()
            if row.get("status") in {"ready_for_attribute_review", "ready_for_review"}
        ]
        rows.sort(key=lambda row: (row["created"], row["id"]))
        return copy.deepcopy(rows[:limit])

    def get_by_ids(self, pending_word_ids: list[int]):
        pending_id_set = {int(value) for value in pending_word_ids}
        rows = [row for row in self.values() if row["id"] in pending_id_set]
        rows.sort(key=lambda row: row["id"])
        return copy.deepcopy(rows)

    def list_for_attribute_build(self, *, limit: int | None, submitted_by_telegram_user_id: int | None = None):
        rows = [
            row for row in self.values()
            if row.get("status") in {"queued_for_attributes", "collecting", "build_failed"}
        ]
        if submitted_by_telegram_user_id is not None:
            rows = [
                row
                for row in rows
                if row.get("submitted_by_telegram_user_id") == submitted_by_telegram_user_id
            ]
        rows.sort(key=lambda row: (row["created"], row["id"]))
        return copy.deepcopy(rows if limit is None else rows[:limit])

    def mark_collecting(self, pending_word_id: int, *, task_log_id: int, current_time: datetime) -> None:
        for row in self.values():
            if row["id"] != pending_word_id:
                continue
            row["status"] = "collecting"
            row["task_log_id"] = task_log_id
            row["build_started"] = row.get("build_started") or current_time
            row["build_completed"] = None
            row["build_last_error"] = None
            row["build_next_retry_at"] = None
            row["updated"] = current_time

    def list_for_audio_build(self, *, limit: int):
        rows = [row for row in self.values() if row.get("status") == "approved"]
        rows.sort(key=lambda row: (row.get("approved") or row["created"], row["id"]))
        return copy.deepcopy(rows[:limit])

    def list_for_embedding_build(self, *, limit: int):
        rows = [
            row
            for row in self.values()
            if row.get("status") == "ready_for_embedding" or (row.get("status") == "ready_for_publish" and not row.get("is_embedding_ready"))
        ]
        rows.sort(key=lambda row: (row.get("approved") or row["created"], row["id"]))
        return copy.deepcopy(rows[:limit])

    def list_for_publish(self, *, limit: int):
        rows = [
            row
            for row in self.values()
            if row.get("status") == "ready_for_publish" and bool(row.get("is_embedding_ready"))
        ]
        rows.sort(key=lambda row: (row.get("approved") or row["created"], row["id"]))
        return copy.deepcopy(rows[:limit])

    def update_audio_path(self, pending_word_id: int, *, audio_path: str, current_time):
        for row in self.values():
            if row["id"] != pending_word_id:
                continue
            row["audio_path"] = audio_path
            row["updated"] = current_time
            return copy.deepcopy(row)
        return None


class FakeUserDictionaryRepository:
    def __init__(self) -> None:
        self.entries: dict[int, dict[str, object]] = {}
        self.assignments: list[dict[str, object]] = []
        self._entry_seq = 1

    def list_entries_by_status(self, status: str, *, limit: int) -> list[dict[str, object]]:
        rows = [row for row in self.entries.values() if row.get("status") == status]
        rows.sort(key=lambda row: int(row["id"]))
        return copy.deepcopy(rows[:limit])

    def update_entry_status(self, entry_id: int, *, status: str, current_time) -> None:
        row = self.entries.get(entry_id)
        if row is not None:
            row["status"] = status
            row["updated"] = current_time

    def update_entry_details(self, entry_id: int, **kwargs) -> None:
        row = self.entries.setdefault(entry_id, {"id": entry_id})
        row.update(kwargs)

    def update_entry_audio(self, entry_id: int, **kwargs) -> None:
        row = self.entries.setdefault(entry_id, {"id": entry_id})
        row.update(kwargs)

    def update_entry_embedding(self, entry_id: int, **kwargs) -> None:
        row = self.entries.setdefault(entry_id, {"id": entry_id})
        row.update(kwargs)

    def mark_assignments_available_for_entry(self, entry_id: int, *, current_time) -> None:
        row = self.entries.get(entry_id)
        if row is not None:
            row["assignments_available_at"] = current_time
        for assignment in self.assignments:
            if assignment["word_source"] == "user" and assignment["word_id"] == entry_id:
                assignment["status"] = "available_for_rotation"
                assignment["updated"] = current_time

    def create_assignment(self, **kwargs) -> dict[str, object]:
        row = {"id": len(self.assignments) + 1, **kwargs}
        self.assignments.append(row)
        return copy.deepcopy(row)

    def create_entry(self, **kwargs) -> dict[str, object]:
        row = {"id": self._entry_seq, **kwargs}
        self._entry_seq += 1
        self.entries[int(row["id"])] = row
        return copy.deepcopy(row)

    def find_entry_by_word_and_part_of_speech(self, word: str, part_of_speech: str | None):
        normalized_word = word.lower()
        normalized_pos = str(part_of_speech or "").lower()
        for row in self.entries.values():
            if str(row.get("word") or "").lower() != normalized_word:
                continue
            if normalized_pos and str(row.get("part_of_speech") or "").lower() != normalized_pos:
                continue
            return copy.deepcopy(row)
        return None

    def find_entry_by_word(self, word: str):
        normalized_word = word.lower()
        for row in self.entries.values():
            if str(row.get("word") or "").lower() == normalized_word:
                return copy.deepcopy(row)
        return None

    def count_entries_created_by_user_since(self, user_uuid, *, since) -> int:
        return sum(
            1
            for row in self.entries.values()
            if row.get("created_by_user_uuid") == user_uuid and (row.get("created") or row.get("current_time") or since) >= since
        )


class FakeAppSettings:
    def __init__(self) -> None:
        self.rows: dict[str, object] = {}

    def get_value(self, key: str):
        return copy.deepcopy(self.rows.get(key))


class FakeSubscriptionsRepository:
    def __init__(self) -> None:
        self.rows_by_user_uuid: dict[str, dict[str, object]] = {}

    def get_by_user_uuid(self, user_uuid: str) -> dict[str, object] | None:
        key = str(user_uuid)
        row = self.rows_by_user_uuid.get(key)
        if row is not None:
            return copy.deepcopy(row)
        return {
            "user_uuid": key,
            "plan_key": "premium",
            "status": "active",
            "start": datetime(2024, 1, 1, 0, 0, 0),
            "end": None,
        }

    def set_plan_for_user(self, user_uuid: str, *, plan_key: str, current_time: datetime) -> dict[str, object]:
        row = {
            "user_uuid": str(user_uuid),
            "plan_key": str(plan_key),
            "status": "active",
            "start": current_time,
            "end": None,
        }
        self.rows_by_user_uuid[str(user_uuid)] = copy.deepcopy(row)
        return copy.deepcopy(row)


class FakeBillingRepository:
    def __init__(self) -> None:
        self.monobank_audit_logs: list[dict[str, object]] = []

    def create_monobank_audit_log(self, **kwargs):
        self.monobank_audit_logs.append(copy.deepcopy(kwargs))
        return copy.deepcopy(kwargs)

    def get_subscription_projection_for_user(self, user_uuid: str, *, current_time: datetime):
        return None

    def list_client_payments_for_user(self, user_uuid: str, *, page: int, page_size: int) -> dict[str, object]:
        return {"items": [], "page": page, "page_size": page_size, "total": 0}


class FakeDatabase:
    def __init__(self) -> None:
        self._learning_levels_repository = FakeLearningLevelRepository(self)
        self.language_levels = [
            {"id": 1, "title": "A1", "description": None},
            {"id": 2, "title": "A2", "description": None},
            {"id": 3, "title": "B1", "description": None},
            {"id": 4, "title": "B2", "description": None},
            {"id": 5, "title": "C1", "description": None},
            {"id": 6, "title": "C2", "description": None},
        ]
        self.settings = type(
            "Settings",
            (),
            {
                "app_bot_message_retention_days": 30,
                "app_user_import_storage_dir": "runtime/test_user_imports",
                "app_user_import_audio_dir": "word_base/user",
                "app_dictionary_audio_dir": "word_base/base",
                "app_user_import_max_words_per_bind": 100,
                "app_user_import_wordnik_limit_per_run": 90,
                "app_user_import_audio_build_hour": 10,
                "app_user_import_embedding_build_hour": 11,
                "app_user_import_test_mode": False,
                "app_user_import_google_tts_language_code": "en-US",
                "app_user_import_google_tts_voice_name": "en-US-Neural2-F",
                "app_user_import_embeddings_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                "app_user_import_embeddings_device": "cpu",
                "app_web_base_url": "https://cronolex.local",
                "app_billing_receipt_storage_dir": "runtime/test_billing_receipts",
                "app_admin_magic_link_ttl_minutes": 5,
            },
        )()
        self.billing = FakeBillingRepository()
        self._subscriptions_repository = FakeSubscriptionsRepository()
        self.saved_events: list[dict[str, object]] = []
        self.saved_levels: list[str] = []
        self.saved_word_counts: list[int] = []
        self.progress_updates: list[dict[str, object]] = []
        self.word_progress: dict[tuple[int, int], dict[str, object]] = {}
        self.google_doc_progress: dict[tuple[int, str], dict[str, object]] = {}
        self.priority_words: list[tuple[int, int]] = []
        self.language_levels = [
            {"id": 1, "title": "A1", "description": None},
            {"id": 2, "title": "A2", "description": None},
            {"id": 3, "title": "B1", "description": None},
            {"id": 4, "title": "B2", "description": None},
            {"id": 5, "title": "C1", "description": None},
            {"id": 6, "title": "C2", "description": None},
        ]
        self.profile = {
            "telegram_user_id": 1,
            "id": "00000000-0000-4000-8000-000000000001",
            "user_id": "00000000-0000-4000-8000-000000000001",
            "first_name": "Олена",
            "username": None,
            "acl_group_title": "student",
            "language_level_id": 1,
            "language_level_title": "A1",
            "words_per_session": 10,
            "daily_reminder_hour": None,
            "reminder_weekdays": [],
            "reminder_schedule": [],
            "preferred_gender": None,
            "import_google_doc_id": None,
            "is_import_google_doc_auto_sync_enabled": False,
            "import_google_doc_last_synced": None,
            "import_google_doc_last_error": None,
            "import_google_doc_retry_count": 0,
            "import_google_doc_next_retry_at": None,
            "import_google_doc_claimed_until": None,
            "chat_id": 55,
            "language_code": "uk",
        }
        self.level_runs: dict[int, dict[str, object]] = {
            1: {"id": 1, "telegram_user_id": 1, "level_id": 1, "run_no": 1, "status": "active", "completed": None}
        }
        self._active_level_runs: dict[tuple[int, int], int] = {(1, 1): 1}
        self._level_run_seq = 2
        self.session = None
        self.session_words = [
            {
                "session_word_id": 11,
                "session_id": 77,
                "word_id": 101,
                "word_source": "core",
                "item_order": 1,
                "card_status": "pending",
                "en_uk_attempts": 0,
                "en_uk_correct": False,
                "uk_en_attempts": 0,
                "uk_en_correct": False,
                "gap_attempts": 0,
                "gap_correct": False,
                "word": "learn",
                "part_of_speech": "verb",
                "parts_of_speech": ["verb"],
                "categories": ["general", "study"],
                "phonetic_us": "/lɜːrn/",
                "audio_path": "word_base/word_audio/2994_learning.mp3",
                "examples_json": ["We learn every day."],
                "translation_uk": "вивчати",
                "level_id": 1,
            },
            {
                "session_word_id": 12,
                "session_id": 77,
                "word_id": 102,
                "word_source": "core",
                "item_order": 2,
                "card_status": "pending",
                "en_uk_attempts": 0,
                "en_uk_correct": False,
                "uk_en_attempts": 0,
                "uk_en_correct": False,
                "gap_attempts": 0,
                "gap_correct": False,
                "word": "read",
                "part_of_speech": "verb",
                "parts_of_speech": ["verb"],
                "categories": ["general"],
                "phonetic_us": "/riːd/",
                "audio_path": "word_base/word_audio/4260_read.mp3",
                "examples_json": ["I read the text aloud."],
                "translation_uk": "читати",
                "level_id": 1,
            },
        ]
        self.extra_lesson_words = [
            {
                "id": 103,
                "word_source": "core",
                "word": "write",
                "translation_uk": "писати",
                "examples_json": ["Write it down."],
                "audio_path": "word_base/word_audio/5918_write.mp3",
                "part_of_speech": "verb",
                "parts_of_speech": ["verb"],
                "categories": ["general", "writing"],
                "phonetic_us": "/raɪt/",
                "level_id": 1,
                "review_priority": 0,
                "is_priority": False,
            }
        ]
        self.extra_word_progress: dict[int, dict[str, object]] = {}
        self.active_session = None
        self._learning_sessions: dict[int, dict[str, object]] = {}
        self.existing_schedules: dict[object, dict[str, object]] = {}
        self.due_schedules: list[dict[str, object]] = []
        self.summary_completed = datetime(2026, 4, 6, 10, 0, 0)
        self.updated_schedule_statuses: list[tuple[int, str]] = []
        self.completed_due_schedule_calls: list[dict[str, object]] = []
        self.created_bot_messages: list[dict[str, object]] = []
        self.cleanup_results: list[dict[str, object]] = []
        self.bot_message_logs = FakeBotMessageLogRepository(self)
        self._admin_auth_repository = FakeAdminAuthRepository(self)
        self.restores: list[dict[str, object]] = []
        self.next_training_schedule: dict[str, object] | None = None
        self.import_jobs: list[dict[str, object]] = []
        self.pending_words: FakePendingWordRepository = FakePendingWordRepository(self)
        self.user_dictionary = FakeUserDictionaryRepository()
        self.dictionary_entries_by_word: dict[str, dict[str, object]] = {}
        self.summary_counts_override: dict[str, int] | None = {"learned_count": 20, "in_progress_count": 6, "needs_work_count": 4}
        self._import_job_seq = 1
        self._import_item_seq = 1
        self._pending_word_seq = 1
        self._task_log_seq = 1
        self.runtime_state: dict[str, dict[str, object]] = {}
        self.app_settings = FakeAppSettings()
        self.task_logs = FakeTaskLogRepository(self)
        self.admin_magic_links: list[dict[str, object]] = []

    @property
    def learning_levels(self):
        return self._learning_levels_repository

    @property
    def user_profiles(self):
        return self

    @property
    def subscriptions(self):
        return self._subscriptions_repository

    @property
    def user_import_google_docs(self):
        return self

    @property
    def user_import_jobs(self):
        return self

    @property
    def user_import_items(self):
        return self

    @property
    def dictionary_lookup(self):
        return self

    @property
    def dictionary_publish(self):
        return self

    @property
    def dictionary_audio(self):
        return self

    @property
    def user_learning_settings(self):
        return self

    @property
    def learning_sessions(self):
        return self

    @property
    def learning_progress(self):
        return self

    @property
    def lesson_word_selection(self):
        return self

    @property
    def similar_words(self):
        return self

    @property
    def training_schedules(self):
        return self

    @property
    def admin_auth(self):
        return self._admin_auth_repository

    @property
    def admin_users(self):
        return self

    @property
    def error_logs(self):
        return self

    @property
    def acl_permissions(self):
        return self

    def _progress_row(self, level_run_id: int, word_id: int) -> dict[str, object] | None:
        row = self.word_progress.get((level_run_id, word_id))
        if row is not None:
            normalized = copy.deepcopy(row)
            normalized.setdefault("level_run_id", level_run_id)
            return normalized
        legacy = self.word_progress.get(word_id)
        if legacy is None:
            return None
        normalized = copy.deepcopy(legacy)
        normalized.setdefault("level_run_id", level_run_id)
        return normalized

    def upsert_user(self, payload: dict[str, object]) -> None:
        self.profile["telegram_user_id"] = payload["telegram_user_id"]
        if payload.get("first_name"):
            self.profile["first_name"] = payload["first_name"]
        if "username" in payload:
            self.profile["username"] = payload.get("username")
            username = str(payload.get("username") or "").strip().lower().lstrip("@")
            self.profile["acl_group_title"] = "super_admin" if username == "cronoshulk" else "student"

    def save_user_event(self, **kwargs) -> None:
        self.saved_events.append(kwargs)

    def get_user_profile(self, telegram_user_id: int) -> dict[str, object]:
        return copy.deepcopy(self.profile)

    def get_profile(self, telegram_user_id: int) -> dict[str, object]:
        return self.get_user_profile(telegram_user_id)

    def is_super_admin(self, telegram_user_id: int) -> bool:
        return self.profile.get("acl_group_title") == "super_admin"

    def can_access(self, telegram_user_id: int, *, action: str, environment: str) -> bool:
        if self.profile.get("telegram_user_id") != telegram_user_id:
            return False
        if environment != "telegram_user":
            return False
        super_admin_actions = {
            "import_review/open_menu",
            "import_review/open",
            "import_review/approve",
            "import_review/reject",
            "import_review/delete",
            "import_review/regenerate",
        }
        return self.profile.get("acl_group_title") == "super_admin" and action in super_admin_actions

    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None:
        if group_title == "super_admin" and environment == "web_admin" and action == "auth/login":
            return "enabled"
        return None

    def list_group_capabilities(self, *, group_title: str, environment: str) -> list[str]:
        if group_title == "super_admin" and environment == "web_admin":
            return ["auth/login"]
        return []

    def get_admin_user_by_id(self, telegram_user_id: int) -> dict[str, object] | None:
        return self.get_by_id(telegram_user_id)

    def get_by_id(self, telegram_user_id: int) -> dict[str, object] | None:
        if self.profile.get("telegram_user_id") != telegram_user_id:
            return None
        return copy.deepcopy(self.profile)

    def list_super_admin_profiles(self):
        if self.profile.get("acl_group_title") != "super_admin" or self.profile.get("chat_id") is None:
            return []
        return [copy.deepcopy(self.profile)]

    def get_active_session(self, telegram_user_id: int):
        if self.active_session is None:
            return None
        session = copy.deepcopy(self.active_session)
        session.setdefault(
            "level_run_id",
            self._active_level_runs.get((telegram_user_id, int(session.get("language_level_id", 0)))) or 1,
        )
        return session

    def get_learning_session(self, session_id: int):
        if self.active_session and self.active_session["id"] == session_id:
            session = copy.deepcopy(self.active_session)
            session["completed"] = self.summary_completed
            session.setdefault(
                "level_run_id",
                self._active_level_runs.get((session["telegram_user_id"], int(session.get("language_level_id", 0)))) or 1,
            )
            return session
        if session_id in self._learning_sessions:
            session = copy.deepcopy(self._learning_sessions[session_id])
            session["completed"] = self.summary_completed
            session.setdefault(
                "level_run_id",
                self._active_level_runs.get((session["telegram_user_id"], int(session.get("language_level_id", 0)))) or 1,
            )
            return session
        return None

    def get_session(self, session_id: int):
        return self.get_learning_session(session_id)

    def replace_session_word(self, session_word_id: int, word_id: int, *, word_source: str = "core") -> None:
        self.replace_learning_session_word(session_word_id, word_id)

    def update(self, telegram_user_id: int, word_id: int, *, level_run_id: int, **kwargs) -> None:
        self.update_assignment_progress(telegram_user_id, word_id, level_run_id=level_run_id, **kwargs)

    def list_language_levels(self) -> list[dict[str, object]]:
        return copy.deepcopy(self.language_levels)

    def save_language_level(self, telegram_user_id: int, level_title: str) -> None:
        self.saved_levels.append(level_title)
        self.profile["language_level_title"] = level_title
        level = next((item for item in self.language_levels if item["title"] == level_title), None)
        if level is not None:
            self.profile["language_level_id"] = level["id"]

    def get_active_level_run(self, telegram_user_id: int, level_id: int):
        run_id = self._active_level_runs.get((telegram_user_id, level_id))
        if run_id is None:
            return None
        return copy.deepcopy(self.level_runs[run_id])

    def get_latest_level_run(self, telegram_user_id: int, level_id: int):
        rows = [
            row for row in self.level_runs.values()
            if row["telegram_user_id"] == telegram_user_id and row["level_id"] == level_id
        ]
        if not rows:
            return None
        return copy.deepcopy(sorted(rows, key=lambda item: (item["run_no"], item["id"]))[-1])

    def create_level_run(self, telegram_user_id: int, level_id: int):
        active_run_id = self._active_level_runs.pop((telegram_user_id, level_id), None)
        if active_run_id is not None:
            self.level_runs[active_run_id]["status"] = "abandoned"
            self.level_runs[active_run_id]["completed"] = datetime(2026, 4, 8, 10, 0, 0)
        latest = self.get_latest_level_run(telegram_user_id, level_id)
        row = {
            "id": self._level_run_seq,
            "telegram_user_id": telegram_user_id,
            "level_id": level_id,
            "run_no": (latest["run_no"] if latest is not None else 0) + 1,
            "status": "active",
            "completed": None,
        }
        self.level_runs[self._level_run_seq] = row
        self._active_level_runs[(telegram_user_id, level_id)] = self._level_run_seq
        self._level_run_seq += 1
        return copy.deepcopy(row)

    def ensure_active_level_run(self, telegram_user_id: int, level_id: int):
        row = self.get_active_level_run(telegram_user_id, level_id)
        if row is not None:
            return row
        return self.create_level_run(telegram_user_id, level_id)

    def complete_level_run(self, level_run_id: int, current_time) -> None:
        row = self.level_runs.get(level_run_id)
        if row is None:
            return
        row["status"] = "completed"
        row["completed"] = current_time
        key = (row["telegram_user_id"], row["level_id"])
        if self._active_level_runs.get(key) == level_run_id:
            self._active_level_runs.pop(key, None)

    def set_words_per_session(self, telegram_user_id: int, words_per_session: int) -> None:
        self.saved_word_counts.append(words_per_session)
        self.profile["words_per_session"] = words_per_session

    def set_daily_reminder_hour(self, telegram_user_id: int, daily_reminder_hour: int | None) -> None:
        self.profile["daily_reminder_hour"] = daily_reminder_hour
        weekdays = list(self.profile.get("reminder_weekdays") or [])
        self.profile["reminder_schedule"] = [
            {"weekday": weekday, "hour": daily_reminder_hour, "status": "enabled"}
            for weekday in weekdays
            if daily_reminder_hour is not None
        ]

    def list_reminder_schedule(self, telegram_user_id: int) -> list[dict[str, object]]:
        return copy.deepcopy(self.profile["reminder_schedule"])

    def replace_reminder_schedule(
        self,
        telegram_user_id: int,
        schedule_rows: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        self.profile["reminder_schedule"] = sorted(
            [dict(row) for row in schedule_rows],
            key=lambda row: (int(row["weekday"]), int(row["hour"])),
        )
        enabled_rows = [row for row in self.profile["reminder_schedule"] if row["status"] == "enabled"]
        self.profile["daily_reminder_hour"] = int(enabled_rows[0]["hour"]) if enabled_rows else None
        self.profile["reminder_weekdays"] = sorted({int(row["weekday"]) for row in enabled_rows})
        return copy.deepcopy(self.profile["reminder_schedule"])

    @property
    def user_import_google_docs(self):
        return self

    def _google_doc_progress_key(self, telegram_user_id: int, doc_id: str) -> tuple[int, str]:
        return (telegram_user_id, doc_id)

    def get_progress(self, telegram_user_id: int, doc_id: str):
        return copy.deepcopy(self.google_doc_progress.get(self._google_doc_progress_key(telegram_user_id, doc_id)))

    def mark_progress(
        self,
        telegram_user_id: int,
        doc_id: str,
        *,
        current_time,
        last_processed_line,
        last_processed_line_hash,
        last_processed_lookup_word,
    ) -> None:
        self.google_doc_progress[self._google_doc_progress_key(telegram_user_id, doc_id)] = {
            "telegram_user_id": telegram_user_id,
            "google_doc_id": doc_id,
            "last_processed_line": last_processed_line,
            "last_processed_line_hash": last_processed_line_hash,
            "last_processed_lookup_word": last_processed_lookup_word,
            "last_synced": current_time,
        }

    def set_binding(self, telegram_user_id: int, doc_id: str, current_time) -> None:
        self.profile["import_google_doc_id"] = doc_id
        self.profile["is_import_google_doc_auto_sync_enabled"] = True
        self.profile["import_google_doc_last_error"] = None
        self.profile["import_google_doc_retry_count"] = 0
        self.profile["import_google_doc_next_retry_at"] = None
        self.profile["import_google_doc_claimed_until"] = None
        self.profile["updated"] = current_time

    def claim_due_syncs(self, current_time, sync_hour, sync_interval_days, claimed_until, sync_weekdays=None, limit=None):
        if not self.profile.get("is_import_google_doc_auto_sync_enabled") or not self.profile.get("import_google_doc_id"):
            return []
        current_claim = self.profile.get("import_google_doc_claimed_until")
        if current_claim is not None and current_claim > current_time:
            return []
        last_synced = self.profile.get("import_google_doc_last_synced")
        next_retry_at = self.profile.get("import_google_doc_next_retry_at")
        is_retry_due = (
            self.profile.get("import_google_doc_retry_count", 0) > 0
            and self.profile.get("import_google_doc_retry_count", 0) <= 3
            and next_retry_at is not None
            and next_retry_at <= current_time
        )
        is_weekday_due = sync_weekdays is not None and current_time.hour == sync_hour and current_time.weekday() in set(sync_weekdays) and (
            last_synced is None or last_synced.date() < current_time.date()
        )
        is_interval_due = sync_weekdays is None and current_time.hour == sync_hour and (
            last_synced is None
            or last_synced <= current_time - timedelta(days=max(int(sync_interval_days), 1))
        )
        if not is_retry_due and not is_weekday_due and not is_interval_due:
            return []
        self.profile["import_google_doc_claimed_until"] = claimed_until
        rows = [
            {
                "telegram_user_id": self.profile["telegram_user_id"],
                "chat_id": self.profile["chat_id"],
                "language_code": self.profile["language_code"],
                "source_identifier": self.profile["import_google_doc_id"],
                "last_synced": last_synced,
                "last_error": self.profile.get("import_google_doc_last_error"),
                "retry_count": self.profile.get("import_google_doc_retry_count", 0),
                "next_retry_at": next_retry_at,
            }
        ]
        if limit is not None:
            return rows[:limit]
        return rows

    def mark_sync_success(self, telegram_user_id: int, *, current_time) -> None:
        self.profile["import_google_doc_last_synced"] = current_time
        self.profile["import_google_doc_last_error"] = None
        self.profile["import_google_doc_retry_count"] = 0
        self.profile["import_google_doc_next_retry_at"] = None
        self.profile["import_google_doc_claimed_until"] = None

    def mark_sync_failure(self, telegram_user_id: int, *, current_time, error_text=None, retry_count=0, next_retry_at=None) -> None:
        self.profile["import_google_doc_last_error"] = error_text
        self.profile["import_google_doc_retry_count"] = retry_count
        self.profile["import_google_doc_next_retry_at"] = next_retry_at
        self.profile["import_google_doc_claimed_until"] = None
        if next_retry_at is None:
            self.profile["import_google_doc_last_synced"] = current_time

    def get_reminder_weekdays(self, telegram_user_id: int) -> list[int]:
        return list(self.profile["reminder_weekdays"])

    def set_reminder_weekdays(self, telegram_user_id: int, weekdays: list[int]) -> None:
        self.profile["reminder_weekdays"] = sorted(set(weekdays))
        hours = sorted({int(row["hour"]) for row in self.profile["reminder_schedule"] if row["status"] == "enabled"})
        if not hours and self.profile["daily_reminder_hour"] is not None:
            hours = [int(self.profile["daily_reminder_hour"])]
        self.profile["reminder_schedule"] = [
            {"weekday": weekday, "hour": hour, "status": "enabled"}
            for weekday in self.profile["reminder_weekdays"]
            for hour in hours
        ]

    def clear_daily_reminder_settings(self, telegram_user_id: int) -> None:
        self.profile["daily_reminder_hour"] = None
        self.profile["reminder_weekdays"] = []
        self.profile["reminder_schedule"] = []

    def clear_binding(self, telegram_user_id: int, current_time) -> None:
        self.profile["import_google_doc_id"] = None
        self.profile["is_import_google_doc_auto_sync_enabled"] = False
        self.profile["import_google_doc_last_synced"] = None
        self.profile["import_google_doc_last_error"] = None
        self.profile["import_google_doc_retry_count"] = 0
        self.profile["import_google_doc_next_retry_at"] = None

    def cancel_active_sessions(self, telegram_user_id: int) -> None:
        self.active_session = None

    def complete_due_training_schedules(self, telegram_user_id: int, current_time, *, exclude_schedule_id=None) -> None:
        self.completed_due_schedule_calls.append(
            {
                "telegram_user_id": telegram_user_id,
                "current_time": current_time,
                "exclude_schedule_id": exclude_schedule_id,
            }
        )

    def complete_due(self, telegram_user_id: int, current_time, *, exclude_schedule_id=None) -> None:
        self.complete_due_training_schedules(
            telegram_user_id,
            current_time,
            exclude_schedule_id=exclude_schedule_id,
        )

    def select_lesson_words(self, telegram_user_id: int, level_id: int, words_limit: int):
        rows = [row for row in self.session_words if str(row.get("audio_path") or "").strip()]
        return copy.deepcopy(rows[:words_limit])

    def select_followup_words(self, source_session_id: int):
        return [
            {
                "id": row["word_id"],
                "word": row["word"],
                "translation_uk": row["translation_uk"],
                "examples_json": row["examples_json"],
                "audio_path": row["audio_path"],
                "part_of_speech": row["part_of_speech"],
                "parts_of_speech": row.get("parts_of_speech") or [row["part_of_speech"]],
                "categories": row.get("categories") or [],
                "phonetic_us": row["phonetic_us"],
                "level_id": row["level_id"],
                "review_priority": 0,
            }
            for row in copy.deepcopy(self.session_words)
            if row.get("card_status") != "known"
        ]

    def select_next_lesson_word(
        self,
        telegram_user_id: int,
        level_id: int,
        excluded_word_ids: list[int],
        excluded_words: list[dict[str, object]] | None = None,
    ):
        ordered_rows = sorted(
            self.extra_lesson_words,
            key=lambda row: (0 if row.get("is_priority") else 1, row["id"]),
        )
        excluded_pairs = {
            (str(row.get("word_source") or "core"), int(row["word_id"]))
            for row in (excluded_words or [])
        }
        for row in ordered_rows:
            progress = self.extra_word_progress.get(row["id"])
            word_source = str(row.get("word_source") or "core")
            if (
                row["id"] not in excluded_word_ids
                and (word_source, int(row["id"])) not in excluded_pairs
                and row["level_id"] == level_id
                and progress is None
                and str(row.get("audio_path") or "").strip()
            ):
                return copy.deepcopy(row)
        return None

    def create_learning_session(
        self,
        telegram_user_id: int,
        level_id: int,
        level_run_id: int | None,
        words_target_count: int,
        words,
        *,
        session_type: str = "regular",
        source_session_id: int | None = None,
    ):
        self.active_session = {
            "id": 77,
            "telegram_user_id": telegram_user_id,
            "language_level_id": level_id,
            "level_run_id": level_run_id,
            "source_session_id": source_session_id,
            "session_type": session_type,
            "words_target_count": words_target_count,
            "status": "active",
            "current_stage": "card",
            "stage_queue_json": [],
            "stage_position": 0,
        }
        self._learning_sessions[77] = copy.deepcopy(self.active_session)
        return copy.deepcopy(self.active_session)

    def create_session(self, **kwargs):
        return self.create_learning_session(**kwargs)

    def get_session_words(self, session_id: int):
        return copy.deepcopy(self.session_words)

    def update_session_state(self, session_id: int, current_stage: str, stage_queue: list[int], stage_position: int) -> None:
        self.active_session["current_stage"] = current_stage
        self.active_session["stage_queue_json"] = list(stage_queue)
        self.active_session["stage_position"] = stage_position
        self._learning_sessions[self.active_session["id"]] = copy.deepcopy(self.active_session)

    def get_session_word(self, session_word_id: int):
        for word in self.session_words:
            if word["session_word_id"] == session_word_id:
                return copy.deepcopy(word)
        return None

    def set_card_status(self, session_word_id: int, status: str) -> None:
        for word in self.session_words:
            if word["session_word_id"] == session_word_id:
                word["card_status"] = status

    def append_learning_session_word(self, session_id: int, word_id: int):
        match = next((row for row in self.extra_lesson_words if row["id"] == word_id), None)
        if match is None:
            return None
        next_session_word_id = max(row["session_word_id"] for row in self.session_words) + 1
        appended = {
            "session_word_id": next_session_word_id,
            "session_id": session_id,
            "word_id": match["id"],
            "word_source": match.get("word_source", "core"),
            "item_order": max(row["item_order"] for row in self.session_words) + 1,
            "card_status": "pending",
            "en_uk_attempts": 0,
            "en_uk_correct": False,
            "uk_en_attempts": 0,
            "uk_en_correct": False,
            "gap_attempts": 0,
            "gap_correct": False,
            "word": match["word"],
            "part_of_speech": match["part_of_speech"],
            "parts_of_speech": match.get("parts_of_speech") or [match["part_of_speech"]],
            "categories": match.get("categories") or [],
            "phonetic_us": match["phonetic_us"],
            "audio_path": match["audio_path"],
            "examples_json": match["examples_json"],
            "translation_uk": match["translation_uk"],
            "level_id": match["level_id"],
        }
        self.session_words.append(appended)
        return copy.deepcopy(appended)

    def replace_learning_session_word(self, session_word_id: int, word_id: int):
        match = next((row for row in self.extra_lesson_words if row["id"] == word_id), None)
        if match is None:
            return None
        for word in self.session_words:
            if word["session_word_id"] != session_word_id:
                continue
            word["word_id"] = match["id"]
            word["word_source"] = match.get("word_source", "core")
            word["card_status"] = "pending"
            word["en_uk_attempts"] = 0
            word["en_uk_correct"] = False
            word["uk_en_attempts"] = 0
            word["uk_en_correct"] = False
            word["gap_attempts"] = 0
            word["gap_correct"] = False
            word["word"] = match["word"]
            word["part_of_speech"] = match["part_of_speech"]
            word["parts_of_speech"] = match.get("parts_of_speech") or [match["part_of_speech"]]
            word["categories"] = match.get("categories") or []
            word["phonetic_us"] = match["phonetic_us"]
            word["audio_path"] = match["audio_path"]
            word["examples_json"] = match["examples_json"]
            word["translation_uk"] = match["translation_uk"]
            word["level_id"] = match["level_id"]
            return copy.deepcopy(word)
        return None

    def update_assignment_progress(self, telegram_user_id: int, word_id: int, *, level_run_id: int, **kwargs) -> None:
        self.progress_updates.append(
            {"telegram_user_id": telegram_user_id, "word_id": word_id, "level_run_id": level_run_id, **kwargs}
        )
        key = (level_run_id, word_id)
        row = self._progress_row(level_run_id, word_id) or {
            "level_run_id": level_run_id,
            "telegram_user_id": telegram_user_id,
            "word_id": word_id,
            "is_known": False,
            "learning_state": "learning",
            "control_success_streak": 0,
            "review_priority": 0,
            "last_completed": None,
            "next_review_at": None,
        }
        if "is_known" in kwargs and kwargs["is_known"] is not None:
            row["is_known"] = kwargs["is_known"]
        if "learning_state" in kwargs and kwargs["learning_state"] is not None:
            row["learning_state"] = kwargs["learning_state"]
        if "control_success_streak" in kwargs and kwargs["control_success_streak"] is not None:
            row["control_success_streak"] = kwargs["control_success_streak"]
        if kwargs.get("review_priority_delta"):
            row["review_priority"] = max(int(row["review_priority"]) + int(kwargs["review_priority_delta"]), 0)
        if kwargs.get("completed_now"):
            row["last_completed"] = kwargs.get("current_time")
        if "next_review_at" in kwargs and kwargs["next_review_at"] is not None:
            row["next_review_at"] = kwargs["next_review_at"]
        self.word_progress[key] = row

    def get_assignment_progress(self, word_id: int, *, level_run_id: int):
        row = self._progress_row(level_run_id, word_id)
        return copy.deepcopy(row) if row is not None else None

    def get(self, item_id: int, *, level_run_id: int | None = None, word_source: str = "core"):
        if level_run_id is not None:
            return self.get_assignment_progress(item_id, level_run_id=level_run_id)
        return self.get_training_schedule(item_id)

    def find_similar_words(
        self,
        word_id: int,
        level_id: int,
        excluded_word_ids: list[int],
        limit: int,
        *,
        telegram_user_id: int | None = None,
        word_source: str = "core",
        excluded_words: list[dict[str, object]] | None = None,
    ):
        return [
            {
                "id": 201,
                "word": "study",
                "translation_uk": "навчатися",
                "examples_json": ["Study more."],
                "audio_path": "word_base/word_audio/5107_stuff.mp3",
                "part_of_speech": "verb",
                "phonetic_us": "/x/",
            },
            {
                "id": 202,
                "word": "write",
                "translation_uk": "писати",
                "examples_json": ["Write it down."],
                "audio_path": "word_base/word_audio/5918_write.mp3",
                "part_of_speech": "verb",
                "phonetic_us": "/x/",
            },
            {
                "id": 203,
                "word": "listen",
                "translation_uk": "слухати",
                "examples_json": ["Listen carefully."],
                "audio_path": "word_base/word_audio/3078_listen.mp3",
                "part_of_speech": "verb",
                "phonetic_us": "/x/",
            },
        ][:limit]

    def record_answer(self, **kwargs) -> None:
        self.saved_events.append({"answer": kwargs})

    def create_user_core_word_assignment(self, telegram_user_id: int, word_id: int, *, current_time=None) -> None:
        payload = (telegram_user_id, word_id)
        if payload not in self.priority_words:
            self.priority_words.append(payload)

    def find_dictionary_entry_by_word(self, word: str):
        return copy.deepcopy(self.dictionary_entries_by_word.get(word.lower()))

    def find_by_word(self, word: str):
        return self.find_dictionary_entry_by_word(word)

    def list_by_word(self, word: str):
        row = self.find_dictionary_entry_by_word(word)
        return [] if row is None else [row]

    def find_by_word_and_part_of_speech(self, word: str, part_of_speech: str | None):
        row = self.find_dictionary_entry_by_word(word)
        if row is None:
            row = self.pending_words.get(word.lower())
            if row is None:
                return None
        if part_of_speech and row.get("part_of_speech") and row.get("part_of_speech") != part_of_speech:
            return None
        return copy.deepcopy(row)

    def get_existing_user_import_lookup_words(self, telegram_user_id: int, lookup_words: list[str]):
        return self.get_existing_lookup_words(telegram_user_id, lookup_words)

    def get_existing_lookup_words(self, telegram_user_id: int, lookup_words: list[str]):
        seen: set[str] = set()
        normalized = {word.lower() for word in lookup_words}
        for job in self.import_jobs:
            if job["telegram_user_id"] != telegram_user_id:
                continue
            for item in job["items"]:
                if item["status"] in {
                    "pending",
                    "queued_for_attributes",
                    "collecting",
                    "found_existing",
                    "ready_for_attribute_review",
                    "ready_for_review",
                    "approved",
                    "ready_for_embedding",
                    "ready_for_publish",
                    "awaiting_audio",
                    "imported",
                } and item["lookup_word"].lower() in normalized:
                    seen.add(item["lookup_word"].lower())
        return seen

    def create_user_vocabulary_import_job(
        self,
        telegram_user_id: int,
        source_type: str,
        source_identifier: str,
        storage_path: str,
        items,
        current_time,
        task_log_id=None,
    ):
        job = {
            "id": self._import_job_seq,
            "telegram_user_id": telegram_user_id,
            "task_log_id": task_log_id,
            "source_type": source_type,
            "source_identifier": source_identifier,
            "storage_path": storage_path,
            "status": "queued",
            "total_items": len(items),
            "processed_items": 0,
            "successful_items": 0,
            "failed_items": 0,
            "summary_sent": False,
            "publish_summary_sent": False,
            "processing_claimed_until": None,
            "completed": None,
            "created": current_time,
            "updated": current_time,
            "items": [],
        }
        self._import_job_seq += 1
        for item in items:
            job["items"].append(
                {
                    "id": self._import_item_seq,
                    "import_job_id": job["id"],
                    "telegram_user_id": telegram_user_id,
                    "task_log_id": task_log_id,
                    "raw_value": item["raw_value"],
                    "lookup_word": item["lookup_word"],
                    "translation_hint": item.get("translation_hint"),
                    "validated_lookup_word": item.get("validated_lookup_word"),
                    "validated_part_of_speech": item.get("validated_part_of_speech"),
                    "validated_translation_uk": item.get("validated_translation_uk"),
                    "validated_translation_ru": item.get("validated_translation_ru"),
                    "validated_translation_pl": item.get("validated_translation_pl"),
                    "status": "pending",
                    "error_text": None,
                    "existing_word_id": None,
                    "pending_word_id": None,
                    "processed": None,
                }
            )
            self._import_item_seq += 1
        self.import_jobs.append(job)
        return copy.deepcopy(job)

    def create_job(
        self,
        telegram_user_id: int,
        source_type: str,
        source_identifier: str,
        storage_path: str,
        items,
        current_time,
        task_log_id=None,
    ):
        return self.create_user_vocabulary_import_job(
            telegram_user_id=telegram_user_id,
            source_type=source_type,
            source_identifier=source_identifier,
            storage_path=storage_path,
            items=items,
            current_time=current_time,
            task_log_id=task_log_id,
        )

    def claim_queued_user_vocabulary_import_jobs(self, *, current_time, claimed_until, limit=None):
        result = []
        for job in self.import_jobs:
            current_claim = job.get("processing_claimed_until")
            if job["status"] not in {"queued", "processing"} or job["summary_sent"]:
                continue
            if current_claim is not None and current_claim > current_time:
                continue
            job["status"] = "processing"
            job["processing_claimed_until"] = claimed_until
            job["updated"] = current_time
            result.append(copy.deepcopy(job))
            if limit is not None and len(result) >= limit:
                break
        return result

    def get_completed_user_vocabulary_import_jobs_pending_summary(self):
        return [copy.deepcopy(job) for job in self.import_jobs if job["status"] in {"completed", "failed"} and not job["summary_sent"]]

    def get_completed_user_vocabulary_import_jobs_pending_publish_summary(self):
        result = []
        for job in self.import_jobs:
            if job["status"] != "completed" or job.get("publish_summary_sent"):
                continue
            if any(item["status"] == "imported" for item in job["items"]):
                result.append(copy.deepcopy(job))
        return result

    def mark_user_vocabulary_import_job_processing(self, job_id: int, current_time) -> None:
        for job in self.import_jobs:
            if job["id"] == job_id:
                job["status"] = "processing"
                job["updated"] = current_time

    def complete_user_vocabulary_import_job(self, job_id: int, *, status: str, current_time, last_error=None) -> None:
        self.complete(job_id, status=status, current_time=current_time, last_error=last_error)

    def complete(self, job_id: int, *, status: str, current_time, last_error=None) -> None:
        for job in self.import_jobs:
            if job["id"] != job_id:
                continue
            job["status"] = status
            job["processing_claimed_until"] = None
            job["updated"] = current_time
            job["completed"] = current_time
            job["last_error"] = last_error
            items = job["items"]
            job["processed_items"] = len(items)
            job["successful_items"] = len(
                [
                    item
                    for item in items
                    if item["status"] in {
                        "found_existing",
                        "queued_for_attributes",
                        "ready_for_attribute_review",
                        "ready_for_review",
                        "approved",
                        "ready_for_embedding",
                        "ready_for_publish",
                        "awaiting_audio",
                        "imported",
                    }
                ]
            )
            job["failed_items"] = len([item for item in items if item["status"] in {"rejected", "build_failed", "failed"}])

    def list_unfinished_items(self, job_id: int):
        for job in self.import_jobs:
            if job["id"] == job_id:
                return copy.deepcopy([item for item in job["items"] if item["status"] in {"pending", "collecting"}])
        return []

    def mark_user_vocabulary_import_job_summary_sent(self, job_id: int, current_time) -> None:
        for job in self.import_jobs:
            if job["id"] == job_id:
                job["summary_sent"] = True
                job["updated"] = current_time

    def mark_user_vocabulary_import_job_publish_summary_sent(self, job_id: int, current_time) -> None:
        for job in self.import_jobs:
            if job["id"] == job_id:
                job["publish_summary_sent"] = True
                job["updated"] = current_time

    def get_user_vocabulary_import_items(self, job_id: int):
        for job in self.import_jobs:
            if job["id"] == job_id:
                return copy.deepcopy(job["items"])
        return []

    def get_user_vocabulary_import_job(self, job_id: int):
        for job in self.import_jobs:
            if job["id"] == job_id:
                payload = copy.deepcopy(job)
                payload.pop("items", None)
                return payload
        return None

    def get_user_vocabulary_import_items_for_user(self, telegram_user_id: int, job_id: int):
        for job in self.import_jobs:
            if job["id"] == job_id and job["telegram_user_id"] == telegram_user_id:
                return copy.deepcopy(job["items"])
        return []

    def get_user_vocabulary_import_job_for_user(self, telegram_user_id: int, job_id: int):
        for job in self.import_jobs:
            if job["id"] == job_id and job["telegram_user_id"] == telegram_user_id:
                payload = copy.deepcopy(job)
                payload.pop("items", None)
                return payload
        return None

    def claim_queued(self, *, current_time, claimed_until, limit=None):
        return self.claim_queued_user_vocabulary_import_jobs(
            current_time=current_time,
            claimed_until=claimed_until,
            limit=limit,
        )

    def list_completed_pending_summary(self):
        return self.get_completed_user_vocabulary_import_jobs_pending_summary()

    def list_completed_pending_publish_summary(self):
        return self.get_completed_user_vocabulary_import_jobs_pending_publish_summary()

    def mark_summary_sent(self, job_id: int, current_time) -> None:
        self.mark_user_vocabulary_import_job_summary_sent(job_id, current_time)

    def mark_publish_summary_sent(self, job_id: int, current_time) -> None:
        self.mark_user_vocabulary_import_job_publish_summary_sent(job_id, current_time)

    def list_items(self, job_id: int):
        return self.get_user_vocabulary_import_items(job_id)

    def get_job(self, job_id: int):
        return self.get_user_vocabulary_import_job(job_id)

    def list_items_for_user(self, telegram_user_id: int, job_id: int):
        return self.get_user_vocabulary_import_items_for_user(telegram_user_id, job_id)

    def get_job_for_user(self, telegram_user_id: int, job_id: int):
        return self.get_user_vocabulary_import_job_for_user(telegram_user_id, job_id)

    def list_by_pending_word(self, pending_word_id: int):
        result = []
        for job in self.import_jobs:
            result.extend(item for item in job["items"] if item["pending_word_id"] == pending_word_id)
        return copy.deepcopy(result)

    def list_dictionary_entries_without_audio(self, *, limit: int):
        rows = [
            row
            for row in self.dictionary_entries_by_word.values()
            if not str(row.get("audio_path") or "").strip()
        ]
        rows.sort(key=lambda row: row["id"])
        return copy.deepcopy(rows[:limit])

    def count_dictionary_entries_without_audio(self) -> int:
        return len([row for row in self.dictionary_entries_by_word.values() if not str(row.get("audio_path") or "").strip()])

    def update_dictionary_entry_audio(self, entry_id: int, *, audio_path: str, current_time):
        for row in self.dictionary_entries_by_word.values():
            if row["id"] != entry_id:
                continue
            row["audio_path"] = audio_path
            row["updated"] = current_time
            return copy.deepcopy(row)
        return None

    def list_without_audio(self, *, limit: int):
        return self.list_dictionary_entries_without_audio(limit=limit)

    def count_without_audio(self) -> int:
        return self.count_dictionary_entries_without_audio()

    def update_entry_audio(self, entry_id: int, *, audio_path: str, current_time):
        return self.update_dictionary_entry_audio(entry_id, audio_path=audio_path, current_time=current_time)

    def mark_existing_word(self, item_id: int, *, word_id: int, current_time) -> None:
        for job in self.import_jobs:
            for item in job["items"]:
                if item["id"] == item_id:
                    item["status"] = "found_existing"
                    item["existing_word_id"] = word_id
                    item["processed"] = current_time

    def mark_pending_word(self, item_id: int, *, pending_word_id: int, status: str, error_text: str | None, current_time) -> None:
        for job in self.import_jobs:
            for item in job["items"]:
                if item["id"] == item_id:
                    item["status"] = status
                    item["pending_word_id"] = pending_word_id
                    item["error_text"] = error_text
                    item["processed"] = current_time

    def mark_rejected(self, item_id: int, *, error_text: str, current_time) -> None:
        for job in self.import_jobs:
            for item in job["items"]:
                if item["id"] == item_id:
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
        current_time,
    ) -> None:
        for job in self.import_jobs:
            for item in job["items"]:
                if item["id"] == item_id:
                    item["status"] = status
                    item["user_dictionary_entry_id"] = user_dictionary_entry_id
                    item["error_text"] = error_text
                    item["processed"] = current_time

    def list_by_user_dictionary_entry(self, entry_id: int):
        rows = []
        for job in self.import_jobs:
            for item in job["items"]:
                if item.get("user_dictionary_entry_id") == entry_id:
                    rows.append({**copy.deepcopy(item), "telegram_user_id": job["telegram_user_id"]})
        return rows

    def sync_for_user_dictionary_entry(self, entry_id: int, *, status: str, error_text: str | None, current_time) -> None:
        for job in self.import_jobs:
            for item in job["items"]:
                if item.get("user_dictionary_entry_id") == entry_id:
                    item["status"] = status
                    item["error_text"] = error_text
                    item["processed"] = current_time

    def sync_for_pending_word(self, pending_word_id: int, *, status: str, error_text: str | None, current_time) -> None:
        for job in self.import_jobs:
            for item in job["items"]:
                if item["pending_word_id"] == pending_word_id:
                    item["status"] = status
                    item["error_text"] = error_text
                    item["processed"] = current_time

    def mark_imported_for_pending_word(self, pending_word_id: int, *, word_id: int, current_time) -> None:
        for job in self.import_jobs:
            for item in job["items"]:
                if item["pending_word_id"] == pending_word_id:
                    item["status"] = "imported"
                    item["existing_word_id"] = word_id
                    item["processed"] = current_time

    def import_pending_word(self, pending_word_id: int, *, admin_telegram_user_id: int, current_time):
        pending_row = next((row for row in self.pending_words.values() if row["id"] == pending_word_id), None)
        if pending_row is None:
            return None
        existing = self.dictionary_entries_by_word.get(str(pending_row["word"]).lower())
        if existing is None:
            entry_id = max([row["id"] for row in self.dictionary_entries_by_word.values()], default=5000) + 1
            entry = {
                "id": entry_id,
                "word": pending_row["word"],
                "translation_uk": pending_row.get("translation_uk"),
                "examples_json": pending_row.get("examples_json") or [],
                "audio_path": pending_row.get("audio_path"),
                "part_of_speech": pending_row.get("part_of_speech") or "",
                "parts_of_speech": [pending_row["part_of_speech"]] if pending_row.get("part_of_speech") else [],
                "categories": [],
                "phonetic_us": pending_row.get("phonetic_us"),
                "level_id": pending_row.get("level_id"),
                "entry_type": pending_row.get("entry_type") or "word",
                "review_priority": 0,
            }
            self.dictionary_entries_by_word[str(pending_row["word"]).lower()] = entry
            existing = entry
        pending_row["status"] = "imported"
        pending_row["approved_by_telegram_user_id"] = admin_telegram_user_id
        pending_row["approved"] = current_time
        pending_row["imported"] = current_time
        pending_row["rejected_reason"] = None
        pending_row["updated"] = current_time
        return copy.deepcopy(existing)

    def create(self, level: str, text, *, context_json=None) -> None:
        self.saved_events.append({"error_level": level, "text": text, "context_json": copy.deepcopy(context_json or {})})

    def create_task_log(
        self,
        *,
        task_type,
        status,
        current_time,
        telegram_user_id=None,
        source_type=None,
        source_identifier=None,
        import_job_id=None,
        description=None,
        error_text=None,
        result_json=None,
    ):
        row = {
            "id": self._task_log_seq,
            "task_type": task_type,
            "status": status,
            "telegram_user_id": telegram_user_id,
            "source_type": source_type,
            "source_identifier": source_identifier,
            "import_job_id": import_job_id,
            "description": description,
            "error_text": error_text,
            "result_json": copy.deepcopy(result_json or {}),
            "started": current_time,
            "finished": current_time if status in {"success", "error", "fatal"} else None,
            "created": current_time,
            "updated": current_time,
        }
        self._task_log_seq += 1
        self.task_logs.append(row)
        return copy.deepcopy(row)

    def update_task_log(
        self,
        task_log_id,
        *,
        status,
        current_time,
        description=None,
        error_text=None,
        result_json=None,
        import_job_id=None,
    ):
        for row in self.task_logs:
            if row["id"] != task_log_id:
                continue
            row["status"] = status
            row["description"] = description
            row["error_text"] = error_text
            row["result_json"] = copy.deepcopy(result_json or {})
            row["import_job_id"] = import_job_id
            row["updated"] = current_time
            row["finished"] = current_time if status in {"success", "error", "fatal"} else None
            return copy.deepcopy(row)
        return None

    def get_task_log(self, task_log_id: int):
        for row in self.task_logs:
            if row["id"] == task_log_id:
                return copy.deepcopy(row)
        return None

    def get_latest_task_log_for_import_job(self, import_job_id: int, *, task_type: str | None = None):
        matches = [
            row
            for row in self.task_logs
            if row.get("import_job_id") == import_job_id and (task_type is None or row.get("task_type") == task_type)
        ]
        if not matches:
            return None
        matches.sort(key=lambda row: (row["created"], row["id"]), reverse=True)
        return copy.deepcopy(matches[0])

    def get_app_runtime_state(self, key: str):
        value = self.runtime_state.get(key)
        return copy.deepcopy(value) if value is not None else None

    def set_app_runtime_state(self, key: str, value_json, current_time) -> None:
        self.runtime_state[key] = {"key": key, "value_json": copy.deepcopy(value_json), "updated": current_time}

    def update_exercise_result(self, session_word_id: int, exercise_type: str, attempts: int, is_correct: bool) -> None:
        for word in self.session_words:
            if word["session_word_id"] == session_word_id:
                word[f"{exercise_type}_attempts"] = attempts
                word[f"{exercise_type}_correct"] = is_correct

    def complete_session(self, session_id: int) -> None:
        self.active_session["status"] = "completed"
        self.active_session["current_stage"] = "completed"
        self._learning_sessions[self.active_session["id"]] = copy.deepcopy(self.active_session)

    def get_level_word_totals(self):
        return {1: 1000}

    def get_user_level_progress_summary(self, telegram_user_id: int, level_id: int, *, level_run_id: int | None = None):
        if self.summary_counts_override is not None:
            return copy.deepcopy(self.summary_counts_override)
        latest = self.get_latest_level_run(telegram_user_id, level_id)
        effective_level_run_id = level_run_id if level_run_id is not None else (latest["id"] if latest is not None else None)
        rows = []
        for key, row in self.word_progress.items():
            normalized = copy.deepcopy(row)
            if "level_run_id" not in normalized:
                normalized["level_run_id"] = key[0] if isinstance(key, tuple) else 1
            if normalized["level_run_id"] == effective_level_run_id:
                rows.append(normalized)
        learned_count = len([row for row in rows if row["learning_state"] == "learned"])
        in_progress_count = len([row for row in rows if row["learning_state"] == "learning"])
        needs_work_count = len([row for row in rows if row["learning_state"] == "needs_work"])
        return {
            "learned_count": learned_count,
            "in_progress_count": in_progress_count,
            "needs_work_count": needs_work_count,
        }

    def get_user_level_summary(self, telegram_user_id: int, level_id: int, *, level_run_id: int | None = None):
        return self.get_user_level_progress_summary(telegram_user_id, level_id, level_run_id=level_run_id)

    def get_user_assignment_summary(self, telegram_user_id: int):
        if self.summary_counts_override is not None:
            payload = copy.deepcopy(self.summary_counts_override)
            payload.setdefault("total_count", self.get_level_word_totals().get(self.profile["language_level_id"], 0))
            return payload
        rows = [
            copy.deepcopy(row)
            for row in self.word_progress.values()
            if int(row.get("telegram_user_id", telegram_user_id)) == telegram_user_id
        ]
        learned_count = len([row for row in rows if row.get("learning_state") == "learned"])
        in_progress_count = len([row for row in rows if row.get("learning_state") == "learning"])
        needs_work_count = len([row for row in rows if row.get("learning_state") == "needs_work"])
        return {
            "learned_count": learned_count,
            "in_progress_count": in_progress_count,
            "needs_work_count": needs_work_count,
            "total_count": len(rows),
        }

    def get_existing_schedule_for_date(self, telegram_user_id: int, target_date, *, schedule_types=None):
        row = self.existing_schedules.get(target_date)
        if row is None:
            return None
        if schedule_types and row.get("schedule_type") not in schedule_types:
            return None
        return copy.deepcopy(row)

    def get_existing_for_date(self, telegram_user_id: int, target_date, *, schedule_types=None):
        return self.get_existing_schedule_for_date(telegram_user_id, target_date, schedule_types=schedule_types)

    def get_next_training_schedule(self, telegram_user_id: int, current_time):
        if self.next_training_schedule is not None:
            return copy.deepcopy(self.next_training_schedule)
        comparable_current_time = current_time.replace(tzinfo=None) if getattr(current_time, "tzinfo", None) is not None else current_time
        candidates = [
            row
            for row in self.existing_schedules.values()
            if row["telegram_user_id"] == telegram_user_id and row["scheduled_for"] >= comparable_current_time
        ]
        if not candidates:
            return None
        return copy.deepcopy(sorted(candidates, key=lambda row: row["scheduled_for"])[0])

    def get_next(self, telegram_user_id: int, current_time):
        return self.get_next_training_schedule(telegram_user_id, current_time)

    def create_or_replace_training_schedule(
        self,
        telegram_user_id: int,
        schedule_type: str,
        scheduled_for,
        period_code: str | None = None,
        source_session_id: int | None = None,
    ):
        row = {
            "id": 501,
            "telegram_user_id": telegram_user_id,
            "schedule_type": schedule_type,
            "scheduled_for": scheduled_for,
            "schedule_date": scheduled_for.date(),
            "period_code": period_code,
            "source_session_id": source_session_id,
        }
        self.existing_schedules[scheduled_for.date()] = row
        return copy.deepcopy(row)

    def create_or_replace(
        self,
        telegram_user_id: int,
        schedule_type: str,
        scheduled_for,
        period_code: str | None = None,
        source_session_id: int | None = None,
    ):
        return self.create_or_replace_training_schedule(
            telegram_user_id,
            schedule_type,
            scheduled_for,
            period_code=period_code,
            source_session_id=source_session_id,
        )

    def get_due_training_schedules(self, current_time):
        return copy.deepcopy(self.due_schedules)

    def get_due(self, current_time):
        return self.get_due_training_schedules(current_time)

    def get_training_schedule(self, schedule_id: int):
        for row in self.existing_schedules.values():
            if row["id"] == schedule_id:
                return copy.deepcopy(row)
        return None

    def update_training_schedule_status(self, schedule_id: int, status: str) -> None:
        self.updated_schedule_statuses.append((schedule_id, status))

    def update_status(self, schedule_id: int, status: str) -> None:
        self.update_training_schedule_status(schedule_id, status)


def build_user(*, first_name: str = "Олена", username: str | None = "olena") -> TelegramUserContext:
    return TelegramUserContext(
        telegram_user_id=1,
        first_name=first_name,
        username=username,
        raw_telegram_json="{}",
    )


def test_learning_service_wires_user_import_services_to_repositories() -> None:
    db = FakeDatabase()

    service = build_service(db)

    assert service.user_import_notification_service.user_profiles is db.user_profiles
    assert service.user_import_intake_manual_bind_service.google_docs is db.user_import_google_docs
    assert (
        service.user_import_intake_service.manual_bind_service
        is service.user_import_intake_manual_bind_service
    )
    assert service.user_import_bound_google_doc_sync_processor.google_docs is db.user_import_google_docs
    assert (
        service.user_import_bound_google_doc_sync_processor.intake_job_service
        is service.user_import_intake_job_service
    )
    assert service.user_import_bound_google_doc_sync_service.google_docs is db.user_import_google_docs
    assert (
        service.user_import_bound_google_doc_sync_service.sync_processor
        is service.user_import_bound_google_doc_sync_processor
    )


def test_main_menu_restore_screen_prefers_editing_active_message() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_bootstrap_service.build_main_menu_restore_screen(1)

    assert screen.screen_id == "menu"
    assert screen.metadata["prefer_edit_active"] is True
    assert screen.metadata["auxiliary_after_active"] is False


def test_main_menu_shows_two_part_learning_and_settings_screen() -> None:
    db = FakeDatabase()
    db.profile["daily_reminder_hour"] = 10
    db.profile["reminder_weekdays"] = [0, 2, 4]
    db.next_training_schedule = {
        "id": 501,
        "telegram_user_id": 1,
        "schedule_type": "planned",
        "scheduled_for": datetime(2026, 4, 7, 19, 0, 0),
    }
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:menu")

    assert screen.clear_chat is True
    assert screen.text == "Почати тренування можна будь-коли, навіть без нагадування."
    assert [button.action for button in screen.buttons] == ["m:s"]
    assert screen.metadata["auxiliary_after_active"] is True
    assert (
        screen.metadata["auxiliary_message_text"]
        == "Графік і рівень тренувань можна змінити в налаштуваннях."
    )
    assert screen.metadata["auxiliary_message_buttons"] == [{"action": "m:settings", "text": "⚙️ Налаштування", "url": None}]


def test_main_menu_places_resume_button_after_start_action() -> None:
    db = FakeDatabase()
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "active",
        "current_stage": "card",
        "stage_queue_json": [],
        "stage_position": 0,
    }
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:menu")

    assert [button.action for button in screen.buttons] == ["m:s", "m:r"]


def test_main_menu_uses_summary_label_for_completed_session() -> None:
    db = FakeDatabase()
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "completed",
        "current_stage": "completed",
        "stage_queue_json": [],
        "stage_position": 0,
    }
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:menu")

    assert screen.buttons[1].action == "m:r"
    assert screen.buttons[1].text == "📊 Відкрити підсумок заняття"


def test_start_learning_without_level_returns_transient_validation_screen() -> None:
    db = FakeDatabase()
    db.profile["language_level_id"] = None
    db.profile["language_level_title"] = None
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:s")

    assert screen.screen_id == "transient:error"
    assert screen.text == "Помилка:\nСпершу оберіть рівень слів, з якого хочете почати."
    assert screen.metadata["force_resend"] is True
    assert screen.metadata["auto_advance_after_ms"] == 5000
    assert screen.metadata["next_action"] == "m:menu"
    assert screen.buttons == []


def test_resume_opens_choice_screen_when_level_changed() -> None:
    db = FakeDatabase()
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "active",
        "current_stage": "card",
        "stage_queue_json": [],
        "stage_position": 0,
        "session_type": "regular",
    }
    db.profile["language_level_id"] = 3
    db.profile["language_level_title"] = "B1"
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")

    assert screen.screen_id == "resume:choice"
    assert "У занятті рівень: A1. Зараз обрано: B1." in screen.text
    assert [button.action for button in screen.buttons] == ["m:r:continue", "m:r:restart", "m:menu"]


def test_resume_opens_choice_screen_when_word_count_changed() -> None:
    db = FakeDatabase()
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "active",
        "current_stage": "card",
        "stage_queue_json": [],
        "stage_position": 0,
        "session_type": "regular",
    }
    db.profile["words_per_session"] = 20
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")

    assert screen.screen_id == "resume:choice"
    assert "У занятті: 10 слів. Зараз обрано: 20 слів." in screen.text


def test_resume_choice_handles_missing_session_word_count_without_crashing() -> None:
    db = FakeDatabase()
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "status": "active",
        "current_stage": "card",
        "stage_queue_json": [],
        "stage_position": 0,
        "session_type": "regular",
    }
    db.profile["words_per_session"] = 20
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")

    assert screen.screen_id == "resume:choice"
    assert "У занятті: —. Зараз обрано: 20 слів." in screen.text


def test_resume_continue_keeps_existing_session() -> None:
    db = FakeDatabase()
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "active",
        "current_stage": "card",
        "stage_queue_json": [],
        "stage_position": 0,
        "session_type": "regular",
    }
    db.profile["language_level_id"] = 3
    db.profile["language_level_title"] = "B1"
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:r:continue")

    assert screen.screen_id == "card:11"


def test_resume_restart_starts_new_session_with_current_settings() -> None:
    db = FakeDatabase()
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "active",
        "current_stage": "card",
        "stage_queue_json": [],
        "stage_position": 0,
        "session_type": "regular",
    }
    db.profile["language_level_id"] = 3
    db.profile["language_level_title"] = "B1"
    db.profile["words_per_session"] = 20
    service = build_service(db)

    service.client_runtime_input_service.handle_action(build_user(), "m:r:restart")

    assert db.active_session["language_level_id"] == 3
    assert db.active_session["words_target_count"] == 20


def test_resume_restart_keeps_existing_session_when_new_settings_have_no_words() -> None:
    db = FakeDatabase()
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "active",
        "current_stage": "card",
        "stage_queue_json": [],
        "stage_position": 0,
        "session_type": "regular",
    }
    db.profile["language_level_id"] = 3
    db.profile["language_level_title"] = "B1"
    db.profile["words_per_session"] = 20
    db.session_words = []
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:r:restart")

    assert screen.screen_id == "menu"
    assert "Для обраного рівня зараз не вдалося сформувати підбірку слів." in screen.text
    assert any(button.action == "m:r" for button in screen.buttons)
    assert db.active_session["id"] == 77
    assert db.active_session["language_level_id"] == 1
    assert db.active_session["words_target_count"] == 10


def test_resume_skips_choice_for_completed_session_even_when_settings_changed() -> None:
    db = FakeDatabase()
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "completed",
        "current_stage": "completed",
        "stage_queue_json": [],
        "stage_position": 0,
        "session_type": "regular",
    }
    db.profile["language_level_id"] = 3
    db.profile["language_level_title"] = "B1"
    db.profile["words_per_session"] = 20
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")

    assert screen.screen_id == "summary:77"
    assert "Підсумок заняття" in screen.text


def test_main_menu_does_not_render_daily_reminder_summary() -> None:
    db = FakeDatabase()
    db.profile["daily_reminder_hour"] = 10
    db.profile["reminder_weekdays"] = [1, 3]
    service = build_service(db, FixedTimeService(datetime(2026, 4, 6, 16, 0, 0)))

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:menu")

    assert "Щоденне нагадування" not in screen.text
    assert "Наступне заняття" not in screen.text
    assert screen.text == "Почати тренування можна будь-коли, навіть без нагадування."


def test_handle_level_selection_saves_level() -> None:
    db = FakeDatabase()
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:l:B1")

    assert db.saved_levels == []
    assert "вебінтерфейсі" in screen.text
    assert screen.screen_id == "menu:settings:web"
    assert screen.clear_chat is False


def test_level_menu_is_opened_from_main_menu() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:levels")

    assert screen.screen_id == "menu:settings:web"
    assert screen.keyboard_type == "inline"
    assert screen.buttons[0].action == "web:settings"


def test_handle_word_count_saves_count() -> None:
    db = FakeDatabase()
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:w:15")

    assert db.saved_word_counts == []
    assert "вебінтерфейсі" in screen.text
    assert screen.screen_id == "menu:settings:web"
    assert screen.clear_chat is False


def test_mode_menu_is_opened_from_main_menu() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:modes")

    assert screen.screen_id == "menu:settings:web"
    assert screen.keyboard_type == "inline"
    assert screen.buttons[0].action == "web:settings"


def test_level_menu_moves_checkmark_after_selection() -> None:
    db = FakeDatabase()
    service = build_service(db)

    service.client_runtime_input_service.handle_action(build_user(), "m:l:B1")
    screen = service.client_runtime_input_service.handle_action(build_user(), "m:levels")

    assert [button.action for button in screen.buttons] == ["web:settings", "m:menu"]


def test_mode_menu_moves_checkmark_after_selection() -> None:
    db = FakeDatabase()
    service = build_service(db)

    service.client_runtime_input_service.handle_action(build_user(), "m:w:15")
    screen = service.client_runtime_input_service.handle_action(build_user(), "m:modes")

    assert [button.action for button in screen.buttons] == ["web:settings", "m:menu"]


def test_notification_menu_is_opened_from_main_menu() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:n")

    assert screen.screen_id == "menu:notifications"
    assert screen.keyboard_type == "inline"
    assert "Налаштування щоденних нагадувань" in screen.text
    assert [button.action for button in screen.buttons] == ["m:n:pick", "m:n:days", "m:n:disable", "m:settings", "m:menu"]


def test_settings_menu_groups_learning_configuration() -> None:
    db = FakeDatabase()
    db.profile["daily_reminder_hour"] = 10
    db.profile["reminder_weekdays"] = [0, 2]
    db.profile["import_google_doc_id"] = "demo"
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:settings")

    assert screen.screen_id == "menu:settings:web"
    assert "вебінтерфейсі" in screen.text
    assert [button.action for button in screen.buttons] == ["web:settings", "m:menu"]
    assert screen.metadata["buttons_per_row"] == 1


def test_level_menu_uses_compact_layout_with_back_and_home() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:levels")

    assert screen.screen_id == "menu:settings:web"
    assert screen.buttons[-2].action == "web:settings"
    assert screen.buttons[-1].action == "m:menu"


def test_notification_hour_picker_uses_compact_layout_with_back_and_home() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:n:period:day")

    assert screen.screen_id == "menu:notifications:hours:day"
    assert screen.buttons[-2].action == "m:n:pick"
    assert screen.buttons[-1].action == "m:menu"


def test_notification_period_picker_marks_current_period() -> None:
    db = FakeDatabase()
    db.profile["daily_reminder_hour"] = 10
    db.profile["reminder_weekdays"] = [0]
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:n:pick")

    assert screen.screen_id == "menu:notifications:period"
    assert screen.buttons[0].text == "✓ Ранок"


def test_notification_hour_picker_marks_current_hour() -> None:
    db = FakeDatabase()
    db.profile["daily_reminder_hour"] = 10
    db.profile["reminder_weekdays"] = [0]
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:n:period:morning")

    assert screen.screen_id == "menu:notifications:hours:morning"
    assert "✓ 10:00" in [button.text for button in screen.buttons]


def test_notification_weekday_picker_uses_compact_layout_with_save_back_and_home() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:n:days")

    assert screen.screen_id == "menu:notifications:days"
    assert screen.buttons[-2].action == "m:n:d:save"
    assert screen.buttons[-1].action == "m:menu"


def test_support_button_returns_to_main_menu_without_stub_notice() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:support")

    assert screen.screen_id == "menu"
    assert "ще в розробці" not in screen.text
    assert [button.action for button in screen.buttons] == ["m:s"]
    assert screen.metadata["auxiliary_message_buttons"] == [{"action": "m:settings", "text": "⚙️ Налаштування", "url": None}]


def test_setting_daily_reminder_hour_opens_weekday_picker() -> None:
    db = FakeDatabase()
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:n:hour:10")

    assert db.profile["daily_reminder_hour"] == 10
    assert screen.screen_id == "menu:notifications:days"


def test_toggle_reminder_weekday_updates_selection() -> None:
    db = FakeDatabase()
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:n:d:toggle:0")

    assert db.profile["reminder_weekdays"] == [0]
    assert screen.screen_id == "menu:notifications:days"


def test_saving_weekdays_requires_at_least_one_day() -> None:
    db = FakeDatabase()
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:n:d:save")

    assert screen.screen_id == "menu:notifications:days"


def test_saving_weekdays_returns_to_notification_menu() -> None:
    db = FakeDatabase()
    db.profile["reminder_weekdays"] = [0, 2, 4]
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:n:d:save")

    assert screen.screen_id == "menu:notifications"


def test_disabling_reminders_clears_hour_and_days() -> None:
    db = FakeDatabase()
    db.profile["daily_reminder_hour"] = 10
    db.profile["reminder_weekdays"] = [0, 1]
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:n:disable")

    assert db.profile["daily_reminder_hour"] is None
    assert db.profile["reminder_weekdays"] == []
    assert screen.screen_id == "menu:notifications"


def test_text_input_routes_to_level_menu_action() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_text_input(build_user(), "Рівень англійської")

    assert screen.screen_id == "menu:settings:web"


def test_text_input_routes_to_mode_selection_action() -> None:
    db = FakeDatabase()
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_text_input(build_user(), "20 слів")

    assert db.saved_word_counts == []
    assert "вебінтерфейсі" in screen.text


def test_text_input_routes_to_15_word_mode_selection() -> None:
    db = FakeDatabase()
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_text_input(build_user(), "15 слів")

    assert db.saved_word_counts == []
    assert "вебінтерфейсі" in screen.text
    assert screen.screen_id == "menu:settings:web"


def test_text_input_routes_to_30_and_40_word_mode_selection() -> None:
    db = FakeDatabase()
    service = build_service(db)

    screen_30 = service.client_runtime_input_service.handle_text_input(build_user(), "30 слів")
    screen_40 = service.client_runtime_input_service.handle_text_input(build_user(), "40 слів")

    assert db.saved_word_counts == []
    assert screen_30.screen_id == "menu:settings:web"
    assert screen_40.screen_id == "menu:settings:web"
    assert "вебінтерфейсі" in screen_30.text
    assert "вебінтерфейсі" in screen_40.text


def test_text_input_restores_current_card_layout_for_unrecognized_text() -> None:
    db = FakeDatabase()
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "active",
        "current_stage": "card",
        "stage_queue_json": [],
        "stage_position": 0,
        "active_interface": "telegram_user",
    }
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_text_input(build_user(), "@WebpageBot")

    assert screen.screen_id == "card:11"
    assert screen.metadata["force_resend"] is True
    assert screen.metadata["auxiliary_message_text"].startswith("Підказка:")
    assert [button.text for button in screen.buttons[:3]] == [" ", "1/2", "→"]


def test_text_input_restores_current_quiz_layout_for_unrecognized_text() -> None:
    db = FakeDatabase()
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "active",
        "current_stage": "quiz_gap",
        "stage_queue_json": [11],
        "stage_position": 0,
        "active_interface": "telegram_user",
    }
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_text_input(build_user(), "@WebpageBot")

    assert screen.screen_id.startswith("quiz_gap")
    assert screen.metadata["force_resend"] is True
    assert (
        "Вправа 3/3 - оберіть слово, яке заповнює пропуск у прикладі"
        in screen.metadata["auxiliary_message_text"]
    )
    assert "[⋯" in screen.text


def test_text_input_routes_to_notification_time_picker() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_text_input(build_user(), "Налаштувати час")

    assert screen.screen_id == "menu:notifications:period"


def test_text_input_routes_to_notification_weekday_picker() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_text_input(build_user(), "Налаштувати дні")

    assert screen.screen_id == "menu:notifications:days"


def test_text_input_routes_to_notification_disable_action() -> None:
    db = FakeDatabase()
    db.profile["daily_reminder_hour"] = 10
    db.profile["reminder_weekdays"] = [0, 1]
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_text_input(build_user(), "Вимкнути нагадування")

    assert db.profile["daily_reminder_hour"] is None
    assert db.profile["reminder_weekdays"] == []
    assert screen.screen_id == "menu:notifications"


def test_text_input_routes_to_settings_screen() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_text_input(build_user(), "⚙️ Налаштування")

    assert screen.screen_id == "menu:settings:web"
    assert "5 хв" in screen.text
    assert [button.action for button in screen.buttons] == ["web:settings", "m:menu"]
    assert screen.metadata["auto_advance_after_ms"] == 5 * 60 * 1000
    assert screen.metadata["next_action"] == "m:menu"


def test_text_input_routes_completed_session_summary_label_to_resume_action() -> None:
    db = FakeDatabase()
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "completed",
        "current_stage": "completed",
        "stage_queue_json": [],
        "stage_position": 0,
    }
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_text_input(build_user(), "📊 Відкрити підсумок заняття")

    assert screen.screen_id == "summary:77"


def test_import_screen_is_opened_from_settings() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:i")

    assert screen.screen_id == "menu:import_words"
    assert "Google Doc" in screen.text
    assert "кожні 3 дні о 00:00" in screen.text
    assert "до 100 нових слів" in screen.text
    assert screen.buttons[-1].action == "m:menu"


def test_import_screen_hides_run_now_button_for_non_admin_in_test_mode() -> None:
    db = FakeDatabase()
    db.settings.app_user_import_test_mode = True
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:i")

    assert all(button.action != "m:i:run-now" for button in screen.buttons)


def test_text_input_with_invalid_google_doc_url_keeps_user_on_import_screen() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_text_input(build_user(), "https://docs.google.com/spreadsheets/d/demo/edit")

    assert screen.screen_id == "menu:import_words"
    assert "Не вдалося прийняти посилання" in screen.text


def test_import_screen_shows_unbind_button_for_bound_doc() -> None:
    db = FakeDatabase()
    db.profile["import_google_doc_id"] = "demo"
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:i")

    assert any(button.action == "m:i:unbind" for button in screen.buttons)


def test_import_screen_can_unbind_google_doc() -> None:
    db = FakeDatabase()
    db.profile["import_google_doc_id"] = "demo"
    db.profile["is_import_google_doc_auto_sync_enabled"] = True
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:i:unbind")

    assert "Google Doc відвʼязано" in screen.text
    assert db.profile["import_google_doc_id"] is None
    assert db.profile["is_import_google_doc_auto_sync_enabled"] is False


def test_import_failed_items_screen_shows_unsuccessful_words_with_reasons() -> None:
    db = FakeDatabase()
    current_time = datetime(2026, 4, 7, 10, 0, 0)
    db.create_user_vocabulary_import_job(
        telegram_user_id=1,
        source_type="google_doc",
        source_identifier="demo",
        storage_path="runtime/test_user_imports/job.json",
        items=[
            {"raw_value": "bad phrase", "lookup_word": "bad phrase"},
            {"raw_value": "broken", "lookup_word": "broken"},
        ],
        current_time=current_time,
    )
    db.import_jobs[0]["items"][0]["status"] = "build_failed"
    db.import_jobs[0]["items"][0]["error_text"] = "не знайдено part_of_speech"
    db.import_jobs[0]["items"][1]["status"] = "failed"
    db.import_jobs[0]["items"][1]["error_text"] = "provider outage"
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:i:failed:1")

    assert screen.screen_id == "import_words:failed:1"
    assert "bad phrase\nне вдалося підготувати слово" in screen.text
    assert "broken\nне вдалося підготувати слово" in screen.text
    assert screen.buttons[0].action == "m:i:summary:1"
    assert screen.buttons[1].action == "m:i:delete:1"
    assert screen.metadata["delete_after_hours"] == 24
    assert screen.metadata["sticky_import_report"] is True


def test_import_queued_items_screen_shows_words_waiting_for_preparation(tmp_path) -> None:
    db = FakeDatabase()
    db.settings.app_user_import_storage_dir = str(tmp_path)
    current_time = datetime(2026, 4, 7, 10, 0, 0)
    storage_path = tmp_path / "job.json"
    db.create_user_vocabulary_import_job(
        telegram_user_id=1,
        source_type="bound_google_doc",
        source_identifier="demo",
        storage_path=str(storage_path),
        items=[
            {"raw_value": "take over", "lookup_word": "take over"},
            {"raw_value": "carry on", "lookup_word": "carry on"},
        ],
        current_time=current_time,
    )
    db.import_jobs[0]["status"] = "completed"
    db.import_jobs[0]["items"][0]["status"] = "queued_for_attributes"
    db.import_jobs[0]["items"][1]["status"] = "queued_for_attributes"
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:i:queued:1")

    assert screen.screen_id == "import_words:documents:queued:1"
    assert screen.metadata["documents_only"] is True
    assert len(screen.documents) == 1
    assert screen.documents[0].caption == "queued: слова в черзі на підготовку"
    assert Path(screen.documents[0].path).read_text(encoding="utf-8") == "take over\ncarry on"
    assert screen.buttons == []


def test_import_existing_items_screen_shows_words_already_in_dictionary(tmp_path) -> None:
    db = FakeDatabase()
    db.settings.app_user_import_storage_dir = str(tmp_path)
    db.dictionary_entries_by_word["speak"] = {"id": 101, "word": "speak", "translation_uk": "говорити"}
    db.dictionary_entries_by_word["write"] = {"id": 102, "word": "write", "translation_uk": "писати"}
    current_time = datetime(2026, 4, 7, 10, 0, 0)
    storage_path = tmp_path / "job.json"
    db.create_user_vocabulary_import_job(
        telegram_user_id=1,
        source_type="bound_google_doc",
        source_identifier="demo",
        storage_path=str(storage_path),
        items=[
            {"raw_value": "speak", "lookup_word": "speak"},
            {"raw_value": "write", "lookup_word": "write"},
        ],
        current_time=current_time,
    )
    db.import_jobs[0]["status"] = "completed"
    db.import_jobs[0]["items"][0]["status"] = "found_existing"
    db.import_jobs[0]["items"][1]["status"] = "found_existing"
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:i:existing:1")

    assert screen.screen_id == "import_words:documents:existing:1"
    assert screen.metadata["documents_only"] is True
    assert len(screen.documents) == 1
    assert screen.documents[0].caption == "existing: слова, які вже були в словнику"
    assert Path(screen.documents[0].path).read_text(encoding="utf-8") == "speak - говорити\nwrite - писати"
    assert screen.buttons == []


def test_import_summary_screen_includes_task_log_context() -> None:
    db = FakeDatabase()
    current_time = datetime(2026, 4, 7, 10, 0, 0)
    job = db.create_user_vocabulary_import_job(
        telegram_user_id=1,
        source_type="google_doc",
        source_identifier="demo-doc-42",
        storage_path="runtime/test_user_imports/job.json",
        items=[{"raw_value": "speak", "lookup_word": "speak"}],
        current_time=current_time,
        task_log_id=1,
    )
    db.import_jobs[0]["status"] = "completed"
    origin_task = db.task_logs.create(
        task_type="bound_google_doc_sync",
        status="success",
        current_time=current_time,
        telegram_user_id=1,
        source_type="google_doc",
        source_identifier="demo-doc-42",
        description="sync completed",
        result_json={"invalid_fragments_count": 2, "skipped_duplicates_count": 3},
    )
    assert origin_task["id"] == 1
    db.task_logs.create(
        task_type="user_vocabulary_import_job_process",
        status="success",
        current_time=current_time + timedelta(minutes=1),
        telegram_user_id=1,
        source_type="google_doc",
        source_identifier="demo-doc-42",
        import_job_id=job["id"],
        description="job completed",
        result_json={"ready_for_attribute_review_count": 1},
    )
    db.import_jobs[0]["items"][0]["status"] = "ready_for_attribute_review"
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:i:summary:1")

    assert screen.screen_id == "import_words:summary:1"
    assert all(button.action != "m:i:existing:1" for button in screen.buttons)
    assert "Технічні деталі:" not in screen.text
    assert "Джерело: demo-doc-42." not in screen.text
    assert "Відхилено: 2 елементи." in screen.text
    assert "На розгляді: 1 елемент." in screen.text


def test_import_failed_items_screen_includes_processing_task_error_context() -> None:
    db = FakeDatabase()
    current_time = datetime(2026, 4, 7, 10, 0, 0)
    job = db.create_user_vocabulary_import_job(
        telegram_user_id=1,
        source_type="google_doc",
        source_identifier="demo-doc-42",
        storage_path="runtime/test_user_imports/job.json",
        items=[{"raw_value": "broken", "lookup_word": "broken"}],
        current_time=current_time,
        task_log_id=1,
    )
    db.import_jobs[0]["status"] = "failed"
    db.import_jobs[0]["items"][0]["status"] = "failed"
    db.import_jobs[0]["items"][0]["error_text"] = "provider outage"
    db.task_logs.create(
        task_type="bound_google_doc_sync",
        status="success",
        current_time=current_time,
        telegram_user_id=1,
        source_type="google_doc",
        source_identifier="demo-doc-42",
        description="sync completed",
    )
    db.task_logs.create(
        task_type="user_vocabulary_import_job_process",
        status="fatal",
        current_time=current_time + timedelta(minutes=1),
        telegram_user_id=1,
        source_type="google_doc",
        source_identifier="demo-doc-42",
        import_job_id=job["id"],
        description="job crashed",
        error_text="fatal boom?api_key=[redacted]",
    )
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:i:failed:1")

    assert "Технічні деталі:" in screen.text
    assert "Обробка партії: запуск #2, статус фатал." in screen.text
    assert "Остання технічна помилка: fatal boom?api_key=[redacted]." in screen.text


def test_import_failed_items_screen_rejects_foreign_job_access() -> None:
    db = FakeDatabase()
    current_time = datetime(2026, 4, 7, 10, 0, 0)
    db.create_user_vocabulary_import_job(
        telegram_user_id=2,
        source_type="google_doc",
        source_identifier="demo",
        storage_path="runtime/test_user_imports/job.json",
        items=[{"raw_value": "broken", "lookup_word": "broken"}],
        current_time=current_time,
    )
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:i:failed:1")

    assert screen.screen_id == "menu:import_words"
    assert "Не вдалося прийняти посилання" in screen.text


def test_import_queued_items_screen_rejects_foreign_job_access() -> None:
    db = FakeDatabase()
    current_time = datetime(2026, 4, 7, 10, 0, 0)
    db.create_user_vocabulary_import_job(
        telegram_user_id=2,
        source_type="bound_google_doc",
        source_identifier="demo",
        storage_path="runtime/test_user_imports/job.json",
        items=[{"raw_value": "take over", "lookup_word": "take over"}],
        current_time=current_time,
    )
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:i:queued:1")

    assert screen.screen_id == "menu:import_words"
    assert "Не вдалося прийняти посилання" in screen.text


def test_import_failed_items_screen_back_returns_to_summary() -> None:
    db = FakeDatabase()
    current_time = datetime(2026, 4, 7, 10, 0, 0)
    db.create_user_vocabulary_import_job(
        telegram_user_id=1,
        source_type="google_doc",
        source_identifier="demo",
        storage_path="runtime/test_user_imports/job.json",
        items=[{"raw_value": "broken", "lookup_word": "broken"}],
        current_time=current_time,
    )
    db.import_jobs[0]["status"] = "completed"
    db.import_jobs[0]["items"][0]["status"] = "failed"
    db.import_jobs[0]["items"][0]["error_text"] = "provider outage"
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:i:summary:1")

    assert screen.screen_id == "import_words:summary:1"
    assert "Додано: 0 елементів." in screen.text
    assert "Відхилено: 1 елемент." in screen.text
    assert "На розгляді: 0 елементів." in screen.text
    assert screen.buttons[-1].action == "m:i:delete:1"
    assert screen.metadata["delete_after_hours"] == 24
    assert screen.metadata["sticky_import_report"] is True


def test_import_delete_action_returns_close_to_menu_screen() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:i:delete:1")

    assert screen.screen_id == "menu"
    assert screen.clear_chat is True
    assert screen.metadata["force_resend"] is True
    assert screen.metadata["delete_cached_active_screen"] is True


def test_billing_close_action_returns_close_to_menu_screen() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_action(build_user(), "billing:close")

    assert screen.screen_id == "menu"
    assert screen.clear_chat is True
    assert screen.metadata["force_resend"] is True
    assert screen.metadata["delete_cached_active_screen"] is True


def test_import_screen_masks_bound_google_doc_url() -> None:
    db = FakeDatabase()
    db.profile["import_google_doc_id"] = "abcdefghijklmnop"
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:i")

    assert "abcdefghijklmnop" not in screen.text
    assert "abcd...mnop" in screen.text


def test_process_due_user_vocabulary_imports_does_not_write_legacy_wordnik_quota_state(monkeypatch, tmp_path) -> None:
    db = FakeDatabase()
    db.settings.app_user_import_storage_dir = str(tmp_path)
    current_time = datetime(2026, 4, 8, 10, 0, 0)
    db.create_user_vocabulary_import_job(
        telegram_user_id=1,
        source_type="google_doc",
        source_identifier="demo",
        storage_path=str(tmp_path / "job.json"),
        items=[{"raw_value": "take over", "lookup_word": "take over"}],
        current_time=current_time,
    )
    monkeypatch.setattr(
        "app.composition.root.resolve_pending_import_word",
        lambda **kwargs: type(
            "Resolution",
            (),
            {
                "word": "take over",
                "translation_uk": None,
                "translation_ru": None,
                "translation_pl": None,
                "part_of_speech": None,
                "phonetic_us": None,
                "phonetic_uk": None,
                "audio_path": None,
                "examples_json": [],
                "source_payload_refs_json": {},
                "source_provider_status_json": {"openai_user_import": {"status": "error", "error": "OPENAI__API_KEY is not configured."}},
                "status": "build_failed",
                "rejected_reason": "OPENAI__API_KEY is not configured.",
                "should_retry": False,
                "level_id": None,
                "embedding": None,
                "embedding_model": None,
                "is_embedding_ready": False,
            },
        )(),
    )
    service = build_service(db, FixedTimeService(current_time))

    service.user_import_scheduled_runtime_service.process_due_user_vocabulary_imports()

    quota = db.runtime_state.get("user_import_wordnik_quota")
    assert quota is None or quota["value_json"].get("requests_used", 0) == 0


def test_process_due_user_vocabulary_imports_does_not_count_legacy_wordnik_quota(monkeypatch, tmp_path) -> None:
    db = FakeDatabase()
    db.settings.app_user_import_storage_dir = str(tmp_path)
    current_time = datetime(2026, 4, 8, 10, 0, 0)
    db.create_user_vocabulary_import_job(
        telegram_user_id=1,
        source_type="google_doc",
        source_identifier="demo",
        storage_path=str(tmp_path / "job.json"),
        items=[{"raw_value": "take over", "lookup_word": "take over"}],
        current_time=current_time,
    )
    monkeypatch.setattr(
        "app.composition.root.resolve_pending_import_word",
        lambda **kwargs: type(
            "Resolution",
            (),
            {
                "word": "take over",
                "translation_uk": "перейняти",
                "translation_ru": "перехватить",
                "translation_pl": "przejąć",
                "part_of_speech": "verb",
                "phonetic_us": "/teik ˈouvər/",
                "phonetic_uk": None,
                "audio_path": "runtime/user_import_audio/take-over.mp3",
                "examples_json": ["They took over the shop."],
                "source_payload_refs_json": {"openai_user_import": str(tmp_path / "take-over.json")},
                "source_provider_status_json": {"openai_user_import": {"status": "ok"}},
                "status": "ready_for_attribute_review",
                "rejected_reason": None,
                "should_retry": False,
                "level_id": None,
                "embedding": None,
                "embedding_model": None,
                "is_embedding_ready": False,
            },
        )(),
    )
    service = build_service(db, FixedTimeService(current_time))

    service.user_import_scheduled_runtime_service.process_due_user_vocabulary_imports()

    quota = db.runtime_state.get("user_import_wordnik_quota")
    assert quota is None or quota["value_json"].get("requests_used", 0) == 0


def test_process_due_bound_google_doc_syncs_enqueues_only_first_hundred_new_words_per_sync(monkeypatch, tmp_path) -> None:
    db = FakeDatabase()
    db.settings.app_user_import_storage_dir = str(tmp_path)
    db.profile["import_google_doc_id"] = "demo"
    db.profile["is_import_google_doc_auto_sync_enabled"] = True
    current_time = datetime(2026, 4, 8, DEFAULT_IMPORT_RUNTIME_SETTINGS["google_doc_sync_hour"], 0, 0)
    service = build_service(db, FixedTimeService(current_time))
    source_words = [build_alpha_word(index) for index in range(1, 151)]
    raw_text = "\n".join(f"{index}. {word}" for index, word in enumerate(source_words, start=1))
    monkeypatch.setattr("app.composition.root.fetch_google_doc_text", lambda value: raw_text)

    service.user_import_scheduled_runtime_service.process_due_bound_google_doc_syncs()

    assert len(db.import_jobs) == 1
    assert db.import_jobs[0]["total_items"] == 100
    assert db.import_jobs[0]["items"][0]["lookup_word"] == source_words[0]
    assert db.import_jobs[0]["items"][-1]["lookup_word"] == source_words[99]


def test_process_due_bound_google_doc_syncs_takes_next_hundred_after_previous_batch(monkeypatch, tmp_path) -> None:
    db = FakeDatabase()
    db.settings.app_user_import_storage_dir = str(tmp_path)
    db.profile["import_google_doc_id"] = "demo"
    db.profile["is_import_google_doc_auto_sync_enabled"] = True
    first_sync_time = datetime(2026, 4, 8, DEFAULT_IMPORT_RUNTIME_SETTINGS["google_doc_sync_hour"], 0, 0)
    second_sync_time = first_sync_time + timedelta(days=DEFAULT_IMPORT_RUNTIME_SETTINGS["google_doc_sync_interval_days"])
    source_words = [build_alpha_word(index) for index in range(1, 221)]
    raw_text = "\n".join(source_words)
    monkeypatch.setattr("app.composition.root.fetch_google_doc_text", lambda value: raw_text)

    first_service = build_service(db, FixedTimeService(first_sync_time))
    first_service.user_import_scheduled_runtime_service.process_due_bound_google_doc_syncs()

    assert len(db.import_jobs) == 1
    assert db.import_jobs[0]["total_items"] == 100
    first_batch_words = [item["lookup_word"] for item in db.import_jobs[0]["items"]]
    assert first_batch_words[0] == source_words[0]
    assert first_batch_words[-1] == source_words[99]
    assert len(first_batch_words) == 100

    second_service = build_service(db, FixedTimeService(second_sync_time))
    second_service.user_import_scheduled_runtime_service.process_due_bound_google_doc_syncs()

    assert len(db.import_jobs) == 2
    assert db.import_jobs[1]["total_items"] == 100
    second_batch_words = [item["lookup_word"] for item in db.import_jobs[1]["items"]]
    assert second_batch_words[0] == source_words[100]
    assert second_batch_words[-1] == source_words[199]


def test_process_due_bound_google_doc_syncs_schedules_retry_for_google_doc_sync_failure(monkeypatch) -> None:
    db = FakeDatabase()
    db.profile["import_google_doc_id"] = "demo"
    db.profile["is_import_google_doc_auto_sync_enabled"] = True
    current_time = datetime(2026, 4, 8, DEFAULT_IMPORT_RUNTIME_SETTINGS["google_doc_sync_hour"], 0, 0)
    service = build_service(db, FixedTimeService(current_time))
    monkeypatch.setattr("app.composition.root.fetch_google_doc_text", lambda value: (_ for _ in ()).throw(RuntimeError("network timeout")))

    service.user_import_scheduled_runtime_service.process_due_bound_google_doc_syncs()

    assert db.profile["import_google_doc_retry_count"] == 1
    assert db.profile["import_google_doc_next_retry_at"] == current_time + timedelta(seconds=2)
    assert db.profile["import_google_doc_last_error"] == "network timeout"


def test_process_due_bound_google_doc_syncs_sanitizes_google_doc_sync_failure(monkeypatch) -> None:
    db = FakeDatabase()
    db.profile["import_google_doc_id"] = "demo"
    db.profile["is_import_google_doc_auto_sync_enabled"] = True
    current_time = datetime(2026, 4, 8, DEFAULT_IMPORT_RUNTIME_SETTINGS["google_doc_sync_hour"], 0, 0)
    service = build_service(db, FixedTimeService(current_time))
    monkeypatch.setattr(
        "app.composition.root.fetch_google_doc_text",
        lambda value: (_ for _ in ()).throw(RuntimeError("network timeout?api_key=secret-token")),
    )

    service.user_import_scheduled_runtime_service.process_due_bound_google_doc_syncs()

    assert db.profile["import_google_doc_last_error"] == "network timeout?api_key=[redacted]"
    assert any(
        "source_identifier=demo" in event["text"] and "[redacted]" in event["text"]
        for event in db.saved_events
        if event.get("error_level") == "warn"
    )
    assert db.task_logs[0]["task_type"] == "bound_google_doc_sync"
    assert db.task_logs[0]["status"] == "error"
    assert db.task_logs[0]["result_json"]["retry_count"] == 1


def test_process_due_user_vocabulary_imports_logs_fatal_task_context_for_import_job_crash(monkeypatch, tmp_path) -> None:
    db = FakeDatabase()
    db.settings.app_user_import_storage_dir = str(tmp_path)
    db.create_user_vocabulary_import_job(
        telegram_user_id=1,
        source_type="google_doc",
        source_identifier="demo",
        storage_path=str(tmp_path / "job.json"),
        items=[{"raw_value": "take over", "lookup_word": "take over"}],
        current_time=datetime(2026, 4, 7, 10, 0, 0),
    )
    service = build_service(db, FixedTimeService(datetime(2026, 4, 7, 10, 5, 0)))
    monkeypatch.setattr(
        service.user_import_job_processing_service,
        "prepare_import_job_items",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fatal boom?api_key=secret-token")),
    )

    notifications = service.user_import_scheduled_runtime_service.process_due_user_vocabulary_imports()

    assert len(notifications) == 1
    assert db.import_jobs[0]["status"] == "failed"
    assert db.task_logs[0]["task_type"] == "user_vocabulary_import_job_process"
    assert db.task_logs[0]["status"] == "fatal"
    assert db.task_logs[0]["error_text"] == "fatal boom?api_key=[redacted]"
    fatal_events = [event for event in db.saved_events if event.get("error_level") == "fatal"]
    assert len(fatal_events) == 1
    assert fatal_events[0]["context_json"]["task_log_id"] == db.task_logs[0]["id"]
    assert fatal_events[0]["context_json"]["import_job_id"] == 1


def test_process_due_bound_google_doc_syncs_treats_empty_bound_google_doc_as_success_without_job(monkeypatch) -> None:
    db = FakeDatabase()
    db.profile["import_google_doc_id"] = "demo"
    db.profile["is_import_google_doc_auto_sync_enabled"] = True
    db.profile["import_google_doc_last_error"] = "old error"
    current_time = datetime(2026, 4, 8, DEFAULT_IMPORT_RUNTIME_SETTINGS["google_doc_sync_hour"], 0, 0)
    service = build_service(db, FixedTimeService(current_time))
    monkeypatch.setattr(
        "app.composition.root.fetch_google_doc_text",
        lambda value: "<script>alert(1)</script>\n",
    )

    notifications = service.user_import_scheduled_runtime_service.process_due_bound_google_doc_syncs()

    assert notifications == []
    assert db.import_jobs == []
    assert db.profile["import_google_doc_retry_count"] == 0
    assert db.profile["import_google_doc_next_retry_at"] is None
    assert db.profile["import_google_doc_last_synced"] == current_time
    assert db.profile["import_google_doc_last_error"] is None


def test_process_due_bound_google_doc_syncs_marks_google_doc_sync_terminal_after_retry_limit(monkeypatch) -> None:
    db = FakeDatabase()
    db.profile["import_google_doc_id"] = "demo"
    db.profile["is_import_google_doc_auto_sync_enabled"] = True
    db.profile["import_google_doc_retry_count"] = 3
    db.profile["import_google_doc_next_retry_at"] = datetime(2026, 4, 7, 23, 59, 0)
    current_time = datetime(2026, 4, 8, DEFAULT_IMPORT_RUNTIME_SETTINGS["google_doc_sync_hour"], 0, 0)
    service = build_service(db, FixedTimeService(current_time))
    monkeypatch.setattr("app.composition.root.fetch_google_doc_text", lambda value: (_ for _ in ()).throw(RuntimeError("network timeout")))

    service.user_import_scheduled_runtime_service.process_due_bound_google_doc_syncs()

    assert db.profile["import_google_doc_retry_count"] == 4
    assert db.profile["import_google_doc_next_retry_at"] is None
    assert db.profile["import_google_doc_last_synced"] == current_time


def test_text_input_reports_plain_text_import_as_temporarily_disabled() -> None:
    db = FakeDatabase()
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_text_input(build_user(), "speak, take over, move on")

    assert screen.screen_id == "menu:import_words"
    assert "тимчасово вимкнений" in screen.text


def test_start_learning_returns_first_card() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:s")

    assert screen.screen_id == "card:11"
    assert screen.audio_path is not None
    assert "Слово 1 із 2" not in screen.text
    assert "────────────" not in screen.text
    assert "learn" in screen.text
    assert "<b>learn</b> <i>(дієслово)</i>" in screen.text
    assert "[lɜːrn]" in screen.text
    assert "вивчати" in screen.text
    assert "Категорії: Загальне, Навчання" in screen.text
    assert "Картка слова" not in screen.text
    assert screen.text.count("<blockquote>") == 1
    assert screen.metadata["auxiliary_message_text"].startswith("Підказка:")
    assert "Слово 1 із 2" not in screen.metadata["auxiliary_message_text"]
    assert "Підказка:" in screen.metadata["auxiliary_message_text"]
    assert "[⋯" not in screen.metadata["auxiliary_message_text"]
    assert screen.keyboard_type == "inline"
    assert [button.action for button in screen.buttons] == [
        "noop",
        "noop",
        "s:77:c:11:next",
        "s:77:c:11:known",
        "m:menu",
    ]
    assert [button.text for button in screen.buttons[:3]] == [" ", "1/2", "→"]


def test_card_menu_button_returns_to_menu_without_losing_active_session() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:menu")

    assert screen.screen_id == "menu"
    assert any(button.action == "m:r" for button in screen.buttons)


def test_start_learning_builds_caption_under_safe_limit() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:s")

    assert len(screen.text) <= 900


def test_known_card_keeps_word_in_learning_flow() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")

    screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:known")

    assert db.progress_updates[0]["is_known"] is True
    assert db.progress_updates[0]["learning_state"] == "learned"
    assert db.progress_updates[0]["control_success_streak"] == 2
    assert db.progress_updates[0]["completed_now"] is True
    assert screen.screen_id == "card:11"
    assert "Слово 1 із 2" not in screen.text
    assert "write" in screen.text
    assert "Слово 1 із 2" not in screen.metadata["auxiliary_message_text"]


def test_known_card_appends_replacement_word_to_keep_session_limit() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")

    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:known")

    assert [row["word_id"] for row in db.session_words] == [103, 102]
    assert db.session_words[0]["word"] == "write"


def test_known_card_replacement_uses_only_fresh_words() -> None:
    db = FakeDatabase()
    db.extra_word_progress[103] = {
        "telegram_user_id": 1,
        "word_id": 103,
        "is_known": False,
        "learning_state": "needs_work",
        "control_success_streak": 0,
        "review_priority": 5,
        "last_completed": None,
        "next_review_at": datetime(2026, 4, 8, 9, 0, 0),
    }
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")

    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:known")

    assert [row["word_id"] for row in db.session_words] == [101, 102]


def test_known_card_replacement_prefers_priority_imported_word() -> None:
    db = FakeDatabase()
    db.extra_lesson_words = [
        {
            "id": 103,
            "word": "write",
            "translation_uk": "писати",
            "examples_json": ["Write it down."],
            "audio_path": "word_base/word_audio/5918_write.mp3",
            "part_of_speech": "verb",
            "parts_of_speech": ["verb"],
            "categories": ["general", "writing"],
            "phonetic_us": "/raɪt/",
            "level_id": 1,
            "review_priority": 0,
            "is_priority": False,
        },
        {
            "id": 104,
            "word": "take over",
            "translation_uk": "переймати",
            "examples_json": ["Take over the task."],
            "audio_path": "runtime/user_import_audio/take_over.mp3",
            "part_of_speech": "phrasal verb",
            "parts_of_speech": ["phrasal verb"],
            "categories": [],
            "phonetic_us": "/teik/",
            "level_id": 1,
            "review_priority": 0,
            "is_priority": True,
        },
    ]
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")

    screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:known")

    assert screen.screen_id == "card:11"
    assert db.session_words[0]["word_id"] == 104
    assert db.session_words[0]["word"] == "take over"
    assert "take over" in screen.text


def test_known_card_replacement_skips_priority_word_without_audio() -> None:
    db = FakeDatabase()
    db.extra_lesson_words = [
        {
            "id": 103,
            "word": "write",
            "translation_uk": "писати",
            "examples_json": ["Write it down."],
            "audio_path": "word_base/word_audio/5918_write.mp3",
            "part_of_speech": "verb",
            "parts_of_speech": ["verb"],
            "categories": ["general", "writing"],
            "phonetic_us": "/raɪt/",
            "level_id": 1,
            "review_priority": 0,
            "is_priority": False,
        },
        {
            "id": 104,
            "word": "take over",
            "translation_uk": "переймати",
            "examples_json": ["Take over the task."],
            "audio_path": "",
            "part_of_speech": "phrasal verb",
            "parts_of_speech": ["phrasal verb"],
            "categories": [],
            "phonetic_us": "/teik/",
            "level_id": 1,
            "review_priority": 0,
            "is_priority": True,
        },
    ]
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")

    screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:known")

    assert screen.screen_id == "card:11"
    assert db.session_words[0]["word_id"] == 103
    assert db.session_words[0]["word"] == "write"
    assert "write" in screen.text


def test_known_card_words_are_excluded_from_quiz_queue() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:known")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:next")

    screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:c:12:quiz")

    assert screen.screen_id == "ready_en_uk"
    service.client_runtime_input_service.handle_action(build_user(), "s:77:ready:ready_en_uk:yes")
    assert db.active_session["stage_queue_json"] == [11, 12]


def test_quiz_button_opens_ready_screen_with_expected_transition_text() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:next")

    screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:c:12:quiz")

    assert screen.screen_id == "ready_en_uk"
    assert screen.text == "Знайомство зі словами завершено.\n\nПереходимо до практики.\n\nГотові продовжувати?"
    assert screen.clear_chat is True


def test_stale_card_callback_is_ignored() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:next")

    screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:known")

    assert db.progress_updates == []
    assert screen.screen_id == "card:12"
    assert len(db.session_words) == 2


def test_card_flow_moves_to_ready_screen_after_last_word() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:next")

    screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:c:12:next")

    assert screen.screen_id == "ready_en_uk"
    assert screen.text == "Знайомство зі словами завершено.\n\nПереходимо до практики.\n\nГотові продовжувати?"
    assert screen.clear_chat is True


def test_ready_no_returns_to_menu_with_resume_option() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:next")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:12:next")

    screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:ready:ready_en_uk:no")

    assert screen.screen_id == "menu"
    assert "Коли будете готові" in screen.text
    assert any(button.action == "m:r" for button in screen.buttons)


def test_ready_yes_starts_quiz() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:next")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:12:next")

    screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:ready:ready_en_uk:yes")

    assert screen.screen_id.startswith("quiz_en_uk")
    assert "Вправа 1/3 - оберіть правильний український переклад" in screen.metadata["auxiliary_message_text"]
    assert "[\u00A0" not in screen.metadata["auxiliary_message_text"]
    assert "[⋯" in screen.text
    assert screen.metadata["button_row_widths"] == [1, 1, 1, 1]


def test_build_learning_runtime_passes_configured_quiz_queue_randomizer_to_quiz_start() -> None:
    db = FakeDatabase()

    def reverse_queue(queue: list[int]) -> list[int]:
        return list(reversed(queue))

    service = build_service(db, quiz_queue_randomizer=reverse_queue)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:next")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:12:next")

    screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:ready:ready_en_uk:yes")

    assert db.active_session["stage_queue_json"] == [12, 11]
    assert screen.screen_id == "quiz_en_uk:12"
    assert "read" in screen.text


def test_ready_screen_buttons_include_expected_stage() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:next")
    screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:c:12:next")

    assert [button.action for button in screen.buttons] == [
        "s:77:ready:ready_en_uk:yes",
        "s:77:ready:ready_en_uk:no",
    ]


def test_outdated_ready_callback_renders_current_stage_without_crashing() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:next")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:12:next")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:ready:ready_en_uk:yes")

    screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:ready:ready_en_uk:yes")

    assert screen.screen_id.startswith("quiz_en_uk")
    assert len(screen.buttons) == 4
    assert "Вправа 1/3 - оберіть правильний український переклад" in screen.metadata["auxiliary_message_text"]
    assert "[\u00A0" not in screen.metadata["auxiliary_message_text"]
    assert "learn" in screen.text
    assert "●○" in screen.text
    assert "\u2007" not in screen.text
    assert "learn" in screen.text
    assert screen.clear_chat is False


def test_first_wrong_answer_requeues_word() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:next")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:12:next")
    quiz_screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:ready:ready_en_uk:yes")
    wrong_index = next(index for index, button in enumerate(quiz_screen.buttons) if button.text != "вивчати")

    screen = service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:11:{wrong_index}")

    assert screen.screen_id.endswith(":feedback")
    assert screen.metadata["auto_advance_after_ms"] == 1500
    assert screen.metadata["next_action"] == "s:77:next"
    assert any(button.text.endswith("❌") for button in screen.buttons)
    assert any(button.text.endswith("✅") and "вивчати" in button.text for button in screen.buttons)
    assert db.active_session["stage_queue_json"][-1] == 11


def test_quiz_progress_uses_unique_words_after_requeue() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:next")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:12:next")
    quiz_screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:ready:ready_en_uk:yes")
    wrong_index = next(index for index, button in enumerate(quiz_screen.buttons) if button.text != "вивчати")

    service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:11:{wrong_index}")
    next_screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:next")

    assert "[\u00A0" not in next_screen.metadata["auxiliary_message_text"]
    assert "✗●" in next_screen.text


def test_quiz_feedback_shows_error_count_after_wrong_answer() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:next")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:12:next")
    quiz_screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:ready:ready_en_uk:yes")
    wrong_index = next(index for index, button in enumerate(quiz_screen.buttons) if button.text != "вивчати")

    feedback_screen = service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:11:{wrong_index}")

    assert "[\u00A0" not in feedback_screen.metadata["auxiliary_message_text"]
    assert "●○" in feedback_screen.text


def test_quiz_progress_shows_repeat_index_and_error_count_for_requeued_word() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:next")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:12:next")
    first_quiz_screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:ready:ready_en_uk:yes")
    wrong_index = next(index for index, button in enumerate(first_quiz_screen.buttons) if button.text != "вивчати")

    service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:11:{wrong_index}")
    second_quiz_screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:next")
    correct_index = next(index for index, button in enumerate(second_quiz_screen.buttons) if button.text == "читати")
    service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:12:{correct_index}")
    repeated_screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:next")

    assert "[\u00A0" not in repeated_screen.metadata["auxiliary_message_text"]
    assert "●✓" in repeated_screen.text


def test_quiz_feedback_uses_actual_error_index_for_second_wrong_repeat() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:next")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:12:next")
    first_quiz_screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:ready:ready_en_uk:yes")
    wrong_index = next(index for index, button in enumerate(first_quiz_screen.buttons) if button.text != "вивчати")

    service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:11:{wrong_index}")
    second_quiz_screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:next")
    correct_index = next(index for index, button in enumerate(second_quiz_screen.buttons) if button.text == "читати")
    service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:12:{correct_index}")
    repeated_screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:next")
    repeated_wrong_index = next(index for index, button in enumerate(repeated_screen.buttons) if button.text != "вивчати")

    feedback_screen = service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:11:{repeated_wrong_index}")

    assert "[\u00A0" not in feedback_screen.metadata["auxiliary_message_text"]
    assert "●✓" in feedback_screen.text


def test_stale_quiz_answer_callback_is_ignored() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:next")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:12:next")
    first_quiz = service.client_runtime_input_service.handle_action(build_user(), "s:77:ready:ready_en_uk:yes")
    correct_index = next(index for index, button in enumerate(first_quiz.buttons) if button.text == "вивчати")
    service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:11:{correct_index}")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:next")
    answers_before = len([event for event in db.saved_events if "answer" in event])

    screen = service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:11:{correct_index}")

    assert screen.screen_id.startswith("quiz_en_uk:12")
    assert len([event for event in db.saved_events if "answer" in event]) == answers_before


def test_second_wrong_answer_updates_priority() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:next")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:12:next")
    quiz_screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:ready:ready_en_uk:yes")
    wrong_index = next(index for index, button in enumerate(quiz_screen.buttons) if button.text != "вивчати")
    service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:11:{wrong_index}")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:a:12:0")

    screen = service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:11:{wrong_index}")

    assert screen.screen_id.endswith(":feedback")
    assert any(button.text.endswith("❌") for button in screen.buttons)
    assert db.progress_updates[-1]["review_priority_delta"] == 2


def test_gap_success_marks_word_as_completed() -> None:
    db = FakeDatabase()
    service = build_service(db)
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "active",
        "current_stage": "quiz_gap",
        "stage_queue_json": [11],
        "stage_position": 0,
    }

    quiz_screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")
    correct_index = next(index for index, button in enumerate(quiz_screen.buttons) if button.text == "learn")
    screen = service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:11:{correct_index}")

    assert screen.screen_id == "quiz_gap:11:feedback"
    assert any(button.text.endswith("✅") and "learn" in button.text for button in screen.buttons)
    assert screen.metadata["next_action"] == "s:77:next"
    assert screen.metadata["auto_advance_after_ms"] == 1500
    assert "&#x27;" not in screen.text
    assert "&amp;#x27;" not in screen.text
    assert db.progress_updates[-1]["learning_state"] == "learning"
    assert db.progress_updates[-1]["control_success_streak"] == 1
    assert db.progress_updates[-1]["review_stage"] == 1
    assert db.progress_updates[-1]["is_known"] is False
    assert db.progress_updates[-1]["completed_now"] is False
    assert db.progress_updates[-1]["next_review_at"] is not None


def test_fill_in_gap_preserves_apostrophes_while_escaping_html_markup() -> None:
    rendered = build_fill_in_gap_example("special", ["That's a <b>special</b> idea!"])

    assert rendered == "That's a &lt;b&gt;_____&lt;/b&gt; idea!"
    assert "&#x27;" not in rendered
    assert "&lt;b&gt;" in rendered
    assert "<b>" not in rendered


def test_quiz_prompt_text_places_progress_bar_above_short_word_prompt() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:11:next")
    service.client_runtime_input_service.handle_action(build_user(), "s:77:c:12:next")

    screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:ready:ready_en_uk:yes")

    assert screen.text.startswith("[⋯")
    assert "learn" in screen.text
    assert "\u2060" in screen.text
    assert "\u2007" not in screen.text
    assert "\n\n\n<b>learn</b>\n\n\n\u2060" in screen.text


def test_summary_screen_is_returned_after_gap_completion() -> None:
    db = FakeDatabase()
    service = build_service(db)
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "active",
        "current_stage": "quiz_gap",
        "stage_queue_json": [11, 12],
        "stage_position": 2,
    }

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")

    assert screen.screen_id == "summary:77"
    assert "Підсумок заняття" in screen.text
    assert "────────────" in screen.text
    assert "Слова в процесі вивчення: 6 слів" in screen.text
    assert "Слова потребують доопрацювання: 4 слова" in screen.text
    assert "Вивчені слова: 20/1000" in screen.text
    assert "Слово вважається вивченим після двох контрольних проходів без помилок після паузи." in screen.text
    assert "Супер, тренування завершено." in screen.text
    assert screen.buttons[0].action == "m:menu"
    assert screen.buttons[0].text == "Завершити тренування"


def test_summary_metrics_use_only_started_words() -> None:
    db = FakeDatabase()
    db.summary_counts_override = None
    db.word_progress = {
        101: {
            "telegram_user_id": 1,
            "word_id": 101,
            "is_known": False,
            "learning_state": "learning",
            "control_success_streak": 0,
            "review_priority": 0,
            "last_completed": None,
            "next_review_at": None,
        },
        102: {
            "telegram_user_id": 1,
            "word_id": 102,
            "is_known": False,
            "learning_state": "needs_work",
            "control_success_streak": 0,
            "review_priority": 0,
            "last_completed": None,
            "next_review_at": None,
        },
    }
    service = build_service(db)
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "completed",
        "current_stage": "completed",
        "stage_queue_json": [],
        "stage_position": 0,
    }

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")

    assert "Слова в процесі вивчення: 1 слово" in screen.text
    assert "Слова потребують доопрацювання: 1 слово" in screen.text
    assert "Вивчені слова: 0/2" in screen.text


def test_summary_existing_schedule_uses_datetime_without_seconds() -> None:
    db = FakeDatabase()
    db.summary_completed = datetime(2026, 4, 6, 16, 0, 0)
    db.existing_schedules = {
        datetime(2026, 4, 7, 10, 0, 0).date(): {
            "id": 501,
            "telegram_user_id": 1,
            "schedule_type": "planned",
            "scheduled_for": datetime(2026, 4, 7, 19, 0, 0),
        }
    }
    service = build_service(db)
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "completed",
        "current_stage": "completed",
        "stage_queue_json": [],
        "stage_position": 0,
    }

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")

    assert "Завершити тренування" in [button.text for button in screen.buttons]
    assert "2026-04-07 19:00:00" not in screen.text


def test_summary_after_afternoon_session_uses_finish_button() -> None:
    db = FakeDatabase()
    db.summary_completed = datetime(2026, 4, 6, 16, 0, 0)
    service = build_service(db)
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "completed",
        "current_stage": "completed",
        "stage_queue_json": [],
        "stage_position": 0,
    }

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")

    assert "Супер, тренування завершено." in screen.text
    assert [(button.action, button.text) for button in screen.buttons] == [("m:menu", "Завершити тренування")]


def test_summary_after_evening_session_mentions_tomorrow_daily_reminder() -> None:
    db = FakeDatabase()
    db.summary_completed = datetime(2026, 4, 6, 20, 30, 0)
    db.profile["daily_reminder_hour"] = 10
    db.profile["reminder_weekdays"] = [1]
    service = build_service(db)
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "completed",
        "current_stage": "completed",
        "stage_queue_json": [],
        "stage_position": 0,
    }

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")

    assert "Супер, тренування завершено." in screen.text
    assert "Завершити тренування" in [button.text for button in screen.buttons]


def test_summary_after_evening_session_mentions_next_non_tomorrow_daily_reminder() -> None:
    db = FakeDatabase()
    db.summary_completed = datetime(2026, 4, 6, 20, 30, 0)
    db.profile["daily_reminder_hour"] = 10
    db.profile["reminder_weekdays"] = [3]
    service = build_service(db)
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "completed",
        "current_stage": "completed",
        "stage_queue_json": [],
        "stage_position": 0,
    }

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")

    assert "Супер, тренування завершено." in screen.text
    assert "Завершити тренування" in [button.text for button in screen.buttons]


def test_summary_after_saving_today_followup_uses_explicit_planned_time() -> None:
    db = FakeDatabase()
    db.summary_completed = datetime(2026, 4, 6, 10, 0, 0)
    db.profile["daily_reminder_hour"] = 10
    db.profile["reminder_weekdays"] = [1]
    service = build_service(db, FixedTimeService(datetime(2026, 4, 6, 10, 0, 0)))
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "completed",
        "current_stage": "completed",
        "stage_queue_json": [],
        "stage_position": 0,
    }

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:p:today:77:hour:evening:19")

    assert "Тренування заплановано на сьогодні о 19:00." in screen.notice_text
    assert "Супер, тренування завершено." in screen.text
    assert [(button.action, button.text) for button in screen.buttons] == [("m:menu", "Завершити тренування")]


def test_summary_keeps_finish_button_when_daily_schedule_exists() -> None:
    db = FakeDatabase()
    db.summary_completed = datetime(2026, 4, 6, 10, 0, 0)
    db.existing_schedules = {
        datetime(2026, 4, 6, 10, 0, 0).date(): {
            "id": 501,
            "telegram_user_id": 1,
            "schedule_type": "daily",
            "scheduled_for": datetime(2026, 4, 6, 20, 0, 0),
        }
    }
    service = build_service(db)
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "words_target_count": 10,
        "status": "completed",
        "current_stage": "completed",
        "stage_queue_json": [],
        "stage_position": 0,
    }

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")

    assert [(button.action, button.text) for button in screen.buttons] == [("m:menu", "Завершити тренування")]


def test_today_planning_skips_period_picker_and_opens_evening_hours() -> None:
    db = FakeDatabase()
    db._learning_sessions[77] = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "status": "completed",
        "current_stage": "completed",
        "stage_queue_json": [],
        "stage_position": 0,
    }
    service = build_service(db, FixedTimeService(datetime(2026, 4, 9, 12, 0, 0)))

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:p:today:77")

    assert screen.screen_id == "planning:today:hours:evening"
    assert screen.buttons[0].text == "19:00"
    assert screen.buttons[-1].action == "m:p:today:77"


def test_planning_hour_picker_marks_existing_hour() -> None:
    db = FakeDatabase()
    db._learning_sessions[77] = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "status": "completed",
        "current_stage": "completed",
        "stage_queue_json": [],
        "stage_position": 0,
    }
    db.existing_schedules = {
        datetime(2026, 4, 7, 19, 0, 0).date(): {
            "id": 501,
            "telegram_user_id": 1,
            "schedule_type": "planned",
            "scheduled_for": datetime(2026, 4, 7, 19, 0, 0),
            "period_code": "evening",
        }
    }
    service = build_service(db, FixedTimeService(datetime(2026, 4, 6, 10, 0, 0)))

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:p:tomorrow:77:period:evening")

    assert "✓ 19:00" in [button.text for button in screen.buttons]


def test_today_planning_rejects_stale_or_foreign_session() -> None:
    db = FakeDatabase()
    db._learning_sessions[88] = {
        "id": 88,
        "telegram_user_id": 99,
        "language_level_id": 1,
        "status": "completed",
        "current_stage": "completed",
        "stage_queue_json": [],
        "stage_position": 0,
    }
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:p:today:88")

    assert screen.screen_id == "menu"


def test_today_planning_hides_past_evening_hours() -> None:
    db = FakeDatabase()
    db._learning_sessions[77] = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "status": "completed",
        "current_stage": "completed",
        "stage_queue_json": [],
        "stage_position": 0,
    }
    service = build_service(db, FixedTimeService(datetime(2026, 4, 6, 19, 30, 0)))

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:p:today:77")

    assert [button.text for button in screen.buttons[:-1]] == ["20:00", "21:00", "22:00"]


def test_today_planning_rejects_past_hour_submission() -> None:
    db = FakeDatabase()
    db._learning_sessions[77] = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "status": "completed",
        "current_stage": "completed",
        "stage_queue_json": [],
        "stage_position": 0,
    }
    service = build_service(db, FixedTimeService(datetime(2026, 4, 6, 20, 30, 0)))

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:p:today:77:hour:evening:19")

    assert screen.screen_id == "summary:77"
    assert screen.notice_text == "На сьогодні вільний час уже минув. Можна запланувати тренування на завтра."
    assert db.existing_schedules == {}


def test_followup_reminder_starts_session_from_source_session_words() -> None:
    db = FakeDatabase()
    db._learning_sessions[77] = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "status": "completed",
        "current_stage": "completed",
        "stage_queue_json": [],
        "stage_position": 0,
    }
    db.existing_schedules = {
        datetime(2026, 4, 6, 19, 0, 0).date(): {
            "id": 501,
            "telegram_user_id": 1,
            "schedule_type": "followup",
            "scheduled_for": datetime(2026, 4, 6, 19, 0, 0),
            "source_session_id": 77,
        }
    }
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "r:start:501")

    assert screen.screen_id == "card:11"
    assert db.active_session["session_type"] == "followup"
    assert db.active_session["source_session_id"] == 77
    assert db.active_session["words_target_count"] == 2
    assert db.updated_schedule_statuses[-1] == (501, "completed")


def test_followup_reminder_with_missing_source_session_does_not_complete_schedule() -> None:
    db = FakeDatabase()
    db.existing_schedules = {
        datetime(2026, 4, 6, 19, 0, 0).date(): {
            "id": 501,
            "telegram_user_id": 1,
            "schedule_type": "followup",
            "scheduled_for": datetime(2026, 4, 6, 19, 0, 0),
            "source_session_id": 77,
        }
    }
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "r:start:501")

    assert screen.screen_id == "menu"
    assert db.updated_schedule_statuses == []
    assert db.completed_due_schedule_calls[-1]["exclude_schedule_id"] == 501


def test_followup_gap_success_does_not_count_towards_learning_progress() -> None:
    db = FakeDatabase()
    service = build_service(db)
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "source_session_id": 55,
        "session_type": "followup",
        "words_target_count": 2,
        "status": "active",
        "current_stage": "quiz_gap",
        "stage_queue_json": [11],
        "stage_position": 0,
    }

    quiz_screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")
    correct_index = next(index for index, button in enumerate(quiz_screen.buttons) if button.text == "learn")
    service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:11:{correct_index}")

    assert db.progress_updates == []


def test_gap_quiz_renders_progress_bar_in_main_text() -> None:
    db = FakeDatabase()
    service = build_service(db)
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "source_session_id": None,
        "session_type": "regular",
        "words_target_count": 10,
        "status": "active",
        "current_stage": "quiz_gap",
        "stage_queue_json": [11],
        "stage_position": 0,
    }

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")

    first_line = screen.text.splitlines()[0]
    assert "⋯" in first_line
    assert "●" in first_line
    assert "<b>" in screen.text
    assert "&lt;b&gt;" not in screen.text
    assert "___" in screen.text


def test_first_control_review_success_sets_first_streak() -> None:
    current_time = datetime(2026, 4, 9, 10, 0, 0)
    db = FakeDatabase()
    service = build_service(db, FixedTimeService(current_time))
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "source_session_id": None,
        "session_type": "regular",
        "words_target_count": 10,
        "status": "active",
        "current_stage": "quiz_gap",
        "stage_queue_json": [11],
        "stage_position": 0,
    }
    db.word_progress[101] = {
        "telegram_user_id": 1,
        "word_id": 101,
        "is_known": False,
        "learning_state": "learning",
        "control_success_streak": 0,
        "review_priority": 0,
        "last_completed": None,
        "next_review_at": current_time - timedelta(minutes=1),
    }

    quiz_screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")
    correct_index = next(index for index, button in enumerate(quiz_screen.buttons) if button.text == "learn")
    service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:11:{correct_index}")

    assert db.progress_updates[-1]["control_success_streak"] == 1
    assert db.progress_updates[-1]["learning_state"] == "learning"
    assert db.progress_updates[-1]["is_known"] is False
    assert db.progress_updates[-1]["next_review_at"] == current_time + timedelta(hours=48)


def test_second_control_review_success_advances_srs_stage() -> None:
    current_time = datetime(2026, 4, 11, 10, 0, 0)
    db = FakeDatabase()
    service = build_service(db, FixedTimeService(current_time))
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "source_session_id": None,
        "session_type": "regular",
        "words_target_count": 10,
        "status": "active",
        "current_stage": "quiz_gap",
        "stage_queue_json": [11],
        "stage_position": 0,
    }
    db.word_progress[101] = {
        "telegram_user_id": 1,
        "word_id": 101,
        "is_known": False,
        "learning_state": "learning",
        "control_success_streak": 1,
        "review_priority": 0,
        "last_completed": None,
        "next_review_at": current_time - timedelta(minutes=1),
    }

    quiz_screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")
    correct_index = next(index for index, button in enumerate(quiz_screen.buttons) if button.text == "learn")
    service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:11:{correct_index}")

    assert db.progress_updates[-1]["control_success_streak"] == 2
    assert db.progress_updates[-1]["review_stage"] == 2
    assert db.progress_updates[-1]["learning_state"] == "learning"
    assert db.progress_updates[-1]["is_known"] is False
    assert db.progress_updates[-1]["completed_now"] is False
    assert db.progress_updates[-1]["next_review_at"] == current_time + timedelta(days=4)


def test_control_review_with_error_resets_streak() -> None:
    current_time = datetime(2026, 4, 11, 10, 0, 0)
    db = FakeDatabase()
    service = build_service(db, FixedTimeService(current_time))
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "source_session_id": None,
        "session_type": "regular",
        "words_target_count": 10,
        "status": "active",
        "current_stage": "quiz_gap",
        "stage_queue_json": [11],
        "stage_position": 0,
    }
    db.word_progress[101] = {
        "telegram_user_id": 1,
        "word_id": 101,
        "is_known": False,
        "learning_state": "learning",
        "control_success_streak": 1,
        "review_priority": 0,
        "last_completed": None,
        "next_review_at": current_time - timedelta(minutes=1),
    }

    quiz_screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")
    wrong_index = next(index for index, button in enumerate(quiz_screen.buttons) if button.text != "learn")
    service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:11:{wrong_index}")
    next_screen = service.client_runtime_input_service.handle_action(build_user(), "s:77:next")
    correct_index = next(index for index, button in enumerate(next_screen.buttons) if button.text == "learn")
    service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:11:{correct_index}")

    assert db.progress_updates[-1]["control_success_streak"] == 0
    assert db.progress_updates[-1]["learning_state"] == "needs_work"
    assert db.progress_updates[-1]["is_known"] is False


def test_control_review_error_resets_streak_immediately() -> None:
    current_time = datetime(2026, 4, 11, 10, 0, 0)
    db = FakeDatabase()
    service = build_service(db, FixedTimeService(current_time))
    db.active_session = {
        "id": 77,
        "telegram_user_id": 1,
        "language_level_id": 1,
        "source_session_id": None,
        "session_type": "regular",
        "words_target_count": 10,
        "status": "active",
        "current_stage": "quiz_en_uk",
        "stage_queue_json": [11],
        "stage_position": 0,
    }
    db.word_progress[101] = {
        "telegram_user_id": 1,
        "word_id": 101,
        "is_known": False,
        "learning_state": "learning",
        "control_success_streak": 1,
        "review_priority": 0,
        "last_completed": None,
        "next_review_at": current_time - timedelta(minutes=1),
    }

    quiz_screen = service.client_runtime_input_service.handle_action(build_user(), "m:r")
    wrong_index = next(index for index, button in enumerate(quiz_screen.buttons) if button.text != "вивчати")
    service.client_runtime_input_service.handle_action(build_user(), f"s:77:a:11:{wrong_index}")

    assert db.progress_updates[-1]["control_success_streak"] == 0
    assert db.progress_updates[-1]["learning_state"] == "needs_work"


def test_invalid_callback_payloads_fall_back_without_crashing() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_input_service.handle_action(build_user(), "m:s")

    invalid_actions = [
        "m:w:not-a-number",
        "m:n:hour:999",
        "m:p:today:not-a-session",
        "s:77:a:11:99",
    ]

    for action in invalid_actions:
        screen = service.client_runtime_input_service.handle_action(build_user(), action)
        assert screen.screen_id in {"menu", "menu:settings:web", "menu:notifications", "card:11"}


def test_checked_single_choice_text_routes_to_same_action() -> None:
    db = FakeDatabase()
    service = build_service(db)

    level_screen = service.client_runtime_input_service.handle_text_input(build_user(), "✓ A1")
    count_screen = service.client_runtime_input_service.handle_text_input(build_user(), "✓ 10 слів")
    period_screen = service.client_runtime_input_service.handle_text_input(build_user(), "✓ Вечір")
    hour_screen = service.client_runtime_input_service.handle_text_input(build_user(), "✓ 19:00")

    assert level_screen.screen_id == "menu:settings:web"
    assert count_screen.screen_id == "menu:settings:web"
    assert period_screen.screen_id == "menu:notifications:hours:evening"
    assert hour_screen.screen_id == "menu:notifications:days"


def test_dispatch_due_reminders_returns_screen_models() -> None:
    db = FakeDatabase()
    db.due_schedules = [
        {
            "id": 501,
            "telegram_user_id": 1,
            "chat_id": 99,
            "schedule_type": "daily",
        }
    ]
    service = build_service(db)

    reminders = service.client_runtime_reminder_service.dispatch_due_reminders()

    assert len(reminders) == 1
    assert reminders[0].chat_id == 99
    assert reminders[0].screen.screen_id == "reminder:501"
    assert reminders[0].screen.text == "Час потренувати слова. Готові?"


def test_dispatch_due_reminders_executes_with_noop_dispatch_lock() -> None:
    db = FakeDatabase()
    db.due_schedules = [
        {
            "id": 501,
            "telegram_user_id": 1,
            "chat_id": 99,
            "schedule_type": "daily",
        }
    ]
    service = build_service(db, TimeService("Europe/Kyiv"))

    reminders = service.client_runtime_reminder_service.dispatch_due_reminders()

    assert len(reminders) == 1


def test_skip_reminder_updates_schedule_status() -> None:
    db = FakeDatabase()
    db.existing_schedules = {
        datetime(2026, 4, 6, 10, 0, 0).date(): {
            "id": 501,
            "telegram_user_id": 1,
            "schedule_type": "daily",
            "scheduled_for": datetime(2026, 4, 6, 10, 0, 0),
        }
    }
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "r:skip:501")

    assert db.updated_schedule_statuses[-1] == (501, "skipped")
    assert screen.screen_id == "menu"
    assert "пропущено" not in screen.text
    assert screen.metadata["force_resend"] is True


def test_snooze_reminder_falls_back_as_unknown_action() -> None:
    db = FakeDatabase()
    db.existing_schedules = {
        datetime(2026, 4, 6, 10, 0, 0).date(): {
            "id": 501,
            "telegram_user_id": 1,
            "schedule_type": "daily",
            "scheduled_for": datetime(2026, 4, 6, 10, 0, 0),
        }
    }
    service = build_service(db, FixedTimeService(datetime(2026, 4, 6, 10, 7, 0)))

    screen = service.client_runtime_input_service.handle_action(build_user(), "r:snooze:501")

    assert screen.screen_id == "menu"
    assert screen.metadata["force_resend"] is False
    assert db.updated_schedule_statuses == []


def test_main_menu_action_marks_screen_for_fresh_resend() -> None:
    service = build_service(FakeDatabase())

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:menu")

    assert screen.screen_id == "menu"
    assert screen.metadata["force_resend"] is True


def test_track_bot_message_uses_backend_retention_policy() -> None:
    db = FakeDatabase()
    service = build_service(db)

    service.client_runtime_bot_message_service.track_bot_message(
        telegram_user_id=1,
        chat_id=99,
        message_id=501,
        screen_id="menu",
    )

    tracked = db.created_bot_messages[-1]
    assert tracked["screen_id"] == "menu"
    assert (tracked["delete_after"] - tracked["current_time"]).days == 30


def test_track_bot_message_respects_delete_after_hours_override() -> None:
    db = FakeDatabase()
    service = build_service(db)

    service.client_runtime_bot_message_service.track_bot_message(
        telegram_user_id=1,
        chat_id=99,
        message_id=501,
        screen_id="import_words:summary:7",
        delete_after_hours=24,
    )

    tracked = db.created_bot_messages[-1]
    assert tracked["screen_id"] == "import_words:summary:7"
    assert (tracked["delete_after"] - tracked["current_time"]).total_seconds() == 24 * 60 * 60


def test_dispatch_due_bot_message_cleanup_returns_backend_payload() -> None:
    service = build_service(FakeDatabase())

    rows = service.client_runtime_bot_message_service.dispatch_due_bot_message_cleanup()

    assert rows[0]["id"] == 901
    assert rows[0]["message_id"] == 501


def test_dispatch_due_bot_message_cleanup_executes_with_noop_dispatch_lock() -> None:
    service = build_service(FakeDatabase(), TimeService("Europe/Kyiv"))

    rows = service.client_runtime_bot_message_service.dispatch_due_bot_message_cleanup()

    assert rows[0]["id"] == 901


def test_process_due_user_vocabulary_imports_executes_with_noop_dispatch_lock() -> None:
    service = build_service(
        FakeDatabase(),
        TimeService("Europe/Kyiv"),
    )
    runtime_service = CapturingUserImportRuntimeService()
    service.user_import_runtime_service = runtime_service
    service.user_import_scheduled_runtime_service.user_import_runtime_service = runtime_service

    assert service.user_import_scheduled_runtime_service.process_due_user_vocabulary_imports() == ["processed"]
    assert runtime_service.due_import_calls == 1


def test_process_user_import_attribute_queue_now_executes_with_noop_dispatch_lock() -> None:
    service = build_service(
        FakeDatabase(),
        TimeService("Europe/Kyiv"),
    )
    runtime_service = CapturingUserImportRuntimeService()
    service.user_import_runtime_service = runtime_service
    service.user_import_scheduled_runtime_service.user_import_runtime_service = runtime_service
    current_time = datetime(2026, 5, 1, 9, 0, 0)

    service.user_import_scheduled_runtime_service.process_user_import_attribute_queue_now(42, current_time)

    assert runtime_service.calls == [current_time]


def test_get_bot_message_log_returns_backend_row() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_bot_message_service.track_bot_message(
        telegram_user_id=1,
        chat_id=99,
        message_id=501,
        screen_id="menu",
    )

    row = service.client_runtime_bot_message_service.get_bot_message_log(
        telegram_user_id=1,
        chat_id=99,
        message_id=501,
    )

    assert row is not None
    assert row["message_id"] == 501
    assert row["screen_id"] == "menu"


def test_list_active_bot_messages_returns_backend_rows() -> None:
    db = FakeDatabase()
    service = build_service(db)
    service.client_runtime_bot_message_service.track_bot_message(
        telegram_user_id=1,
        chat_id=99,
        message_id=501,
        screen_id="menu",
    )

    rows = service.client_runtime_bot_message_service.list_active_bot_messages(
        telegram_user_id=1,
        chat_id=99,
    )

    assert rows[0]["message_id"] == 501
    assert rows[0]["screen_id"] == "menu"


def test_save_bot_message_cleanup_result_passes_result_to_db() -> None:
    db = FakeDatabase()
    service = build_service(db)

    service.client_runtime_bot_message_service.save_bot_message_cleanup_result(
        message_log_id=901,
        is_deleted=False,
        error_text="message not found",
    )

    assert db.cleanup_results[-1]["message_log_id"] == 901
    assert db.cleanup_results[-1]["is_deleted"] is False
    assert db.cleanup_results[-1]["error_text"] == "message not found"


def test_completed_level_offers_next_unfinished_level() -> None:
    db = FakeDatabase()
    db.summary_counts_override = None
    db.get_level_word_totals = lambda: {1: 2, 2: 2, 3: 2, 4: 2, 5: 2, 6: 2}
    db.word_progress = {
        (1, 101): {
            "level_run_id": 1,
            "telegram_user_id": 1,
            "word_id": 101,
            "learning_state": "learned",
        },
        (1, 102): {
            "level_run_id": 1,
            "telegram_user_id": 1,
            "word_id": 102,
            "learning_state": "learned",
        },
    }
    db.select_lesson_words = lambda telegram_user_id, level_id, words_limit: []
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:s")

    assert screen.screen_id == "level:completed"
    assert "A1" in screen.text
    assert "A2" in screen.text
    assert screen.buttons[0].action == "m:level:next:A2"


def test_completed_course_offers_course_replay() -> None:
    db = FakeDatabase()
    db.profile["language_level_id"] = 6
    db.profile["language_level_title"] = "C2"
    db.summary_counts_override = None
    db.get_level_word_totals = lambda: {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1}
    db.level_runs = {}
    db._active_level_runs = {}
    db.word_progress = {}
    for index, level_id in enumerate(range(1, 7), start=1):
        db.level_runs[index] = {
            "id": index,
            "telegram_user_id": 1,
            "level_id": level_id,
            "run_no": 1,
            "status": "completed",
            "completed": datetime(2026, 4, 8, 10, 0, 0),
        }
        db.word_progress[(index, 100 + level_id)] = {
            "level_run_id": index,
            "telegram_user_id": 1,
            "word_id": 100 + level_id,
            "learning_state": "learned",
        }
    db._level_run_seq = 7
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:s")

    assert screen.screen_id == "course:completed"
    assert any(button.action == "m:course:repeat" for button in screen.buttons)


def test_completed_high_levels_offer_unfinished_lower_levels() -> None:
    db = FakeDatabase()
    db.profile["language_level_id"] = 6
    db.profile["language_level_title"] = "C2"
    db.summary_counts_override = None
    db.get_level_word_totals = lambda: {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1}
    db.level_runs = {}
    db._active_level_runs = {}
    db.word_progress = {}
    for index, level_id in enumerate(range(2, 7), start=2):
        db.level_runs[index] = {
            "id": index,
            "telegram_user_id": 1,
            "level_id": level_id,
            "run_no": 1,
            "status": "completed",
            "completed": datetime(2026, 4, 8, 10, 0, 0),
        }
        db.word_progress[(index, 200 + level_id)] = {
            "level_run_id": index,
            "telegram_user_id": 1,
            "word_id": 200 + level_id,
            "learning_state": "learned",
        }
    db._level_run_seq = 10
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:s")

    assert screen.screen_id == "course:lower-levels"
    assert any(button.action == "m:course:repeat:A1" for button in screen.buttons)


def test_repeat_course_from_selected_level_creates_new_run_and_starts_session() -> None:
    db = FakeDatabase()
    db.profile["language_level_id"] = 6
    db.profile["language_level_title"] = "C2"
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:course:repeat:A2")

    assert db.saved_levels[-1] == "A2"
    latest_run = db.get_latest_level_run(1, 2)
    assert latest_run is not None
    assert latest_run["status"] == "active"
    assert screen.screen_id.startswith("card:")


def test_completed_level_skips_empty_higher_levels() -> None:
    db = FakeDatabase()
    db.summary_counts_override = None
    db.get_level_word_totals = lambda: {1: 2, 2: 0, 3: 2, 4: 0, 5: 0, 6: 0}
    db.word_progress = {
        (1, 101): {
            "level_run_id": 1,
            "telegram_user_id": 1,
            "word_id": 101,
            "learning_state": "learned",
        },
        (1, 102): {
            "level_run_id": 1,
            "telegram_user_id": 1,
            "word_id": 102,
            "learning_state": "learned",
        },
    }
    db.select_lesson_words = lambda telegram_user_id, level_id, words_limit: []
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:s")

    assert screen.screen_id == "level:completed"
    assert screen.buttons[0].action == "m:level:next:B1"


def test_level_menu_shows_only_levels_present_in_database() -> None:
    db = FakeDatabase()
    db.language_levels = [
        {"id": 1, "title": "A1", "description": None},
        {"id": 3, "title": "B1", "description": None},
    ]
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:levels")

    assert [button.action for button in screen.buttons] == ["web:settings", "m:menu"]


def test_missing_level_action_falls_back_without_error() -> None:
    db = FakeDatabase()
    db.language_levels = [
        {"id": 1, "title": "A1", "description": None},
    ]
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:l:B2")

    assert screen.screen_id == "menu:settings:web"
    assert db.saved_levels == []


def test_course_repeat_picker_hides_levels_without_words() -> None:
    db = FakeDatabase()
    db.get_level_word_totals = lambda: {1: 3, 2: 0, 3: 2}
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:course:repeat")

    assert [button.action for button in screen.buttons[:2]] == ["m:course:repeat:A1", "m:course:repeat:B1"]


def test_course_repeat_falls_back_to_menu_when_no_levels_have_words() -> None:
    db = FakeDatabase()
    db.get_level_word_totals = lambda: {}
    service = build_service(db)

    screen = service.client_runtime_input_service.handle_action(build_user(), "m:course:repeat")

    assert screen.screen_id == "menu"
    assert "не вдалося сформувати підбірку" in screen.text
