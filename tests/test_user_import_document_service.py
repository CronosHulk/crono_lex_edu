from __future__ import annotations

from typing import Any

from app.storage.user_import_artifacts import FileSystemUserImportArtifactStorageProvider
from app.user_import.services.document_service import UserImportDocumentService


class FakeDocumentDb:
    def __init__(self) -> None:
        self.dictionary: dict[str, dict[str, Any]] = {}

    @property
    def dictionary_lookup(self) -> FakeDocumentDb:
        return self

    def find_by_word(self, lookup_word: str) -> dict[str, Any] | None:
        return self.dictionary.get(lookup_word)


def build_job(tmp_path) -> dict[str, Any]:
    return {"id": 7, "storage_path": str(tmp_path / "source.txt")}


def build_service(tmp_path, db: FakeDocumentDb | None = None) -> UserImportDocumentService:
    return UserImportDocumentService(
        db or FakeDocumentDb(),
        artifact_storage_provider=FileSystemUserImportArtifactStorageProvider(tmp_path),
    )


def test_build_queued_document_prefers_intake_snapshot_and_normalizes_lines(tmp_path) -> None:
    service = build_service(tmp_path)

    document = service.build_queued_document(
        locale="uk",
        job=build_job(tmp_path),
        items=[{"lookup_word": "fallback", "status": "queued_for_attributes"}],
        intake_snapshot={"queued_lookup_words": ["  take   over  ", "", " carry\t on "]},
    )

    assert document is not None
    assert document.filename == "source_queued_words.txt"
    assert (tmp_path / document.filename).read_text(encoding="utf-8") == "take over\ncarry on"


def test_build_queued_document_falls_back_to_items(tmp_path) -> None:
    service = build_service(tmp_path)

    document = service.build_queued_document(
        locale="uk",
        job=build_job(tmp_path),
        items=[
            {"lookup_word": "take over", "status": "queued_for_attributes"},
            {"lookup_word": "known", "status": "found_existing"},
        ],
        intake_snapshot={},
    )

    assert document is not None
    assert (tmp_path / document.filename).read_text(encoding="utf-8") == "take over"


def test_build_existing_document_writes_translation_and_missing_marker(tmp_path) -> None:
    db = FakeDocumentDb()
    db.dictionary["known"] = {"translation_uk": "знаний"}
    service = build_service(tmp_path, db)

    document = service.build_existing_document(
        locale="en",
        job=build_job(tmp_path),
        items=[
            {"lookup_word": "known", "status": "found_existing"},
            {"lookup_word": "missing", "status": "found_existing"},
        ],
    )

    assert document is not None
    assert (tmp_path / document.filename).read_text(encoding="utf-8") == "known - знаний\nmissing - —"


def test_build_summary_documents_keeps_queued_before_existing(tmp_path) -> None:
    db = FakeDocumentDb()
    db.dictionary["known"] = {"translation_uk": "знаний"}
    service = build_service(tmp_path, db)

    documents = service.build_summary_documents(
        locale="uk",
        job=build_job(tmp_path),
        items=[
            {"lookup_word": "new", "status": "queued_for_attributes"},
            {"lookup_word": "known", "status": "found_existing"},
        ],
    )

    assert [document.filename for document in documents] == [
        "source_queued_words.txt",
        "source_existing_words.txt",
    ]


def test_build_published_document_skips_empty_and_writes_imported_words(tmp_path) -> None:
    db = FakeDocumentDb()
    db.dictionary["done"] = {"translation_uk": "готово"}
    service = build_service(tmp_path, db)

    assert service.build_published_document(locale="uk", job=build_job(tmp_path), items=[]) is None

    document = service.build_published_document(
        locale="uk",
        job=build_job(tmp_path),
        items=[
            {"lookup_word": "done", "status": "imported"},
            {"lookup_word": "skip", "status": "ready_for_publish"},
        ],
    )

    assert document is not None
    assert document.filename == "source_published_words.txt"
    assert (tmp_path / document.filename).read_text(encoding="utf-8") == "done - готово"
