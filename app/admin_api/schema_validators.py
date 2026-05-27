from __future__ import annotations


def model_allowed_value(value: str, allowed_values: set[str], field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    allowed = {str(item) for item in allowed_values}
    if normalized not in allowed:
        expected = ", ".join(sorted(allowed))
        raise ValueError(f"{field_name} must be one of: {expected}")
    return normalized


def model_positive_id_list(value: list[int], field_name: str) -> list[int]:
    result: list[int] = []
    seen: set[int] = set()
    for item in value:
        resolved = int(item)
        if resolved <= 0:
            raise ValueError(f"{field_name} must be a positive integer")
        if resolved not in seen:
            seen.add(resolved)
            result.append(resolved)
    if not result:
        raise ValueError(f"{field_name} must contain at least one id")
    return result
