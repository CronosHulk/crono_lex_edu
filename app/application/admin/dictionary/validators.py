from __future__ import annotations

from typing import Any

from app.word_validation import has_non_ascii_characters


class AdminExamplesValidationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def normalize_examples_json(
    value: Any,
    *,
    max_count: int,
    max_item_length: int = 1000,
    ascii_only: bool = False,
) -> list[str]:
    if isinstance(value, str):
        examples = [line.strip() for line in value.splitlines()]
    elif isinstance(value, list):
        examples = [str(item).strip() for item in value]
    else:
        raise AdminExamplesValidationError("examples_json must be a list or multiline string")
    examples = [item for item in examples if item]
    if len(examples) > max_count:
        raise AdminExamplesValidationError("examples_json contains too many items")
    if any(len(item) > max_item_length for item in examples):
        raise AdminExamplesValidationError("examples_json item is too long")
    if ascii_only and any(has_non_ascii_characters(item) for item in examples):
        raise AdminExamplesValidationError("examples_json items must contain only ASCII characters")
    return examples
