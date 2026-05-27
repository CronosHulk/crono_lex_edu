from __future__ import annotations

from typing import Any, Protocol

from app.acl.processor import AclEnvironment, AclPermissionReader, AclProcessor

ALLOWED_ADMIN_ROLES = {"admin", "admin_editor", "super_admin"}


class AdminPermissionDatabasePort(Protocol):
    acl_permissions: AclPermissionReader


class AdminPermissionDeniedError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def require_admin_access_allowed(
    db: AdminPermissionDatabasePort,
    actor: dict[str, Any],
    *,
    action: str,
    detail: str = "Access denied",
) -> None:
    require_acl_access_allowed(
        AclProcessor(db.acl_permissions),
        actor,
        action=action,
        environment="web_admin",
        detail=detail,
    )


def require_acl_access_allowed(
    acl_processor: AclProcessor,
    actor: dict[str, Any] | None,
    *,
    action: str,
    environment: AclEnvironment,
    detail: str = "Access denied",
) -> None:
    decision = acl_processor.can_access(actor, action=action, environment=environment)
    if not decision.is_allowed:
        raise AdminPermissionDeniedError(detail)


def ensure_super_admin_actor_allowed(actor: dict[str, Any]) -> None:
    if actor.get("acl_group_title") != "super_admin":
        raise AdminPermissionDeniedError("Action is allowed only for super_admin")


def ensure_admin_actor_allowed(actor: dict[str, Any]) -> None:
    if actor.get("acl_group_title") not in ALLOWED_ADMIN_ROLES:
        raise AdminPermissionDeniedError("Admin access required")
