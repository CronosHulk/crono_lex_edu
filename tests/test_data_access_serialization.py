from __future__ import annotations

from app.data_access.serialization import normalize_examples_json


def test_normalize_examples_json_returns_empty_for_non_list() -> None:
    assert normalize_examples_json("one\ntwo") == []


def test_normalize_examples_json_extracts_text_from_dict_items() -> None:
    assert normalize_examples_json([{"text": " One. "}, {"missing": "ignored"}]) == ["One."]


def test_normalize_examples_json_stringifies_other_items() -> None:
    assert normalize_examples_json([123, " Two. "]) == ["123", "Two."]
