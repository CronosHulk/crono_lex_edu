from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

from app.domain.user_import.text_parser import normalize_import_text


@dataclass(frozen=True)
class ScopedGoogleDocParseResult:
    parsed_words: list[Any]
    invalid_fragments: list[str]
    word_line_numbers: list[int]
    lines: list[str]
    start_line: int
    skipped_lookup_words: list[str] = field(default_factory=list)
    is_truncated: bool = False

    @property
    def total_line_count(self) -> int:
        return len(self.lines)

    @property
    def parse_result(self) -> Any:
        return SimpleNamespace(parsed_words=self.parsed_words, invalid_fragments=self.invalid_fragments)


def parse_google_doc_since_progress(
    raw_text: str,
    progress: dict[str, Any] | None,
    parse_user_vocabulary_text_result: Callable[[str], Any],
    *,
    max_parsed_words: int | None = None,
    skip_lookup_words: set[str] | None = None,
) -> ScopedGoogleDocParseResult:
    lines = google_doc_lines(raw_text)
    start_index = start_index_from_progress(lines, progress)
    parsed_words: list[Any] = []
    word_line_numbers: list[int] = []
    invalid_fragments: list[str] = []
    seen_lookup_words: set[str] = set()
    seen_invalid: set[str] = set()
    skipped_lookup_words: list[str] = []
    normalized_skip_lookup_words = {
        normalized
        for normalized in (_normalize_lookup_word(value) for value in (skip_lookup_words or set()))
        if normalized
    }
    for index, line in enumerate(lines[start_index:], start=start_index):
        result = parse_user_vocabulary_text_result(line)
        for fragment in result.invalid_fragments:
            if fragment in seen_invalid:
                continue
            seen_invalid.add(fragment)
            invalid_fragments.append(fragment)
        for item in result.parsed_words:
            lookup_word = str(getattr(item, "lookup_word", "") or "").strip()
            normalized_lookup_word = _normalize_lookup_word(lookup_word)
            if not lookup_word or normalized_lookup_word in seen_lookup_words:
                continue
            seen_lookup_words.add(normalized_lookup_word)
            if normalized_lookup_word in normalized_skip_lookup_words:
                skipped_lookup_words.append(lookup_word)
                continue
            parsed_words.append(item)
            word_line_numbers.append(index + 1)
            if max_parsed_words is not None and len(parsed_words) >= max(int(max_parsed_words), 1):
                return ScopedGoogleDocParseResult(
                    parsed_words=parsed_words,
                    invalid_fragments=invalid_fragments,
                    word_line_numbers=word_line_numbers,
                    lines=lines,
                    start_line=start_index + 1,
                    skipped_lookup_words=skipped_lookup_words,
                    is_truncated=True,
                )
    return ScopedGoogleDocParseResult(
        parsed_words=parsed_words,
        invalid_fragments=invalid_fragments,
        word_line_numbers=word_line_numbers,
        lines=lines,
        start_line=start_index + 1,
        skipped_lookup_words=skipped_lookup_words,
    )


def google_doc_lines(raw_text: str) -> list[str]:
    normalized_text = normalize_import_text(raw_text)
    return normalized_text.split("\n") if normalized_text else []


def start_index_from_progress(lines: list[str], progress: dict[str, Any] | None) -> int:
    if not progress:
        return 0
    saved_hash = str(progress.get("last_processed_line_hash") or "")
    if saved_hash:
        for index, line in enumerate(lines):
            if line_hash(line) == saved_hash:
                return min(index + 1, len(lines))
    saved_line = int(progress.get("last_processed_line") or 0)
    return min(max(saved_line, 0), len(lines))


def progress_checkpoint_for_scope(
    scope: ScopedGoogleDocParseResult,
    *,
    existing_lookup_words: set[str],
    max_new_words: int,
) -> dict[str, Any]:
    new_words_seen = 0
    max_new_words = max(int(max_new_words), 1)
    normalized_existing_lookup_words = {
        normalized
        for normalized in (_normalize_lookup_word(value) for value in existing_lookup_words)
        if normalized
    }
    new_words_total = sum(
        1
        for item in scope.parsed_words
        if _normalize_lookup_word(getattr(item, "lookup_word", "")) not in normalized_existing_lookup_words
    )
    if new_words_total <= max_new_words and not scope.is_truncated:
        return progress_checkpoint_for_line(scope.lines, scope.total_line_count, last_lookup_word=None)

    last_processed_line = scope.start_line - 1
    last_lookup_word = None
    for item, line_number in zip(scope.parsed_words, scope.word_line_numbers, strict=True):
        lookup_word = str(getattr(item, "lookup_word", "") or "").strip()
        last_processed_line = line_number
        last_lookup_word = lookup_word or None
        if _normalize_lookup_word(lookup_word) not in normalized_existing_lookup_words:
            new_words_seen += 1
        if new_words_seen >= max_new_words:
            break
    return progress_checkpoint_for_line(scope.lines, last_processed_line, last_lookup_word=last_lookup_word)


def progress_checkpoint_for_line(
    lines: list[str],
    line_number: int,
    *,
    last_lookup_word: str | None,
) -> dict[str, Any]:
    normalized_line_number = min(max(int(line_number), 0), len(lines))
    line = lines[normalized_line_number - 1] if normalized_line_number > 0 else ""
    return {
        "last_processed_line": normalized_line_number,
        "last_processed_line_hash": line_hash(line) if line else None,
        "last_processed_lookup_word": last_lookup_word,
    }


def line_hash(line: str) -> str:
    return hashlib.sha256(line.strip().encode("utf-8")).hexdigest()


def _normalize_lookup_word(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())
