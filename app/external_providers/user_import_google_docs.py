from __future__ import annotations

import time
from collections.abc import Callable

import httpx

from app.domain.user_import.text_parser import normalize_import_text

MAX_GOOGLE_DOC_TEXT_BYTES = 200_000
GOOGLE_DOC_FETCH_ATTEMPTS = 3
GOOGLE_DOC_FETCH_RETRY_DELAY_SECONDS = 2.0
GOOGLE_DOC_TEMPORARY_ERROR_TEXT = "Не вдалося скачати Google Doc. Спробуйте ще раз трохи пізніше."
GOOGLE_DOC_ACCESS_ERROR_TEXT = "Не вдалося скачати Google Doc. Перевірте, що документ доступний за посиланням."


class GoogleDocFetchError(RuntimeError):
    """Google Doc export could not be downloaded after retryable failures."""


def fetch_google_doc_text(
    export_url: str,
    timeout_seconds: float = 20.0,
    *,
    attempts: int = GOOGLE_DOC_FETCH_ATTEMPTS,
    retry_delay_seconds: float = GOOGLE_DOC_FETCH_RETRY_DELAY_SECONDS,
    sleep_func: Callable[[float], None] = time.sleep,
) -> str:
    attempts = max(int(attempts), 1)
    last_error: Exception | None = None
    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
        for attempt_index in range(attempts):
            try:
                response = client.get(export_url)
                response.raise_for_status()
                if len(response.content) > MAX_GOOGLE_DOC_TEXT_BYTES:
                    raise ValueError("Google Doc завеликий для імпорту.")
                text = response.text
                break
            except ValueError:
                raise
            except httpx.HTTPStatusError as error:
                last_error = error
                if not _should_retry_google_doc_fetch(error, attempt_index=attempt_index, attempts=attempts):
                    raise GoogleDocFetchError(_google_doc_fetch_error_text(error)) from error
                sleep_func(retry_delay_seconds)
            except httpx.RequestError as error:
                last_error = error
                if attempt_index >= attempts - 1:
                    raise GoogleDocFetchError(GOOGLE_DOC_TEMPORARY_ERROR_TEXT) from error
                sleep_func(retry_delay_seconds)
        else:  # pragma: no cover - loop always exits by break or raise
            raise GoogleDocFetchError(GOOGLE_DOC_TEMPORARY_ERROR_TEXT) from last_error
    normalized = normalize_import_text(text)
    if not normalized:
        raise ValueError("Google Doc не містить тексту для імпорту.")
    return normalized


def _should_retry_google_doc_fetch(error: httpx.HTTPStatusError, *, attempt_index: int, attempts: int) -> bool:
    if attempt_index >= attempts - 1:
        return False
    status_code = error.response.status_code if error.response is not None else 0
    return status_code == 429 or 500 <= status_code < 600


def _google_doc_fetch_error_text(error: httpx.HTTPStatusError) -> str:
    status_code = error.response.status_code if error.response is not None else 0
    if status_code in {401, 403, 404}:
        return GOOGLE_DOC_ACCESS_ERROR_TEXT
    return GOOGLE_DOC_TEMPORARY_ERROR_TEXT
