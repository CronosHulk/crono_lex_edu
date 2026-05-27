from __future__ import annotations

from app.domain.user_import.text_parser import parse_user_vocabulary_text_result
from app.user_import.services.google_doc_progress import (
    parse_google_doc_since_progress,
    progress_checkpoint_for_scope,
)


def test_parse_google_doc_since_progress_uses_line_hash_after_reordered_prefix() -> None:
    raw_text = "intro\nspeak\ncarry on\nwrite"
    progress = {
        "last_processed_line": 1,
        "last_processed_line_hash": "21e5205f73d9edbf72bc29b5ffcb4631cfc95e8f287c4d68e73d17ad72eb5eb3",
    }

    scope = parse_google_doc_since_progress(raw_text, progress, parse_user_vocabulary_text_result)

    assert [item.lookup_word for item in scope.parsed_words] == ["carry on", "write"]
    assert scope.word_line_numbers == [3, 4]


def test_parse_google_doc_since_progress_falls_back_to_line_number() -> None:
    raw_text = "speak\ncarry on\nwrite"
    progress = {"last_processed_line": 2, "last_processed_line_hash": "missing"}

    scope = parse_google_doc_since_progress(raw_text, progress, parse_user_vocabulary_text_result)

    assert [item.lookup_word for item in scope.parsed_words] == ["write"]
    assert scope.start_line == 3


def test_parse_google_doc_since_progress_respects_max_parsed_words() -> None:
    scope = parse_google_doc_since_progress(
        "speak\ncarry on\nwrite",
        None,
        parse_user_vocabulary_text_result,
        max_parsed_words=2,
    )

    assert [item.lookup_word for item in scope.parsed_words] == ["speak", "carry on"]
    assert scope.word_line_numbers == [1, 2]
    assert scope.is_truncated is True


def test_parse_google_doc_since_progress_skips_lookup_words_before_limit() -> None:
    scope = parse_google_doc_since_progress(
        "known\nspeak\ncarry on",
        None,
        parse_user_vocabulary_text_result,
        max_parsed_words=2,
        skip_lookup_words={"known"},
    )

    assert [item.lookup_word for item in scope.parsed_words] == ["speak", "carry on"]
    assert scope.skipped_lookup_words == ["known"]
    assert scope.word_line_numbers == [2, 3]
    assert scope.is_truncated is True


def test_progress_checkpoint_stops_at_truncated_scope_line() -> None:
    scope = parse_google_doc_since_progress(
        "speak\ncarry on\nwrite",
        None,
        parse_user_vocabulary_text_result,
        max_parsed_words=2,
    )

    checkpoint = progress_checkpoint_for_scope(scope, existing_lookup_words=set(), max_new_words=2)

    assert checkpoint["last_processed_line"] == 2
    assert checkpoint["last_processed_lookup_word"] == "carry on"


def test_progress_checkpoint_stops_at_max_new_word_line() -> None:
    scope = parse_google_doc_since_progress("known\nspeak\ncarry on\nwrite", None, parse_user_vocabulary_text_result)

    checkpoint = progress_checkpoint_for_scope(scope, existing_lookup_words={"known"}, max_new_words=2)

    assert checkpoint["last_processed_line"] == 3
    assert checkpoint["last_processed_lookup_word"] == "carry on"


def test_progress_checkpoint_normalizes_existing_lookup_words() -> None:
    scope = parse_google_doc_since_progress("Known Word\nSpeak\nCarry on", None, parse_user_vocabulary_text_result)

    checkpoint = progress_checkpoint_for_scope(scope, existing_lookup_words={"known word"}, max_new_words=1)

    assert checkpoint["last_processed_line"] == 2
    assert checkpoint["last_processed_lookup_word"] == "speak"


def test_progress_checkpoint_advances_to_end_when_all_new_words_fit() -> None:
    scope = parse_google_doc_since_progress("known\nspeak\ncarry on", None, parse_user_vocabulary_text_result)

    checkpoint = progress_checkpoint_for_scope(scope, existing_lookup_words={"known"}, max_new_words=10)

    assert checkpoint["last_processed_line"] == 3
    assert checkpoint["last_processed_lookup_word"] is None
