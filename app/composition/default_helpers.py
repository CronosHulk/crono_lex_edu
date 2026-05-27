from __future__ import annotations

import sys
from typing import Any

from app.composition.provider_helpers import (
    ensure_user_import_embedding,
    fetch_google_doc_text,
    sync_due_provider_pricing_snapshots,
)
from app.composition.user_import_provider_adapters import (
    build_word_audio_provider,
    build_word_details_provider,
    build_word_validation_provider,
)
from app.domain.user_import.text_parser import parse_user_vocabulary_text_result
from app.helpers.external_error_text import (
    mask_provider_error_for_user,
    sanitize_external_error_text,
)
from app.helpers.user_import_storage import (
    build_import_snapshot,
    build_import_storage_path,
    write_json_atomic,
)
from app.user_import.services.helpers import build_invalid_import_notice
from app.user_import.services.pending_import_enrichment import resolve_pending_import_word
from app.validators.google_docs import (
    build_google_doc_export_url,
    extract_google_doc_id,
    mask_google_doc_url,
)

_DEFAULT_HELPERS = {
    "build_google_doc_export_url": build_google_doc_export_url,
    "build_import_snapshot": build_import_snapshot,
    "build_import_storage_path": build_import_storage_path,
    "build_invalid_import_notice": build_invalid_import_notice,
    "build_word_audio_provider": build_word_audio_provider,
    "build_word_details_provider": build_word_details_provider,
    "build_word_validation_provider": build_word_validation_provider,
    "ensure_user_import_embedding": ensure_user_import_embedding,
    "extract_google_doc_id": extract_google_doc_id,
    "fetch_google_doc_text": fetch_google_doc_text,
    "mask_google_doc_url": mask_google_doc_url,
    "mask_provider_error_for_user": mask_provider_error_for_user,
    "parse_user_vocabulary_text_result": parse_user_vocabulary_text_result,
    "resolve_pending_import_word": resolve_pending_import_word,
    "sanitize_external_error_text": sanitize_external_error_text,
    "sync_due_provider_pricing_snapshots": sync_due_provider_pricing_snapshots,
    "write_json_atomic": write_json_atomic,
}

_MISSING = object()


def default_helper_resolver(name: str) -> Any:
    if name not in _DEFAULT_HELPERS:
        raise KeyError(name)
    root_module = sys.modules.get("app.composition.root")
    helper = globals()[name]
    root_helper = vars(root_module).get(name, _MISSING) if root_module is not None else _MISSING
    if root_helper is not _MISSING and root_helper is not helper:
        return root_helper
    return helper
