from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pytest
from fastapi import HTTPException

from app.api_helpers.audio_response import build_audio_response
from app.storage.audio import (
    FileSystemAudioStorageProvider,
    filesystem_audio_storage_provider,
)


class FakeAudioResponseStorageProvider:
    def __init__(self, *, payload: bytes = b"audio", error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def open_binary(self, audio_path: str | Path | None) -> BinaryIO:
        self.calls.append(("open_binary", str(audio_path)))
        if self.error is not None:
            raise self.error
        return BytesIO(self.payload)


async def _response_body(response) -> bytes:
    if hasattr(response, "body"):
        return response.body
    return b"".join([chunk async for chunk in response.body_iterator])


def test_filesystem_audio_storage_provider_resolves_relative_paths_under_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    provider = FileSystemAudioStorageProvider()

    assert provider.resolve_local_path("word_base/base/noun/cord.mp3") == (
        tmp_path / "word_base/base/noun/cord.mp3"
    )
    assert provider.resolve_local_path(Path("word_base/base/noun/cord.mp3")) == (
        tmp_path / "word_base/base/noun/cord.mp3"
    )


@pytest.mark.parametrize(
    "audio_path",
    [
        "",
        "   ",
        ".",
        "/tmp/cord.mp3",
        "../cord.mp3",
        "word_base/../cord.mp3",
    ],
)
def test_filesystem_audio_storage_provider_rejects_invalid_normal_resolve(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    audio_path: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    provider = FileSystemAudioStorageProvider()

    assert provider.resolve_local_path(audio_path) is None


def test_filesystem_audio_storage_provider_resolves_relative_paths_under_project_root(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    provider = FileSystemAudioStorageProvider(project_root=project_root)

    assert provider.resolve_local_path("runtime/audio/word.mp3") == (
        project_root / "runtime/audio/word.mp3"
    )


def test_filesystem_audio_storage_provider_open_binary_reads_safe_relative_path(
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "runtime/audio/word.mp3"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"audio-bytes")
    provider = FileSystemAudioStorageProvider(project_root=tmp_path)

    with provider.open_binary("runtime/audio/word.mp3") as audio_file:
        assert audio_file.read() == b"audio-bytes"


@pytest.mark.parametrize(
    "audio_path",
    [
        "",
        "   ",
        ".",
        "/tmp/cord.mp3",
        "../cord.mp3",
        "word_base/../cord.mp3",
        "runtime/audio/missing.mp3",
    ],
)
def test_filesystem_audio_storage_provider_open_binary_rejects_invalid_or_missing_paths(
    tmp_path: Path,
    audio_path: str,
) -> None:
    provider = FileSystemAudioStorageProvider(project_root=tmp_path)

    with pytest.raises(FileNotFoundError):
        provider.open_binary(audio_path)


def test_filesystem_audio_storage_provider_writes_bytes_atomically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    provider = FileSystemAudioStorageProvider()

    returned_path = provider.write_bytes_atomic("runtime/audio/nested/word.mp3", b"audio")

    assert returned_path == "runtime/audio/nested/word.mp3"
    assert (tmp_path / "runtime/audio/nested/word.mp3").read_bytes() == b"audio"
    assert list(tmp_path.rglob("*.tmp")) == []


def test_filesystem_audio_storage_provider_returns_posix_string_for_path_write_key(
    tmp_path: Path,
) -> None:
    provider = FileSystemAudioStorageProvider(project_root=tmp_path)
    audio_path = Path("runtime/audio/nested/word.mp3")

    returned_path = provider.write_bytes_atomic(audio_path, b"audio")

    assert returned_path == audio_path.as_posix()
    assert (tmp_path / audio_path).read_bytes() == b"audio"


def test_filesystem_audio_storage_provider_copy_creates_parent_and_preserves_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "word_base/user/noun/cord.mp3"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"audio")
    provider = FileSystemAudioStorageProvider()

    returned_path = provider.copy(
        "word_base/user/noun/cord.mp3",
        "word_base/base/noun/cord.mp3",
    )

    assert returned_path == "word_base/base/noun/cord.mp3"
    assert (tmp_path / "word_base/base/noun/cord.mp3").read_bytes() == b"audio"


def test_filesystem_audio_storage_provider_returns_posix_string_for_path_copy_key(
    tmp_path: Path,
) -> None:
    source_path = Path("word_base/user/noun/cord.mp3")
    target_path = Path("word_base/base/noun/cord.mp3")
    source = tmp_path / source_path
    source.parent.mkdir(parents=True)
    source.write_bytes(b"audio")
    provider = FileSystemAudioStorageProvider(project_root=tmp_path)

    returned_path = provider.copy(source_path, target_path)

    assert returned_path == target_path.as_posix()
    assert (tmp_path / target_path).read_bytes() == b"audio"


def test_filesystem_audio_storage_provider_delete_if_under_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    provider = FileSystemAudioStorageProvider()
    audio_root = tmp_path / "word_base"
    relative_file = audio_root / "base/noun/cord.mp3"
    absolute_file = audio_root / "user/noun/cord.mp3"
    outside_file = tmp_path / "outside/cord.mp3"
    for audio_file in (relative_file, absolute_file, outside_file):
        audio_file.parent.mkdir(parents=True, exist_ok=True)
        audio_file.write_bytes(b"audio")

    assert provider.delete_if_under_roots("word_base/base/noun/cord.mp3", [audio_root]) is True
    assert not relative_file.exists()
    assert provider.delete_if_under_roots(str(absolute_file), ["word_base"]) is True
    assert not absolute_file.exists()
    assert provider.delete_if_under_roots(str(outside_file), [audio_root]) is False
    assert outside_file.exists()
    assert provider.delete_if_under_roots("word_base/base/noun/missing.mp3", [audio_root]) is False


def test_default_filesystem_audio_storage_provider_tracks_current_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    default_provider = filesystem_audio_storage_provider()
    explicit_provider = filesystem_audio_storage_provider(project_root=first_root)

    monkeypatch.chdir(first_root)
    assert default_provider.resolve_local_path("audio/word.mp3") == first_root / "audio/word.mp3"

    monkeypatch.chdir(second_root)
    assert default_provider.resolve_local_path("audio/word.mp3") == second_root / "audio/word.mp3"
    assert explicit_provider.resolve_local_path("audio/word.mp3") == first_root / "audio/word.mp3"


def test_build_audio_response_uses_injected_storage_provider_open_binary() -> None:
    provider = FakeAudioResponseStorageProvider(payload=b"audio-bytes")

    response = build_audio_response("runtime/audio/word.mp3", storage_provider=provider)

    assert response.media_type == "audio/mpeg"
    assert "word.mp3" in response.headers["content-disposition"]
    assert provider.calls == [("open_binary", "runtime/audio/word.mp3")]


def test_build_audio_response_requires_storage_provider_at_runtime() -> None:
    with pytest.raises(TypeError):
        build_audio_response("runtime/audio/word.mp3")


def test_build_audio_response_streams_provider_bytes() -> None:
    provider = FakeAudioResponseStorageProvider(payload=b"audio-bytes")

    response = build_audio_response("runtime/audio/word.mp3", storage_provider=provider)

    assert asyncio.run(_response_body(response)) == b"audio-bytes"


def test_build_audio_response_404s_when_storage_cannot_open_audio() -> None:
    provider = FakeAudioResponseStorageProvider(error=FileNotFoundError("Audio not found"))

    with pytest.raises(HTTPException) as exc_info:
        build_audio_response("runtime/audio/word.mp3", storage_provider=provider)

    assert exc_info.value.status_code == 404
