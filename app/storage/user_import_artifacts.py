from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from app.helpers.user_import_storage import (
    build_import_storage_path,
    build_source_payload_path,
    write_json_atomic,
)


@dataclass(frozen=True, slots=True)
class UserImportArtifactRef:
    path: str
    filename: str


class UserImportArtifactStorageProvider(Protocol):
    def write_json_snapshot(
        self,
        telegram_user_id: int,
        current_time: datetime,
        payload: dict[str, Any],
    ) -> str: ...

    def write_text_sibling(
        self,
        base_path: str,
        suffix: str,
        content: str,
    ) -> UserImportArtifactRef: ...

    def write_provider_payload(
        self,
        telegram_user_id: int,
        lookup_word: str,
        provider: str,
        created_at: datetime,
        payload: Any,
    ) -> str: ...


class FileSystemUserImportArtifactStorageProvider:
    def __init__(
        self,
        storage_dir: str | Path,
        *,
        build_import_storage_path: Callable[[int, datetime], Path] = build_import_storage_path,
        write_json_atomic: Callable[[Path, Any], None] = write_json_atomic,
        write_text_atomic: Callable[[Path, str], None] | None = None,
    ) -> None:
        self.storage_dir = Path(storage_dir)
        self.build_import_storage_path = build_import_storage_path
        self.write_json_atomic = write_json_atomic
        self.write_text_atomic = write_text_atomic or _write_text_atomic

    def write_json_snapshot(
        self,
        telegram_user_id: int,
        current_time: datetime,
        payload: dict[str, Any],
    ) -> str:
        storage_path = self.storage_dir / self.build_import_storage_path(
            telegram_user_id,
            current_time,
        ).name
        self.write_json_atomic(storage_path, payload)
        return str(storage_path)

    def write_text_sibling(
        self,
        base_path: str,
        suffix: str,
        content: str,
    ) -> UserImportArtifactRef:
        base = Path(base_path)
        target = base.with_name(f"{base.stem}{suffix}")
        self.write_text_atomic(target, content)
        return UserImportArtifactRef(path=str(target), filename=target.name)

    def write_provider_payload(
        self,
        telegram_user_id: int,
        lookup_word: str,
        provider: str,
        created_at: datetime,
        payload: Any,
    ) -> str:
        relative_path = Path("payloads") / provider / build_source_payload_path(
            telegram_user_id=telegram_user_id,
            lookup_word=lookup_word,
            provider=provider,
            created_at=created_at,
        ).name
        absolute_path = self.storage_dir / relative_path
        self.write_json_atomic(absolute_path, payload)
        return str(absolute_path)


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)
