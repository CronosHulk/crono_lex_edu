from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from fastapi import HTTPException

import app.validation.request_values as request_values

DEFAULT_FILTER_VALUE_RE = request_values.DEFAULT_FILTER_VALUE_RE
PROJECT_DATETIME_FORMAT = request_values.PROJECT_DATETIME_FORMAT
PROJECT_DATETIME_RE = request_values.PROJECT_DATETIME_RE

P = ParamSpec("P")
T = TypeVar("T")

__all__ = [
    "DEFAULT_FILTER_VALUE_RE",
    "PROJECT_DATETIME_FORMAT",
    "PROJECT_DATETIME_RE",
    "ensure_allowed_value",
    "ensure_allowed_values",
    "ensure_positive_int",
    "ensure_project_datetime_string",
    "ensure_text",
    "ensure_unique_positive_int_list",
    "ensure_values_match_pattern",
    "normalize_string_list",
    "validate_filter_metadata_values",
]


def _http_validation(validator: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        return validator(*args, **kwargs)
    except request_values.RequestValueValidationError as error:
        raise HTTPException(status_code=400, detail=error.detail) from error


def ensure_positive_int(value: Any, field_name: str) -> int:
    return _http_validation(request_values.ensure_positive_int, value, field_name)


def ensure_text(
    value: Any,
    field_name: str,
    *,
    max_length: int,
    required: bool = False,
) -> str:
    return _http_validation(request_values.ensure_text, value, field_name, max_length=max_length, required=required)


def normalize_string_list(
    value: str | list[str] | tuple[str, ...] | None,
    field_name: str,
    *,
    max_items: int = 50,
    max_item_length: int = 100,
) -> list[str]:
    return _http_validation(
        request_values.normalize_string_list,
        value,
        field_name,
        max_items=max_items,
        max_item_length=max_item_length,
    )


def ensure_allowed_value(value: Any, allowed_values: set[str] | list[str] | tuple[str, ...], field_name: str) -> str:
    return _http_validation(request_values.ensure_allowed_value, value, allowed_values, field_name)


def ensure_allowed_values(
    value: str | list[str] | tuple[str, ...] | None,
    allowed_values: set[str] | list[str] | tuple[str, ...],
    field_name: str,
    *,
    max_items: int = 50,
) -> list[str]:
    return _http_validation(request_values.ensure_allowed_values, value, allowed_values, field_name, max_items=max_items)


def ensure_values_match_pattern(
    value: str | list[str] | tuple[str, ...] | None,
    field_name: str,
    *,
    pattern: re.Pattern[str] = DEFAULT_FILTER_VALUE_RE,
    max_items: int = 50,
    max_item_length: int = 100,
) -> list[str]:
    return _http_validation(
        request_values.ensure_values_match_pattern,
        value,
        field_name,
        pattern=pattern,
        max_items=max_items,
        max_item_length=max_item_length,
    )


def ensure_unique_positive_int_list(value: list[int], field_name: str, *, max_items: int = 200) -> list[int]:
    return _http_validation(request_values.ensure_unique_positive_int_list, value, field_name, max_items=max_items)


def ensure_project_datetime_string(value: Any, field_name: str) -> str:
    return _http_validation(request_values.ensure_project_datetime_string, value, field_name)


def validate_filter_metadata_values(
    metadata: dict[str, Any],
    field_name: str,
    value: str | list[str] | tuple[str, ...] | None,
    *,
    max_items: int = 50,
) -> list[str]:
    return _http_validation(
        request_values.validate_filter_metadata_values,
        metadata,
        field_name,
        value,
        max_items=max_items,
    )
