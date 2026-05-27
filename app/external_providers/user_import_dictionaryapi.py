from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx


def dedupe_texts(values: list[str], limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = " ".join(value.strip().split())
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
        if limit is not None and len(result) >= limit:
            break
    return result


def dictionaryapi_lookup(client: httpx.Client, word: str) -> Any:
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(word, safe='')}"
    response = client.get(url)
    response.raise_for_status()
    return response.json()


def dictionaryapi_extract(payload: Any) -> tuple[str | None, str | None, str | None, list[str]]:
    if not isinstance(payload, list) or not payload:
        return None, None, None, []
    first_entry = payload[0]
    if not isinstance(first_entry, dict):
        return None, None, None, []

    part_of_speech: str | None = None
    phonetic_us: str | None = None
    audio_path: str | None = None
    for phonetic in first_entry.get("phonetics", []):
        if not isinstance(phonetic, dict):
            continue
        text = phonetic.get("text")
        audio = phonetic.get("audio")
        if phonetic_us is None and isinstance(text, str) and text.strip():
            phonetic_us = text.strip()
        if audio_path is None and isinstance(audio, str) and audio.strip():
            audio_path = audio.strip()

    examples: list[str] = []
    for meaning in first_entry.get("meanings", []):
        if not isinstance(meaning, dict):
            continue
        if part_of_speech is None and isinstance(meaning.get("partOfSpeech"), str):
            part_of_speech = meaning["partOfSpeech"].strip()
        for definition in meaning.get("definitions", []):
            if not isinstance(definition, dict):
                continue
            example = definition.get("example")
            if isinstance(example, str):
                examples.append(example)
    return part_of_speech, phonetic_us, audio_path, dedupe_texts(examples, limit=3)
