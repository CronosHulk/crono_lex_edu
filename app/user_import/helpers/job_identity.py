from __future__ import annotations

from typing import Any
from uuid import UUID


def resolve_job_user_uuid(job: dict[str, Any]) -> UUID | None:
    raw_user_id = job.get("user_uuid") or job.get("user_id")
    if raw_user_id is None:
        return None
    return UUID(str(raw_user_id))
