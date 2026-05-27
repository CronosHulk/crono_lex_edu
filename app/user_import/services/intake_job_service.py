from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.storage.user_import_artifacts import UserImportArtifactStorageProvider


class UserImportIntakeJobJobsPort(Protocol):
    def get_existing_lookup_words(self, telegram_user_id: int, lookup_words: list[str]) -> set[str]: ...

    def create_job(
        self,
        telegram_user_id: int,
        source_type: str,
        source_identifier: str,
        storage_path: str,
        items: list[dict[str, Any]],
        current_time: datetime,
        task_log_id: int | None = None,
    ) -> dict[str, Any]: ...

    def list_items(self, job_id: int) -> list[dict[str, Any]]: ...


class UserImportIntakeJobTaskLogsPort(Protocol):
    def get(self, task_log_id: int) -> dict[str, Any] | None: ...

    def get_latest_for_import_job(
        self,
        import_job_id: int,
        *,
        task_type: str | None = None,
    ) -> dict[str, Any] | None: ...


class UserImportIntakeJobDatabasePort(Protocol):
    @property
    def user_import_jobs(self) -> UserImportIntakeJobJobsPort: ...

    @property
    def task_logs(self) -> UserImportIntakeJobTaskLogsPort: ...


class UserImportIntakeJobService:
    def __init__(
        self,
        db: UserImportIntakeJobDatabasePort,
        *,
        max_import_entries_per_submission: Callable[[], int],
        build_import_snapshot: Callable[..., dict[str, Any]],
        artifact_storage_provider: UserImportArtifactStorageProvider,
    ) -> None:
        self.db = db
        self.max_import_entries_per_submission = max_import_entries_per_submission
        self.build_import_snapshot = build_import_snapshot
        self.artifact_storage_provider = artifact_storage_provider

    def build_user_import_intake_snapshot(
        self,
        parsed_words: list[Any],
        existing_lookup_words: set[str],
        invalid_fragments: list[str],
        *,
        max_words_per_bind: int,
    ) -> dict[str, Any]:
        existing_lookup_words_list: list[str] = []
        queued_lookup_words: list[str] = []
        seen_existing: set[str] = set()
        seen_queued: set[str] = set()
        normalized_invalid_fragments = self._normalize_nonempty_strings(invalid_fragments)
        for item in parsed_words:
            lookup_word = str(getattr(item, "lookup_word", "")).strip()
            if not lookup_word:
                continue
            if lookup_word in existing_lookup_words:
                if lookup_word not in seen_existing:
                    seen_existing.add(lookup_word)
                    existing_lookup_words_list.append(lookup_word)
                continue
            if lookup_word in seen_queued:
                continue
            seen_queued.add(lookup_word)
            queued_lookup_words.append(lookup_word)
            if len(queued_lookup_words) >= max_words_per_bind:
                break
        return {
            "existing_lookup_words": existing_lookup_words_list,
            "queued_lookup_words": queued_lookup_words,
            "invalid_fragments": normalized_invalid_fragments,
            "invalid_fragments_count": len(normalized_invalid_fragments),
            "existing_lookup_words_count": len(existing_lookup_words_list),
            "queued_lookup_words_count": len(queued_lookup_words),
        }

    def get_user_import_intake_snapshot(self, job: dict[str, Any]) -> dict[str, Any]:
        task_log = None
        task_log_id = job.get("task_log_id")
        if task_log_id is not None:
            task_log = self.db.task_logs.get(int(task_log_id))
        if task_log is None:
            task_log = self.db.task_logs.get_latest_for_import_job(int(job["id"]), task_type="bound_google_doc_sync")
        result = dict(task_log.get("result_json") or {}) if task_log is not None else {}
        existing_lookup_words = self._normalize_nonempty_strings(result.get("existing_lookup_words"))
        queued_lookup_words = self._normalize_nonempty_strings(result.get("queued_lookup_words"))
        invalid_fragments = self._normalize_nonempty_strings(result.get("invalid_fragments"))
        if not existing_lookup_words or not queued_lookup_words:
            items = self.db.user_import_jobs.list_items(job["id"])
            if not existing_lookup_words:
                existing_lookup_words = [str(item["lookup_word"]) for item in items if item["status"] == "found_existing"]
            if not queued_lookup_words:
                queued_lookup_words = [
                    str(item["lookup_word"]) for item in items if item["status"] == "queued_for_attributes"
                ]
        invalid_fragments_count = int(result.get("invalid_fragments_count") or len(invalid_fragments))
        return {
            "existing_lookup_words": existing_lookup_words,
            "queued_lookup_words": queued_lookup_words,
            "invalid_fragments": invalid_fragments,
            "invalid_fragments_count": invalid_fragments_count,
            "existing_lookup_words_count": len(existing_lookup_words),
            "queued_lookup_words_count": len(queued_lookup_words),
        }

    def create_user_import_job_from_words(
        self,
        *,
        telegram_user_id: int,
        source_identifier: str,
        parsed_words: list[Any],
        current_time: datetime,
        task_log_id: int | None = None,
        source_type: str = "google_doc",
        max_words_per_job: int | None = None,
    ) -> tuple[int, int, int | None]:
        already_seen_lookup_words = {
            _normalize_lookup_word(value)
            for value in self.db.user_import_jobs.get_existing_lookup_words(
                telegram_user_id,
                [item.lookup_word for item in parsed_words],
            )
            if _normalize_lookup_word(value)
        }
        new_words = [
            item
            for item in parsed_words
            if _normalize_lookup_word(getattr(item, "lookup_word", "")) not in already_seen_lookup_words
        ]
        if not new_words:
            return 0, len(already_seen_lookup_words), None

        max_words_per_bind = max(int(max_words_per_job or self._max_import_entries_per_submission()), 1)
        batch_words = new_words[:max_words_per_bind]

        storage_path = self.artifact_storage_provider.write_json_snapshot(
            telegram_user_id,
            current_time,
            self.build_import_snapshot(
                telegram_user_id=telegram_user_id,
                source_identifier=source_identifier,
                parsed_words=batch_words,
            ),
        )
        job = self.db.user_import_jobs.create_job(
            telegram_user_id=telegram_user_id,
            task_log_id=task_log_id,
            source_type=source_type,
            source_identifier=source_identifier,
            storage_path=storage_path,
            items=[
                {
                    "raw_value": item.raw_value,
                    "lookup_word": item.lookup_word,
                    "translation_hint": getattr(item, "translation_hint", None),
                    "validated_lookup_word": getattr(item, "validated_lookup_word", None),
                    "validated_part_of_speech": getattr(item, "validated_part_of_speech", None),
                    "validated_translation_uk": getattr(item, "validated_translation_uk", None),
                    "validated_translation_ru": getattr(item, "validated_translation_ru", None),
                    "validated_translation_pl": getattr(item, "validated_translation_pl", None),
                }
                for item in batch_words
            ],
            current_time=current_time,
        )
        return len(batch_words), len(already_seen_lookup_words), int(job["id"])

    def _max_import_entries_per_submission(self) -> int:
        return max(int(self.max_import_entries_per_submission()), 1)

    @staticmethod
    def _normalize_nonempty_strings(values: Any) -> list[str]:
        if not isinstance(values, list):
            return []
        result: list[str] = []
        for value in values:
            text = str(value).strip()
            if text:
                result.append(text)
        return result


def _normalize_lookup_word(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())
