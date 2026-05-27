from __future__ import annotations

from typing import Any

import app.validation.request_values as request_values


def normalize_pagination(
    params: dict[str, Any],
    *,
    default_page_size: int,
    allowed_page_sizes: set[int],
) -> tuple[int, int]:
    raw_page_size = params.get("page_size") or default_page_size
    page_size = int(
        request_values.ensure_allowed_value(
            raw_page_size,
            {str(value) for value in allowed_page_sizes},
            "page_size",
        )
    )
    page = request_values.ensure_positive_int(params.get("page") or 1, "page")
    return page, page_size
