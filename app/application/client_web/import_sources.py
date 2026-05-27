from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.application.client_web.import_errors import (
    ClientWebImportProviderUnavailableError,
    ClientWebImportValidationError,
)
from app.domain.user_import.constants import MAX_IMPORT_TEXT_BYTES
from app.validators.google_docs import build_google_doc_export_url, extract_google_doc_id

GoogleDocTextFetcher = Callable[[str], str]


def read_client_web_import_source(
    *,
    source_url: str | None,
    text_content: str | None,
    file_name: str | None,
    google_doc_text_fetcher: GoogleDocTextFetcher | None = None,
) -> dict[str, str]:
    normalized_url = (source_url or "").strip()
    normalized_text = text_content or ""
    has_url = bool(normalized_url)
    has_text = bool(normalized_text.strip())
    if has_url == has_text:
        raise ClientWebImportValidationError("Provide exactly one import source: Google Doc URL or TXT file")
    if has_url:
        if google_doc_text_fetcher is None:
            raise ClientWebImportProviderUnavailableError("Google Doc import provider is unavailable")
        doc_id = extract_downloadable_google_doc_id(normalized_url)
        text = fetch_downloadable_google_doc_text(
            build_google_doc_export_url(doc_id),
            google_doc_text_fetcher,
        )
        return {
            "source_type": "client_web_google_doc",
            "source_identifier": doc_id,
            "text": text,
        }
    safe_name = validate_txt_file_name(file_name)
    validate_text_size(normalized_text)
    return {
        "source_type": "client_web_txt",
        "source_identifier": safe_name,
        "text": normalized_text,
    }


def extract_downloadable_google_doc_id(source_url: str) -> str:
    try:
        return extract_google_doc_id(source_url)
    except ValueError as error:
        raise ClientWebImportValidationError(str(error)) from error


def fetch_downloadable_google_doc_text(export_url: str, google_doc_text_fetcher: GoogleDocTextFetcher) -> str:
    try:
        return google_doc_text_fetcher(export_url)
    except ValueError as error:
        raise ClientWebImportValidationError(str(error)) from error
    except RuntimeError as error:
        raise ClientWebImportProviderUnavailableError(str(error)) from error


def validate_txt_file_name(file_name: str | None) -> str:
    candidate = (file_name or "import.txt").strip()
    if len(candidate) > 160:
        raise ClientWebImportValidationError("TXT file name is too long")
    if not candidate.lower().endswith(".txt"):
        raise ClientWebImportValidationError("Only .txt import files are supported")
    return Path(candidate).name or "import.txt"


def validate_text_size(text: str) -> None:
    size = len(text.encode("utf-8"))
    if size > MAX_IMPORT_TEXT_BYTES:
        raise ClientWebImportValidationError("TXT import file is too large")
