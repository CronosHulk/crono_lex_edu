from __future__ import annotations

from app.serialization.json_datetimes import normalize_json_datetimes


def test_normalize_json_datetimes_formats_nested_iso_strings() -> None:
    payload = {
        "created": "2026-12-01T00:01:02Z",
        "items": [
            {"updated": "2026-12-01T03:01:02+02:00"},
            {"plain": "not-a-date"},
        ],
    }

    assert normalize_json_datetimes(payload, timezone_name="Europe/Kyiv") == {
        "created": "2026-12-01 02:01:02",
        "items": [
            {"updated": "2026-12-01 03:01:02"},
            {"plain": "not-a-date"},
        ],
    }


def test_normalize_json_datetimes_leaves_invalid_iso_like_string_unchanged() -> None:
    payload = {"created": "2026-99-01T00:01:02Z"}

    assert normalize_json_datetimes(payload, timezone_name="Europe/Kyiv") == payload
