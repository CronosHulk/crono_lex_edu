from __future__ import annotations


def parse_import_job_id(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        job_id = int(value)
    except (TypeError, ValueError):
        return None
    if job_id <= 0:
        return None
    return job_id
