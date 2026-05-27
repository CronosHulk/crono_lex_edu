from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from app.storage.audio import AudioStorageProvider


def delete_audio_file_if_under_roots(
    audio_path: str | None,
    audio_roots: Iterable[Path | str],
    *,
    storage_provider: AudioStorageProvider,
) -> bool:
    return storage_provider.delete_if_under_roots(audio_path, audio_roots)
