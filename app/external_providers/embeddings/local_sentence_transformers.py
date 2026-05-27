from __future__ import annotations

import importlib.util
from typing import Any

MISSING_DEPENDENCY_ERROR = (
    "sentence-transformers is not installed. Run embeddings via the app-embedding-worker "
    "image built from Dockerfile.embeddings."
)


def ensure_runtime_available() -> None:
    if importlib.util.find_spec("sentence_transformers") is None:
        raise RuntimeError(MISSING_DEPENDENCY_ERROR)


def build_embedding_input(
    *,
    word: str,
    translation_uk: str | None,
    part_of_speech: str | None,
    examples_json: list[str],
) -> str:
    examples = " | ".join(str(example).strip() for example in examples_json if str(example).strip())
    return "\n".join(
        [
            f"word: {word.strip()}",
            f"part_of_speech: {(part_of_speech or '').strip()}",
            f"translation_uk: {(translation_uk or '').strip()}",
            f"examples: {examples}",
        ]
    ).strip()


def build_encoder(*, model_name: str, device: str) -> Any:
    try:
        from sentence_transformers import SentenceTransformer
    except ModuleNotFoundError as error:
        if error.name == "sentence_transformers":
            raise RuntimeError(MISSING_DEPENDENCY_ERROR) from error
        raise

    cache_key = (model_name, device)
    cache = getattr(build_encoder, "_cache", {})
    encoder = cache.get(cache_key)
    if encoder is not None:
        return encoder
    encoder = SentenceTransformer(model_name, device=device)
    cache[cache_key] = encoder
    setattr(build_encoder, "_cache", cache)
    return encoder


def clear_encoder_cache() -> None:
    cache = getattr(build_encoder, "_cache", None)
    if isinstance(cache, dict):
        cache.clear()
    setattr(build_encoder, "_cache", {})


def build_embedding(
    *,
    word: str,
    translation_uk: str | None,
    part_of_speech: str | None,
    examples_json: list[str],
    model_name: str,
    device: str,
) -> list[float]:
    encoder = build_encoder(model_name=model_name, device=device)
    embedding_input = build_embedding_input(
        word=word,
        translation_uk=translation_uk,
        part_of_speech=part_of_speech,
        examples_json=examples_json,
    )
    vector = encoder.encode(
        [embedding_input],
        batch_size=1,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=False,
    )[0]
    return [float(value) for value in vector.tolist()]
