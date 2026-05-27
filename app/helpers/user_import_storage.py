from __future__ import annotations

import json
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.domain.user_import.text_parser import ParsedImportWord

DEFAULT_IMPORT_STORAGE_DIR = Path("runtime/user_vocabulary_imports")


def utc_now() -> datetime:
    return datetime.now(UTC)


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + f".{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


def write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + f".{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temp_path.write_bytes(payload)
    temp_path.replace(path)


def build_import_snapshot(
    *,
    telegram_user_id: int,
    source_identifier: str,
    parsed_words: list[ParsedImportWord],
) -> dict[str, Any]:
    return {
        "telegram_user_id": telegram_user_id,
        "source_type": "google_doc",
        "source_identifier": source_identifier,
        "submitted_at": utc_now().isoformat(),
        "items": [
            {
                "raw_value": item.raw_value,
                "lookup_word": item.lookup_word,
                "translation_hint": item.translation_hint,
                "validated_lookup_word": item.validated_lookup_word,
                "effective_lookup_word": item.validated_lookup_word or item.lookup_word,
            }
            for item in parsed_words
        ],
    }


def build_import_storage_path(telegram_user_id: int, created_at: datetime | None = None) -> Path:
    timestamp = (created_at or utc_now()).strftime("%Y%m%d%H%M%S")
    return DEFAULT_IMPORT_STORAGE_DIR / f"telegram_{telegram_user_id}_voc_import_{timestamp}.json"


def build_source_payload_path(
    *,
    telegram_user_id: int,
    lookup_word: str,
    provider: str,
    created_at: datetime | None = None,
) -> Path:
    timestamp = (created_at or utc_now()).strftime("%Y%m%d%H%M%S")
    safe_word = re.sub(r"[^a-z0-9_-]+", "_", lookup_word.lower()).strip("_") or "word"
    return DEFAULT_IMPORT_STORAGE_DIR / "payloads" / provider / f"{timestamp}_{telegram_user_id}_{safe_word}.json"


def slugify(value: str) -> str:
    lowered = value.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered)
    return slug.strip("-") or "word"


def build_user_import_audio_relative_path(audio_dir: Path, word: str) -> str:
    slug = slugify(word)
    return str(audio_dir / f"{slug}.mp3")
