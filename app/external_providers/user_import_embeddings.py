from __future__ import annotations

from typing import Any

from app.domain.provider_settings import (
    DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL as DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL,
)
from app.helpers.external_error_text import sanitize_external_error_text


def ensure_user_import_embedding(
    *,
    word: str,
    translation_uk: str | None,
    part_of_speech: str | None,
    examples_json: list[str],
    model_name: str = DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL,
    device: str = "cpu",
) -> tuple[list[float] | None, dict[str, Any], str | None]:
    try:
        from app.external_providers.embeddings.local_sentence_transformers import build_embedding

        embedding = build_embedding(
            word=word,
            translation_uk=translation_uk,
            part_of_speech=part_of_speech,
            examples_json=examples_json,
            model_name=model_name,
            device=device,
        )
        return (
            embedding,
            {"status": "ok", "model": model_name, "device": device},
            None,
        )
    except Exception as error:
        embedding_error = sanitize_external_error_text(str(error)) or "Embedding build failed"
        return None, {"status": "error", "model": model_name, "device": device, "error": embedding_error}, embedding_error
