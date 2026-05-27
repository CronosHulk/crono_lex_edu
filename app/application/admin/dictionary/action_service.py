from __future__ import annotations

from typing import Protocol

from app.application.admin.dictionary.archive_entry import (
    ArchiveDictionaryEntryDatabasePort,
    archive_dictionary_entry,
)
from app.application.admin.dictionary.delete_entry import (
    DeleteDictionaryEntryDatabasePort,
    delete_dictionary_entry,
)
from app.application.admin.dictionary.verify_entries import (
    VerifyDictionaryEntriesDatabasePort,
    verify_dictionary_entries,
)
from app.time_utils import TimeService


class AdminDictionaryActionDatabasePort(
    ArchiveDictionaryEntryDatabasePort,
    DeleteDictionaryEntryDatabasePort,
    VerifyDictionaryEntriesDatabasePort,
    Protocol,
):
    pass


class AdminDictionaryActionService:
    def __init__(self, db: AdminDictionaryActionDatabasePort, time_service: TimeService) -> None:
        self.db = db
        self.time_service = time_service

    def archive_entry(self, *, actor: dict, entry_id: int) -> dict[str, str]:
        return archive_dictionary_entry(self.db, self.time_service, actor=actor, entry_id=entry_id)

    def delete_entry(self, *, actor: dict, entry_id: int) -> dict[str, str]:
        return delete_dictionary_entry(self.db, actor=actor, entry_id=entry_id)

    def verify_entries(self, *, actor: dict, entry_ids: list[int]) -> dict:
        return verify_dictionary_entries(self.db, self.time_service, actor=actor, entry_ids=entry_ids)
