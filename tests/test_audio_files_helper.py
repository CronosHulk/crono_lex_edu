from __future__ import annotations

from pathlib import Path

from app.helpers.audio_files import delete_audio_file_if_under_roots
from app.storage.audio import FileSystemAudioStorageProvider


class FakeAudioStorageProvider:
    def __init__(self) -> None:
        self.delete_calls: list[tuple[str | None, list[Path | str]]] = []

    def delete_if_under_roots(self, audio_path: str | None, audio_roots) -> bool:
        self.delete_calls.append((audio_path, list(audio_roots)))
        return True


def test_delete_audio_file_if_under_roots_delegates_to_storage_provider() -> None:
    provider = FakeAudioStorageProvider()
    audio_roots = [Path("word_base/base")]

    assert (
        delete_audio_file_if_under_roots(
            "word_base/base/noun/cord.mp3",
            audio_roots,
            storage_provider=provider,
        )
        is True
    )
    assert provider.delete_calls == [("word_base/base/noun/cord.mp3", audio_roots)]


def test_delete_audio_file_if_under_roots_deletes_allowed_relative_path(tmp_path: Path) -> None:
    audio_root = tmp_path / "word_base" / "base"
    audio_file = audio_root / "noun" / "cord.mp3"
    audio_file.parent.mkdir(parents=True)
    audio_file.write_bytes(b"audio")
    provider = FileSystemAudioStorageProvider(project_root=tmp_path)

    assert (
        delete_audio_file_if_under_roots(
            "word_base/base/noun/cord.mp3",
            [audio_root],
            storage_provider=provider,
        )
        is True
    )
    assert not audio_file.exists()


def test_delete_audio_file_if_under_roots_rejects_paths_outside_allowed_roots(tmp_path: Path) -> None:
    allowed_root = tmp_path / "word_base" / "base"
    other_root = tmp_path / "other"
    audio_file = other_root / "cord.mp3"
    audio_file.parent.mkdir(parents=True)
    audio_file.write_bytes(b"audio")
    provider = FileSystemAudioStorageProvider(project_root=tmp_path)

    assert delete_audio_file_if_under_roots(str(audio_file), [allowed_root], storage_provider=provider) is False
    assert audio_file.exists()


def test_delete_audio_file_if_under_roots_ignores_missing_allowed_files(tmp_path: Path) -> None:
    audio_root = tmp_path / "word_base" / "user"
    provider = FileSystemAudioStorageProvider(project_root=tmp_path)

    assert (
        delete_audio_file_if_under_roots(
            str(audio_root / "noun" / "missing.mp3"),
            [audio_root],
            storage_provider=provider,
        )
        is False
    )
