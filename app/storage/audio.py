from __future__ import annotations

import os
import shutil
import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import BinaryIO, Protocol


class AudioStorageProvider(Protocol):
    def exists(self, audio_path: str | Path | None) -> bool: ...

    def open_binary(self, audio_path: str | Path | None) -> BinaryIO: ...

    def write_bytes_atomic(self, audio_path: str | Path, payload: bytes) -> str: ...

    def copy(self, source_audio_path: str | Path, target_audio_path: str | Path) -> str: ...

    def delete_if_under_roots(
        self,
        audio_path: str | Path | None,
        audio_roots: Iterable[Path | str],
    ) -> bool: ...


class FileSystemAudioStorageProvider:
    def __init__(self, project_root: str | Path | None = None) -> None:
        self._project_root = Path(project_root).resolve() if project_root is not None else None

    def resolve_local_path(self, audio_path: str | Path | None) -> Path | None:
        return self._resolve_relative_audio_path(audio_path)

    def exists(self, audio_path: str | Path | None) -> bool:
        path = self._resolve_relative_audio_path(audio_path)
        return path is not None and path.exists()

    def open_binary(self, audio_path: str | Path | None) -> BinaryIO:
        path = self._resolve_relative_audio_path(audio_path)
        if path is None or not path.is_file():
            raise FileNotFoundError("Audio not found")
        return path.open("rb")

    def write_bytes_atomic(self, audio_path: str | Path, payload: bytes) -> str:
        target_path = self._require_relative_audio_path(audio_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target_path.with_suffix(target_path.suffix + f".{os.getpid()}.{uuid.uuid4().hex}.tmp")
        temp_path.write_bytes(payload)
        temp_path.replace(target_path)
        return self._return_audio_path(audio_path)

    def copy(self, source_audio_path: str | Path, target_audio_path: str | Path) -> str:
        source_path = self._require_relative_audio_path(source_audio_path)
        target_path = self._require_relative_audio_path(target_audio_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(source_path), str(target_path))
        return self._return_audio_path(target_audio_path)

    def delete_if_under_roots(
        self,
        audio_path: str | Path | None,
        audio_roots: Iterable[Path | str],
    ) -> bool:
        target = self._resolve_delete_path(audio_path)
        if target is None or not self._is_under_any_root(target, audio_roots):
            return False
        try:
            target.unlink()
        except FileNotFoundError:
            return False
        return True

    def _root(self) -> Path:
        return self._project_root or Path.cwd().resolve()

    def _resolve_relative_audio_path(self, audio_path: str | Path | None) -> Path | None:
        if audio_path is None:
            return None
        raw_audio_path = str(audio_path).strip()
        if not raw_audio_path or raw_audio_path == ".":
            return None
        candidate = Path(raw_audio_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            return None
        root = self._root()
        resolved = (root / candidate).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            return None
        return resolved

    def _require_relative_audio_path(self, audio_path: str | Path) -> Path:
        resolved = self._resolve_relative_audio_path(audio_path)
        if resolved is None:
            raise ValueError("Invalid audio path")
        return resolved

    def _resolve_delete_path(self, audio_path: str | Path | None) -> Path | None:
        if audio_path is None:
            return None
        raw_audio_path = str(audio_path).strip()
        if not raw_audio_path:
            return None
        path = Path(raw_audio_path)
        if path.is_absolute():
            return path.resolve()
        return (self._root() / path).resolve()

    def _is_under_any_root(self, target: Path, audio_roots: Iterable[Path | str]) -> bool:
        for root in audio_roots:
            resolved_root = self._resolve_delete_path(root)
            if resolved_root is None:
                continue
            try:
                target.relative_to(resolved_root)
                return True
            except ValueError:
                continue
        return False

    def _return_audio_path(self, audio_path: str | Path) -> str:
        if isinstance(audio_path, Path):
            return audio_path.as_posix().strip()
        return str(audio_path).strip()


def filesystem_audio_storage_provider(
    project_root: str | Path | None = None,
) -> FileSystemAudioStorageProvider:
    return FileSystemAudioStorageProvider(project_root=project_root)
