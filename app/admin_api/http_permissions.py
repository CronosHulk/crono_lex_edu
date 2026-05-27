from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException

from app.acl.processor import AclEnvironment, AclProcessor
from app.application.admin.permissions import (
    AdminPermissionDatabasePort,
    AdminPermissionDeniedError,
    ensure_admin_actor_allowed,
    ensure_super_admin_actor_allowed,
    require_acl_access_allowed,
    require_admin_access_allowed,
)


def require_admin_access(
    db: AdminPermissionDatabasePort,
    actor: dict[str, object],
    *,
    action: str,
    detail: str = "Access denied",
) -> None:
    _translate_permission_error(
        lambda: require_admin_access_allowed(db, actor, action=action, detail=detail),
    )


def require_acl_access(
    acl_processor: AclProcessor,
    actor: dict[str, object] | None,
    *,
    action: str,
    environment: AclEnvironment,
    detail: str = "Access denied",
) -> None:
    _translate_permission_error(
        lambda: require_acl_access_allowed(
            acl_processor,
            actor,
            action=action,
            environment=environment,
            detail=detail,
        ),
    )


def ensure_super_admin_actor(actor: dict[str, object]) -> None:
    _translate_permission_error(lambda: ensure_super_admin_actor_allowed(actor))


def ensure_admin_actor(actor: dict[str, object]) -> None:
    _translate_permission_error(lambda: ensure_admin_actor_allowed(actor))


def _translate_permission_error(check: Callable[[], None]) -> None:
    try:
        check()
    except AdminPermissionDeniedError as error:
        raise HTTPException(status_code=403, detail=error.detail) from error
