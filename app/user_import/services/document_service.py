from __future__ import annotations

from typing import Any, Protocol

from app.contracts import DocumentAttachmentModel
from app.i18n import translate
from app.storage.user_import_artifacts import UserImportArtifactStorageProvider
from app.user_import.services.helpers import (
    normalize_import_document_lines,
    normalize_nonempty_strings,
)


class UserImportDocumentDictionaryLookupPort(Protocol):
    def find_by_word(self, word: str) -> dict[str, Any] | None: ...


class UserImportDocumentDatabasePort(Protocol):
    @property
    def dictionary_lookup(self) -> UserImportDocumentDictionaryLookupPort: ...


class UserImportDocumentService:
    def __init__(
        self,
        db: UserImportDocumentDatabasePort,
        *,
        artifact_storage_provider: UserImportArtifactStorageProvider,
    ) -> None:
        self.db = db
        self.artifact_storage_provider = artifact_storage_provider

    def build_queued_document(
        self,
        *,
        locale: str,
        job: dict[str, Any],
        items: list[dict[str, Any]],
        intake_snapshot: dict[str, Any] | None = None,
    ) -> DocumentAttachmentModel | None:
        intake_snapshot = intake_snapshot or {}
        queued_lookup_words = normalize_nonempty_strings(intake_snapshot.get("queued_lookup_words")) or [
            str(item["lookup_word"]) for item in items if item["status"] == "queued_for_attributes"
        ]
        queued_lookup_words = normalize_import_document_lines(queued_lookup_words)
        if not queued_lookup_words:
            return None
        queued_ref = self.artifact_storage_provider.write_text_sibling(
            str(job["storage_path"]),
            "_queued_words.txt",
            "\n".join(queued_lookup_words),
        )
        return DocumentAttachmentModel(
            path=queued_ref.path,
            filename=queued_ref.filename,
            caption=translate(locale, "import_words_summary_queued_document_caption"),
        )

    def build_existing_document(
        self,
        *,
        locale: str,
        job: dict[str, Any],
        items: list[dict[str, Any]],
        intake_snapshot: dict[str, Any] | None = None,
    ) -> DocumentAttachmentModel | None:
        intake_snapshot = intake_snapshot or {}
        existing_lookup_words = normalize_nonempty_strings(intake_snapshot.get("existing_lookup_words")) or [
            str(item["lookup_word"]) for item in items if item["status"] == "found_existing"
        ]
        existing_lookup_words = normalize_import_document_lines(existing_lookup_words)
        if not existing_lookup_words:
            return None
        existing_lines = [
            f"{word} - {self.resolve_existing_translation(locale, word)}"
            for word in existing_lookup_words
        ]
        existing_ref = self.artifact_storage_provider.write_text_sibling(
            str(job["storage_path"]),
            "_existing_words.txt",
            "\n".join(existing_lines),
        )
        return DocumentAttachmentModel(
            path=existing_ref.path,
            filename=existing_ref.filename,
            caption=translate(locale, "import_words_summary_existing_document_caption"),
        )

    def build_summary_documents(
        self,
        *,
        locale: str,
        job: dict[str, Any],
        items: list[dict[str, Any]],
        intake_snapshot: dict[str, Any] | None = None,
    ) -> list[DocumentAttachmentModel]:
        documents: list[DocumentAttachmentModel] = []
        queued_document = self.build_queued_document(
            locale=locale,
            job=job,
            items=items,
            intake_snapshot=intake_snapshot,
        )
        if queued_document is not None:
            documents.append(queued_document)
        existing_document = self.build_existing_document(
            locale=locale,
            job=job,
            items=items,
            intake_snapshot=intake_snapshot,
        )
        if existing_document is not None:
            documents.append(existing_document)
        return documents

    def build_published_document(
        self,
        *,
        locale: str,
        job: dict[str, Any],
        items: list[dict[str, Any]],
    ) -> DocumentAttachmentModel | None:
        published_items = [item for item in items if item["status"] == "imported"]
        if not published_items:
            return None
        published_lines = normalize_import_document_lines(
            [
                f"{item['lookup_word']} - {self.resolve_existing_translation(locale, str(item['lookup_word']))}"
                for item in published_items
            ]
        )
        if not published_lines:
            return None
        published_ref = self.artifact_storage_provider.write_text_sibling(
            str(job["storage_path"]),
            "_published_words.txt",
            "\n".join(published_lines),
        )
        return DocumentAttachmentModel(
            path=published_ref.path,
            filename=published_ref.filename,
            caption=translate(locale, "import_words_publish_summary_document_caption"),
        )

    def resolve_existing_translation(self, locale: str, lookup_word: str) -> str:
        entry = self.db.dictionary_lookup.find_by_word(lookup_word)
        if entry is None:
            return "\u2014"
        translation = str(entry.get("translation_uk") or "").strip() if locale == "uk" else str(entry.get("translation_uk") or "").strip()
        return translation or "\u2014"
