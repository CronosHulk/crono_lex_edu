from __future__ import annotations

import json
import os

from app.composition.provider_helpers import (
    ensure_user_import_embedding,
)
from app.domain.provider_settings import (
    DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL,
)


def run_embedding_smoke() -> dict[str, object]:
    model_name = os.getenv("APP__USER_IMPORT_EMBEDDINGS_MODEL", DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL)
    device = os.getenv("APP__USER_IMPORT_EMBEDDINGS_DEVICE", "cpu")
    embedding, provider_status, error_text = ensure_user_import_embedding(
        word="carry on",
        translation_uk="продовжувати",
        part_of_speech="phrasal verb",
        examples_json=["Carry on with the deployment."],
        model_name=model_name,
        device=device,
    )
    if embedding is None:
        raise RuntimeError(error_text or "Embedding smoke-check failed")
    return {
        "status": "ok",
        "model": model_name,
        "device": device,
        "embedding_dimensions": len(embedding),
        "provider_status": provider_status,
    }


def main() -> None:
    print(json.dumps(run_embedding_smoke(), ensure_ascii=False))


if __name__ == "__main__":
    main()
