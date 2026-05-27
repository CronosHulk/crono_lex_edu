from __future__ import annotations

from pathlib import Path
from typing import Any

from app.helpers.user_import_storage import slugify


def build_pos_audio_dir(audio_root: Path | str, entry: dict[str, Any]) -> Path:
    return Path(audio_root) / _pos_directory(entry)


def build_pos_audio_path(audio_root: Path | str, entry: dict[str, Any]) -> str:
    word = str(entry.get("word") or entry.get("normalized_word") or entry.get("id") or "word")
    return str(build_pos_audio_dir(audio_root, entry) / f"{slugify(word)}.mp3")


def _pos_directory(entry: dict[str, Any]) -> str:
    value = entry.get("part_of_speech") or entry.get("entry_type") or "unknown"
    return slugify(str(value)).replace("-", "_") or "unknown"
