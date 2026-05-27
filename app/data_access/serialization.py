from __future__ import annotations

from typing import Any


def normalize_examples_json(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    examples: list[str] = []
    for item in value:
        if isinstance(item, str):
            candidate = item.strip()
        elif isinstance(item, dict):
            candidate = str(item.get("text", "")).strip()
        else:
            candidate = str(item).strip()
        if candidate:
            examples.append(candidate)
    return examples
