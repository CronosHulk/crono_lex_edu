from __future__ import annotations

import pytest

import app.external_providers.embeddings.local_sentence_transformers as local_sentence_transformers


def test_build_embedding_input_uses_stable_text_contract() -> None:
    payload = local_sentence_transformers.build_embedding_input(
        word=" harbor ",
        part_of_speech="verb",
        translation_uk="давати притулок",
        examples_json=[" They harbor hope. ", "", "Small towns harbor artists."],
    )

    assert payload == (
        "word: harbor\n"
        "part_of_speech: verb\n"
        "translation_uk: давати притулок\n"
        "examples: They harbor hope. | Small towns harbor artists."
    )


def test_ensure_runtime_available_reports_embedding_worker_image(monkeypatch) -> None:
    monkeypatch.setattr(local_sentence_transformers.importlib.util, "find_spec", lambda name: None)

    with pytest.raises(RuntimeError) as error:
        local_sentence_transformers.ensure_runtime_available()

    assert "Dockerfile.embeddings" in str(error.value)
    assert "app-embedding-worker" in str(error.value)


def test_clear_encoder_cache_drops_cached_models() -> None:
    local_sentence_transformers.build_encoder._cache = {("model", "cpu"): object()}

    local_sentence_transformers.clear_encoder_cache()

    assert local_sentence_transformers.build_encoder._cache == {}
