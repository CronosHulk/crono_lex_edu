from __future__ import annotations

import re
from datetime import datetime
from typing import Any, NoReturn

PROJECT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
PROJECT_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
DEFAULT_FILTER_VALUE_RE = re.compile(r"^[a-zA-Z0-9_.:-]+$")


class RequestValueValidationError(ValueError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def _error(detail: str) -> NoReturn:
    raise RequestValueValidationError(detail)


def ensure_positive_int(value: Any, field_name: str) -> int:
    try:
        resolved = int(value)
    except (TypeError, ValueError) as error:
        raise RequestValueValidationError(f"{field_name} must be a positive integer") from error
    if resolved <= 0:
        _error(f"{field_name} must be a positive integer")
    return resolved


def ensure_text(
    value: Any,
    field_name: str,
    *,
    max_length: int,
    required: bool = False,
) -> str:
    if value is None:
        if required:
            _error(f"{field_name} is required")
        return ""
    text = str(value).strip()
    if required and not text:
        _error(f"{field_name} is required")
    if len(text) > max_length:
        _error(f"{field_name} must be at most {max_length} characters")
    return text


def normalize_string_list(
    value: str | list[str] | tuple[str, ...] | None,
    field_name: str,
    *,
    max_items: int = 50,
    max_item_length: int = 100,
) -> list[str]:
    if value is None:
        return []
    raw_values = value.split(",") if isinstance(value, str) else list(value)
    normalized = [str(item).strip() for item in raw_values if str(item).strip()]
    if len(normalized) > max_items:
        _error(f"{field_name} accepts at most {max_items} values")
    for item in normalized:
        if len(item) > max_item_length:
            _error(f"{field_name} values must be at most {max_item_length} characters")
    return normalized


def normalize_filter_values(value: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if value is None:
        return []
    raw_values = value.split(",") if isinstance(value, str) else list(value)
    normalized: list[str] = []
    for item in raw_values:
        candidate = str(item).strip()
        if candidate and candidate not in normalized:
            normalized.append(candidate)
    return normalized


def ensure_allowed_value(value: Any, allowed_values: set[str] | list[str] | tuple[str, ...], field_name: str) -> str:
    text = ensure_text(value, field_name, max_length=100, required=True)
    allowed = {str(item) for item in allowed_values}
    if text not in allowed:
        expected = ", ".join(sorted(allowed))
        _error(f"{field_name} must be one of: {expected}")
    return text


def ensure_allowed_values(
    value: str | list[str] | tuple[str, ...] | None,
    allowed_values: set[str] | list[str] | tuple[str, ...],
    field_name: str,
    *,
    max_items: int = 50,
) -> list[str]:
    values = normalize_string_list(value, field_name, max_items=max_items)
    allowed = {str(item) for item in allowed_values}
    invalid = [item for item in values if item not in allowed]
    if invalid:
        expected = ", ".join(sorted(allowed))
        _error(f"{field_name} contains unsupported value '{invalid[0]}'. Expected one of: {expected}")
    return values


def ensure_values_match_pattern(
    value: str | list[str] | tuple[str, ...] | None,
    field_name: str,
    *,
    pattern: re.Pattern[str] = DEFAULT_FILTER_VALUE_RE,
    max_items: int = 50,
    max_item_length: int = 100,
) -> list[str]:
    values = normalize_string_list(value, field_name, max_items=max_items, max_item_length=max_item_length)
    for item in values:
        if not pattern.fullmatch(item):
            _error(f"{field_name} values must match pattern {pattern.pattern}")
    return values


def ensure_unique_positive_int_list(value: list[int], field_name: str, *, max_items: int = 200) -> list[int]:
    if len(value) > max_items:
        _error(f"{field_name} accepts at most {max_items} values")
    result: list[int] = []
    seen: set[int] = set()
    for item in value:
        resolved = ensure_positive_int(item, field_name)
        if resolved not in seen:
            seen.add(resolved)
            result.append(resolved)
    if not result:
        _error(f"{field_name} must contain at least one id")
    return result


def ensure_project_datetime_string(value: Any, field_name: str) -> str:
    text = ensure_text(value, field_name, max_length=19, required=True)
    if not PROJECT_DATETIME_RE.fullmatch(text):
        _error(f"{field_name} must use YYYY-MM-DD HH:MM:SS format")
    try:
        parsed = datetime.strptime(text, PROJECT_DATETIME_FORMAT)
    except ValueError as error:
        raise RequestValueValidationError(f"{field_name} must be a valid datetime") from error
    if parsed.strftime(PROJECT_DATETIME_FORMAT) != text:
        _error(f"{field_name} must use YYYY-MM-DD HH:MM:SS format")
    return text


def validate_filter_metadata_values(
    metadata: dict[str, Any],
    field_name: str,
    value: str | list[str] | tuple[str, ...] | None,
    *,
    max_items: int = 50,
) -> list[str]:
    options: set[str] = set()
    for filter_item in metadata.get("filters", []):
        if filter_item.get("name") != field_name:
            continue
        options = {str(option.get("value")) for option in filter_item.get("options", []) if option.get("value") is not None}
        break
    return ensure_allowed_values(value, options, field_name, max_items=max_items)
