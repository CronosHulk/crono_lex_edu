from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.user_import.services.google_doc_progress import progress_checkpoint_for_scope


class UserImportManualBindProgressGoogleDocRepository(Protocol):
    def mark_progress(
        self,
        telegram_user_id: int,
        doc_id: str,
        *,
        current_time: datetime,
        last_processed_line: int,
        last_processed_line_hash: str | None,
        last_processed_lookup_word: str | None,
    ) -> None: ...


class UserImportManualBindProgressService:
    def __init__(self, google_docs: UserImportManualBindProgressGoogleDocRepository) -> None:
        self._google_docs = google_docs

    def mark_google_doc_progress(
        self,
        *,
        telegram_user_id: int,
        doc_id: str,
        scope: Any,
        existing_lookup_words: set[str],
        max_words_per_bind: int,
        current_time: datetime,
    ) -> None:
        checkpoint = progress_checkpoint_for_scope(
            scope,
            existing_lookup_words={normalize_lookup_word(value) for value in existing_lookup_words},
            max_new_words=max_words_per_bind,
        )
        self._google_docs.mark_progress(
            telegram_user_id,
            doc_id,
            current_time=current_time,
            last_processed_line=checkpoint["last_processed_line"],
            last_processed_line_hash=checkpoint["last_processed_line_hash"],
            last_processed_lookup_word=checkpoint["last_processed_lookup_word"],
        )


def normalize_lookup_word(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())
