from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, cast
from uuid import UUID

from app.domain.user_dictionary.constants import (
    USER_DICTIONARY_QUEUED_DETAILS,
    USER_DICTIONARY_READY,
    USER_WORD_ASSIGNMENT_AVAILABLE,
    USER_WORD_ASSIGNMENT_WAITING,
    USER_WORD_SOURCE_CORE,
    USER_WORD_SOURCE_USER,
)
from app.user_import.helpers.job_identity import resolve_job_user_uuid


class UserImportPreparationJobsPort(Protocol):
    def list_items(self, job_id: int) -> list[dict[str, Any]]: ...


class UserImportPreparationItemsPort(Protocol):
    def mark_existing_word(self, item_id: int, *, word_id: int, current_time: datetime) -> None: ...

    def mark_rejected(self, item_id: int, *, error_text: str, current_time: datetime) -> None: ...

    def mark_user_dictionary_entry(
        self,
        item_id: int,
        *,
        user_dictionary_entry_id: int,
        status: str,
        error_text: str | None,
        current_time: datetime,
    ) -> None: ...


class SupportsFindDictionaryEntryByPartOfSpeech(Protocol):
    def find_by_word_and_part_of_speech(
        self,
        word: str,
        part_of_speech: str,
    ) -> dict[str, Any] | None: ...


class SupportsListDictionaryEntriesByWord(Protocol):
    def list_by_word(self, word: str) -> list[dict[str, Any]]: ...


class SupportsCreateCoreAssignmentForUserUuid(Protocol):
    def create_user_core_word_assignment_for_user_uuid(
        self,
        user_uuid: str,
        word_id: int,
        *,
        current_time: datetime | None = None,
    ) -> None: ...


class UserImportPreparationDictionaryLookupPort(Protocol):
    def find_by_word(self, word: str) -> dict[str, Any] | None: ...

    def create_user_core_word_assignment(
        self,
        telegram_user_id: int,
        word_id: int,
        *,
        current_time: datetime | None = None,
    ) -> None: ...


class SupportsFindUserDictionaryEntryByWord(Protocol):
    def find_entry_by_word(self, word: str) -> dict[str, Any] | None: ...


class UserImportPreparationUserDictionaryPort(Protocol):
    def find_entry_by_word_and_part_of_speech(
        self,
        word: str,
        part_of_speech: str,
    ) -> dict[str, Any] | None: ...

    def create_entry(
        self,
        *,
        word: str,
        part_of_speech: str,
        created_by_user_uuid: UUID | None,
        translation_uk: str | None,
        translation_ru: str | None,
        translation_pl: str | None,
        status: str,
        source_provider_status_json: dict[str, Any],
        current_time: datetime,
    ) -> dict[str, Any]: ...

    def create_assignment(
        self,
        *,
        user_uuid: UUID,
        word_source: str,
        word_id: int,
        status: str,
        import_job_id: int,
        import_item_id: int,
        current_time: datetime,
    ) -> None: ...


class UserImportPreparationDatabasePort(Protocol):
    @property
    def user_import_jobs(self) -> UserImportPreparationJobsPort: ...

    @property
    def user_import_items(self) -> UserImportPreparationItemsPort: ...

    @property
    def dictionary_lookup(self) -> UserImportPreparationDictionaryLookupPort: ...

    @property
    def user_dictionary(self) -> UserImportPreparationUserDictionaryPort: ...


class UserImportPreparationAccessPolicy(Protocol):
    def user_uuid_for_telegram_user(self, telegram_user_id: int) -> UUID | str | None: ...

    def is_lookup_only_import(self, user_uuid: UUID, *, current_time: datetime) -> bool: ...

    def can_create_new_user_dictionary_entry(self, user_uuid: UUID | None, *, current_time: datetime) -> bool: ...


LOOKUP_ONLY_IMPORT_REJECTED_REASON = (
    "Smart import is not available on the free account. "
    "Upgrade your plan for deeper AI analysis of new words."
)


class UserImportPreparationService:
    def __init__(
        self,
        db: UserImportPreparationDatabasePort,
        access_policy: UserImportPreparationAccessPolicy,
    ) -> None:
        self.db = db
        self.access_policy = access_policy

    def prepare_import_job_items(self, job: dict[str, Any], current_time: datetime, *, task_log_id: int | None) -> None:
        user_uuid = self._resolve_job_user_uuid(job)
        for item in self.db.user_import_jobs.list_items(job["id"]):
            if item["status"] != "pending":
                continue
            effective_lookup_word = self._clean_optional(item.get("validated_lookup_word")) or item["lookup_word"]
            validated_part_of_speech = self._clean_optional(item.get("validated_part_of_speech"))
            existing_words = self._find_dictionary_entries(effective_lookup_word, validated_part_of_speech)
            if existing_words:
                for existing_word in existing_words:
                    self._create_core_assignment(user_uuid, int(existing_word["id"]), job, current_time=current_time)
                    self._create_word_assignment(
                        user_uuid=user_uuid,
                        word_source=USER_WORD_SOURCE_CORE,
                        word_id=int(existing_word["id"]),
                        status=USER_WORD_ASSIGNMENT_AVAILABLE,
                        import_job_id=int(job["id"]),
                        import_item_id=int(item["id"]),
                        current_time=current_time,
                    )
                self.db.user_import_items.mark_existing_word(
                    item["id"],
                    word_id=existing_words[0]["id"],
                    current_time=current_time,
                )
                continue
            if validated_part_of_speech is None and self._is_lookup_only_import(user_uuid, current_time):
                self.db.user_import_items.mark_rejected(
                    item["id"],
                    error_text=LOOKUP_ONLY_IMPORT_REJECTED_REASON,
                    current_time=current_time,
                )
                continue
            user_dictionary_entry = self._find_user_dictionary_entry(effective_lookup_word, validated_part_of_speech)
            if user_dictionary_entry is not None:
                assignment_status = (
                    USER_WORD_ASSIGNMENT_AVAILABLE
                    if user_dictionary_entry.get("status") == USER_DICTIONARY_READY
                    else USER_WORD_ASSIGNMENT_WAITING
                )
                item_status = (
                    "ready_for_rotation"
                    if assignment_status == USER_WORD_ASSIGNMENT_AVAILABLE
                    else "waiting_for_user_dictionary_entry"
                )
                self._create_word_assignment(
                    user_uuid=user_uuid,
                    word_source=USER_WORD_SOURCE_USER,
                    word_id=int(user_dictionary_entry["id"]),
                    status=assignment_status,
                    import_job_id=int(job["id"]),
                    import_item_id=int(item["id"]),
                    current_time=current_time,
                )
                self.db.user_import_items.mark_user_dictionary_entry(
                    item["id"],
                    user_dictionary_entry_id=int(user_dictionary_entry["id"]),
                    status=item_status,
                    error_text=None,
                    current_time=current_time,
                )
                continue
            if validated_part_of_speech is None:
                self.db.user_import_items.mark_rejected(
                    item["id"],
                    error_text="part_of_speech is required for user dictionary import",
                    current_time=current_time,
                )
                continue
            translation_uk = self._clean_optional(item.get("validated_translation_uk")) or self._clean_optional(
                item.get("translation_hint")
            )
            translation_ru = self._clean_optional(item.get("validated_translation_ru"))
            translation_pl = self._clean_optional(item.get("validated_translation_pl"))
            if not self._can_create_new_user_dictionary_entry(user_uuid, current_time):
                self.db.user_import_items.mark_rejected(
                    item["id"],
                    error_text="weekly new word import quota exceeded",
                    current_time=current_time,
                )
                continue
            user_dictionary_entry = self.db.user_dictionary.create_entry(
                word=effective_lookup_word,
                part_of_speech=validated_part_of_speech,
                created_by_user_uuid=user_uuid,
                translation_uk=translation_uk,
                translation_ru=translation_ru,
                translation_pl=translation_pl,
                status=USER_DICTIONARY_QUEUED_DETAILS,
                source_provider_status_json=self._build_source_provider_status(item),
                current_time=current_time,
            )
            self._create_word_assignment(
                user_uuid=user_uuid,
                word_source=USER_WORD_SOURCE_USER,
                word_id=int(user_dictionary_entry["id"]),
                status=USER_WORD_ASSIGNMENT_WAITING,
                import_job_id=int(job["id"]),
                import_item_id=int(item["id"]),
                current_time=current_time,
            )
            self.db.user_import_items.mark_user_dictionary_entry(
                item["id"],
                user_dictionary_entry_id=int(user_dictionary_entry["id"]),
                status="waiting_for_user_dictionary_entry",
                error_text=None,
                current_time=current_time,
            )

    def _find_dictionary_entries(self, lookup_word: str, part_of_speech: str | None) -> list[dict[str, Any]]:
        dictionary_lookup = self.db.dictionary_lookup
        if part_of_speech and hasattr(dictionary_lookup, "find_by_word_and_part_of_speech"):
            dictionary_lookup = cast(SupportsFindDictionaryEntryByPartOfSpeech, dictionary_lookup)
            row = dictionary_lookup.find_by_word_and_part_of_speech(lookup_word, part_of_speech)
            return [row] if row is not None else []
        if hasattr(dictionary_lookup, "list_by_word"):
            dictionary_lookup = cast(SupportsListDictionaryEntriesByWord, dictionary_lookup)
            return list(dictionary_lookup.list_by_word(lookup_word))
        row = dictionary_lookup.find_by_word(lookup_word)
        return [row] if row is not None else []

    def _find_user_dictionary_entry(self, lookup_word: str, part_of_speech: str | None) -> dict[str, Any] | None:
        if not hasattr(self.db, "user_dictionary"):
            return None
        user_dictionary = self.db.user_dictionary
        if part_of_speech:
            return user_dictionary.find_entry_by_word_and_part_of_speech(lookup_word, part_of_speech)
        if hasattr(user_dictionary, "find_entry_by_word"):
            user_dictionary = cast(SupportsFindUserDictionaryEntryByWord, user_dictionary)
            return user_dictionary.find_entry_by_word(lookup_word)
        return None

    def _create_word_assignment(
        self,
        *,
        user_uuid: UUID | None,
        word_source: str,
        word_id: int,
        status: str,
        import_job_id: int,
        import_item_id: int,
        current_time: datetime,
    ) -> None:
        if not hasattr(self.db, "user_dictionary"):
            return
        if user_uuid is None:
            return
        self.db.user_dictionary.create_assignment(
            user_uuid=user_uuid,
            word_source=word_source,
            word_id=word_id,
            status=status,
            import_job_id=import_job_id,
            import_item_id=import_item_id,
            current_time=current_time,
        )

    def _resolve_job_user_uuid(self, job: dict[str, Any]) -> UUID | None:
        user_uuid = resolve_job_user_uuid(job)
        if user_uuid is not None:
            return user_uuid
        telegram_user_id = job.get("telegram_user_id")
        if telegram_user_id is None:
            return None
        raw_user_id = self.access_policy.user_uuid_for_telegram_user(int(telegram_user_id))
        return UUID(str(raw_user_id)) if raw_user_id else None

    def _create_core_assignment(
        self,
        user_uuid: UUID | None,
        word_id: int,
        job: dict[str, Any],
        *,
        current_time: datetime,
    ) -> None:
        dictionary_lookup = self.db.dictionary_lookup
        if user_uuid is not None and hasattr(dictionary_lookup, "create_user_core_word_assignment_for_user_uuid"):
            dictionary_lookup = cast(SupportsCreateCoreAssignmentForUserUuid, dictionary_lookup)
            dictionary_lookup.create_user_core_word_assignment_for_user_uuid(
                str(user_uuid),
                word_id,
                current_time=current_time,
            )
            return
        telegram_user_id = job.get("telegram_user_id")
        if telegram_user_id is None:
            return
        dictionary_lookup.create_user_core_word_assignment(int(telegram_user_id), word_id, current_time=current_time)

    def _build_source_provider_status(self, item: dict[str, Any]) -> dict[str, Any]:
        if not any(
            item.get(key)
            for key in (
                "validated_part_of_speech",
                "validated_lookup_word",
                "validated_translation_uk",
                "validated_translation_ru",
                "validated_translation_pl",
            )
        ):
            return {}
        return {
            "import_validation": {
                "status": "ok",
                "lookup_word": bool(item.get("validated_lookup_word")),
                "part_of_speech": bool(item.get("validated_part_of_speech")),
                "translation_uk": bool(item.get("validated_translation_uk")),
                "translation_ru": bool(item.get("validated_translation_ru")),
                "translation_pl": bool(item.get("validated_translation_pl")),
            }
        }

    def _can_create_new_user_dictionary_entry(self, user_uuid: UUID | None, current_time: datetime) -> bool:
        return self.access_policy.can_create_new_user_dictionary_entry(
            user_uuid,
            current_time=current_time,
        )

    def _is_lookup_only_import(self, user_uuid: UUID | None, current_time: datetime) -> bool:
        if user_uuid is None:
            return False
        return self.access_policy.is_lookup_only_import(user_uuid, current_time=current_time)

    def _clean_optional(self, value: Any) -> str | None:
        candidate = " ".join(str(value or "").strip().split())
        return candidate or None
