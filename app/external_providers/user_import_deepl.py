from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"


def resolve_deepl_api_key() -> str:
    value = os.environ.get("DEEPL__API_KEY", "").strip()
    if not value:
        raise RuntimeError("DEEPL__API_KEY is not configured.")
    return value


def translate_word_to_uk(client: httpx.Client, word: str, *, context: str | None = None) -> str:
    auth_key = resolve_deepl_api_key()
    payload: dict[str, Any] = {
        "text": [word],
        "source_lang": "EN",
        "target_lang": "UK",
        "split_sentences": "0",
        "preserve_formatting": True,
    }
    if context:
        payload["context"] = context
    response = client.post(
        DEFAULT_DEEPL_API_URL,
        headers={
            "Authorization": f"DeepL-Auth-Key {auth_key}",
            "Content-Type": "application/json",
        },
        json=payload,
    )
    response.raise_for_status()
    data = response.json()
    translations = data.get("translations")
    if not isinstance(translations, list) or not translations:
        raise RuntimeError("DeepL response does not contain translations")
    text = translations[0].get("text")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError(f"DeepL response does not contain translated text for word: {word}")
    return text.strip()
