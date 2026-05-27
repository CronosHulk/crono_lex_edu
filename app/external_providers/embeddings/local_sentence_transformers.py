from __future__ import annotations

import importlib.util
from typing import Any

MISSING_DEPENDENCY_ERROR = (
    "fastembed is not installed. Run embeddings via the app-embedding-worker "
    "image built from Dockerfile.embeddings."
)


def ensure_runtime_available() -> None:
    if importlib.util.find_spec("fastembed") is None:
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
        from fastembed import TextEmbedding
    except ModuleNotFoundError as error:
        if error.name == "fastembed":
            raise RuntimeError(MISSING_DEPENDENCY_ERROR) from error
        raise

    cache_key = (model_name, device)
    cache = getattr(build_encoder, "_cache", {})
    encoder = cache.get(cache_key)
    if encoder is not None:
        return encoder
    
    # fastembed uses ONNX runtime under the hood, optimized for CPU execution out-of-the-box.
    encoder = TextEmbedding(model_name=model_name)
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
    # fastembed's embed() returns a generator of numpy ndarrays.
    vectors = list(encoder.embed([embedding_input]))
    vector = vectors[0]
    return [float(value) for value in vector.tolist()]
