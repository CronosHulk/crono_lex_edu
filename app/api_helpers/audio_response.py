from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO
from urllib.parse import quote

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from app.storage.audio import AudioStorageProvider


def build_audio_response(
    audio_path: str | None,
    storage_provider: AudioStorageProvider,
) -> StreamingResponse:
    if not audio_path:
        raise HTTPException(status_code=404, detail="Audio not found")
    try:
        audio_file = storage_provider.open_binary(audio_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Audio not found")
    filename = _audio_response_filename(audio_path)
    return StreamingResponse(
        _iter_binary_file(audio_file),
        media_type="audio/mpeg",
        headers={"Content-Disposition": _content_disposition(filename)},
    )


def _iter_binary_file(audio_file: BinaryIO) -> Iterator[bytes]:
    try:
        while chunk := audio_file.read(64 * 1024):
            yield chunk
    finally:
        audio_file.close()


def _audio_response_filename(audio_path: str) -> str:
    return Path(audio_path).name or "audio.mp3"


def _content_disposition(filename: str) -> str:
    return f"attachment; filename*=utf-8''{quote(filename)}"
