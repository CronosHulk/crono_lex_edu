from __future__ import annotations

DEFAULT_ADMIN_TARGET_PATH = "/admin/user-dictionary"


def normalize_admin_target_path(value: str | None) -> str:
    target_path = str(value or DEFAULT_ADMIN_TARGET_PATH).strip() or DEFAULT_ADMIN_TARGET_PATH
    if not target_path.startswith("/admin") or target_path.startswith("//") or "://" in target_path:
        return DEFAULT_ADMIN_TARGET_PATH
    return target_path[:500]
