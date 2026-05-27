from __future__ import annotations

import re
from urllib.parse import urlparse

GOOGLE_DOC_HOST = "docs.google.com"
GOOGLE_DOC_PATH_RE = re.compile(r"^/document(?:/u/\d+)?/d/([a-zA-Z0-9_-]+)(?:/|$)")


def extract_google_doc_id(value: str) -> str:
    candidate = value.strip()
    parsed = urlparse(candidate)
    if parsed.scheme != "https" or parsed.netloc.lower() != GOOGLE_DOC_HOST:
        raise ValueError("Потрібне публічне https-посилання на Google Doc.")
    if parsed.query or parsed.fragment:
        candidate = parsed._replace(query="", fragment="").geturl()
        parsed = urlparse(candidate)
    match = GOOGLE_DOC_PATH_RE.match(parsed.path)
    if match is None:
        raise ValueError("Посилання має вести на Google Doc у форматі /document/d/<id>.")
    return match.group(1)


def build_google_doc_export_url(doc_id: str) -> str:
    return f"https://docs.google.com/document/d/{doc_id}/export?format=txt"


def validate_google_doc_url(value: str) -> str:
    return build_google_doc_export_url(extract_google_doc_id(value))


def mask_google_doc_url(value: str) -> str:
    try:
        doc_id = extract_google_doc_id(value)
    except Exception:
        candidate = value.strip()
        if not candidate:
            return "[invalid google doc url]"
        doc_id = candidate
    masked_doc_id = f"{doc_id[:4]}...{doc_id[-4:]}" if len(doc_id) > 8 else "***"
    return f"https://docs.google.com/document/d/{masked_doc_id}/..."
