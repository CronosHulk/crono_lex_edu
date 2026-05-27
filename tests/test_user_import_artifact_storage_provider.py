from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.storage.user_import_artifacts import (
    FileSystemUserImportArtifactStorageProvider,
)


def test_filesystem_provider_writes_json_snapshot_under_configured_storage_dir(tmp_path) -> None:
    calls: list[tuple[Path, dict[str, Any]]] = []
    current_time = datetime(2026, 5, 26, 10, 15, 30)

    provider = FileSystemUserImportArtifactStorageProvider(
        tmp_path,
        build_import_storage_path=lambda telegram_user_id, created_at: Path(
            f"telegram_{telegram_user_id}_voc_import_{created_at:%Y%m%d%H%M%S}.json"
        ),
        write_json_atomic=lambda path, payload: calls.append((path, payload)),
    )

    storage_path = provider.write_json_snapshot(
        123,
        current_time,
        {"items": [{"lookup_word": "carry on"}]},
    )

    expected_path = tmp_path / "telegram_123_voc_import_20260526101530.json"
    assert storage_path == str(expected_path)
    assert calls == [(expected_path, {"items": [{"lookup_word": "carry on"}]})]


def test_filesystem_provider_writes_text_sibling_with_legacy_filename(tmp_path) -> None:
    calls: list[tuple[Path, str]] = []
    provider = FileSystemUserImportArtifactStorageProvider(
        tmp_path,
        write_text_atomic=lambda path, content: calls.append((path, content)),
    )

    artifact = provider.write_text_sibling(
        str(tmp_path / "source.json"),
        "_queued_words.txt",
        "take over\ncarry on",
    )

    expected_path = tmp_path / "source_queued_words.txt"
    assert artifact.path == str(expected_path)
    assert artifact.filename == "source_queued_words.txt"
    assert calls == [(expected_path, "take over\ncarry on")]


def test_filesystem_provider_writes_provider_payload_with_legacy_path(tmp_path) -> None:
    calls: list[tuple[Path, dict[str, Any]]] = []
    created_at = datetime(2026, 4, 23, 8, 9, 10)
    provider = FileSystemUserImportArtifactStorageProvider(
        tmp_path,
        write_json_atomic=lambda path, payload: calls.append((path, payload)),
    )

    storage_path = provider.write_provider_payload(
        telegram_user_id=123,
        lookup_word="carry on",
        provider="fake_details",
        created_at=created_at,
        payload={"provider": "fake_details"},
    )

    expected_path = (
        tmp_path
        / "payloads"
        / "fake_details"
        / "20260423080910_123_carry_on.json"
    )
    assert storage_path == str(expected_path)
    assert calls == [(expected_path, {"provider": "fake_details"})]
