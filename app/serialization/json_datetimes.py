from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.time_utils import format_project_datetime

ISO_DATETIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$"
)


def normalize_json_datetimes(value: Any, *, timezone_name: str) -> Any:
    if isinstance(value, dict):
        return {key: normalize_json_datetimes(item, timezone_name=timezone_name) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_json_datetimes(item, timezone_name=timezone_name) for item in value]
    if isinstance(value, str) and ISO_DATETIME_PATTERN.match(value):
        return _format_iso_datetime_string(value, timezone_name=timezone_name)
    return value


def _format_iso_datetime_string(value: str, *, timezone_name: str) -> str:
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return value
    return format_project_datetime(parsed, timezone_name)
