from __future__ import annotations


def normalize_username(value: str) -> str:
    return value.strip().lstrip("@").lower()
