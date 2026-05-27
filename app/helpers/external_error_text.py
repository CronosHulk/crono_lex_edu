from __future__ import annotations

import json
import re

import httpx


def sanitize_external_error_text(value: str) -> str:
    sanitized = value
    sanitized = re.sub(r"([?&](?:api_key|key)=)[^&\s]+", r"\1[redacted]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"(DeepL-Auth-Key\s+)[^\s,;]+", r"\1[redacted]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"(Authorization['\"]?:\s*['\"]?)[^'\",\s]+", r"\1[redacted]", sanitized, flags=re.IGNORECASE)
    return sanitized


def mask_provider_error_for_user(error_text: str | None, fallback: str) -> str:
    if not error_text:
        return fallback
    sanitized = sanitize_external_error_text(error_text)
    if "http" in sanitized.lower() or "[redacted]" in sanitized.lower():
        return fallback
    return sanitized


def format_external_error(error: Exception, *, fallback: str) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code if error.response is not None else "unknown"
        return f"{fallback} (HTTP {status_code})"
    if isinstance(error, httpx.RequestError):
        return f"{fallback} (request error)"
    return sanitize_external_error_text(str(error)) or fallback


def format_word_details_provider_error(error: Exception) -> str:
    if isinstance(error, httpx.RequestError | httpx.HTTPStatusError):
        return format_external_error(error, fallback="details provider request failed")
    if isinstance(error, ValueError | json.JSONDecodeError | KeyError | TypeError):
        return f"details provider bad response/schema error: {sanitize_external_error_text(str(error))}"
    return format_external_error(error, fallback="details provider error")
