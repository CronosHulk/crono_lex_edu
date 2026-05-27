from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UserImportCandidateFilterResult:
    eligible_words: list[Any]
    skipped_existing_words: list[Any]
    assigned_lookup_words: set[str]


class UserImportCandidateFilterService:
    def __init__(self, db: Any) -> None:
        self.db = db

    def filter_already_assigned_words(
        self,
        parsed_words: list[Any],
        *,
        user_uuid: str | None,
    ) -> UserImportCandidateFilterResult:
        assigned_lookup_words = self.list_assigned_lookup_words(user_uuid)
        if not assigned_lookup_words:
            return UserImportCandidateFilterResult(
                eligible_words=list(parsed_words),
                skipped_existing_words=[],
                assigned_lookup_words=set(),
            )
        eligible_words: list[Any] = []
        skipped_existing_words: list[Any] = []
        for item in parsed_words:
            lookup_word = _normalize_lookup_word(getattr(item, "lookup_word", ""))
            if lookup_word and lookup_word in assigned_lookup_words:
                skipped_existing_words.append(item)
                continue
            eligible_words.append(item)
        return UserImportCandidateFilterResult(
            eligible_words=eligible_words,
            skipped_existing_words=skipped_existing_words,
            assigned_lookup_words=assigned_lookup_words,
        )

    def list_assigned_lookup_words(self, user_uuid: str | None) -> set[str]:
        if not user_uuid:
            return set()
        user_dictionary = getattr(self.db, "user_dictionary", None)
        if user_dictionary is None or not hasattr(user_dictionary, "list_assigned_lookup_words_for_user"):
            return set()
        return {
            normalized
            for normalized in (
                _normalize_lookup_word(value)
                for value in user_dictionary.list_assigned_lookup_words_for_user(user_uuid)
            )
            if normalized
        }


def _normalize_lookup_word(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())
