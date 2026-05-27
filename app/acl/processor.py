from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal, Protocol

AclEnvironment = Literal["web_admin", "client_web", "telegram_user"]
ACL_ACTION_PATTERN = re.compile(r"^[a-z][a-z0-9_]*/[a-z][a-z0-9_]*$")


class AclPermissionReader(Protocol):
    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None: ...

    def list_group_capabilities(self, *, group_title: str, environment: str) -> list[str]: ...


@dataclass(frozen=True)
class AccessDecision:
    is_allowed: bool
    action: str
    environment: str
    reason: str | None = None


class AclProcessor:
    def __init__(self, permissions: AclPermissionReader) -> None:
        self.permissions = permissions

    def can_access(self, user: dict[str, Any] | None, *, action: str, environment: AclEnvironment) -> AccessDecision:
        if not user:
            return AccessDecision(False, action, environment, "User is required")
        group_title = str(user.get("acl_group_title") or "").strip()
        if not group_title:
            return AccessDecision(False, action, environment, "User ACL group is required")
        normalized_action = normalize_acl_action(action)
        if not is_valid_acl_action(normalized_action):
            return AccessDecision(False, action, environment, "Action must use service/action format")
        rule = self.permissions.get_effective_rule(
            group_title=group_title,
            action=normalized_action,
            environment=environment,
        )
        if rule == "enabled":
            return AccessDecision(True, action, environment)
        if rule == "disabled":
            return AccessDecision(False, action, environment, "Access disabled")
        return AccessDecision(False, action, environment, "Access is not configured")

    def capabilities_for(self, user: dict[str, Any] | None, *, environment: AclEnvironment) -> list[str]:
        if not user:
            return []
        group_title = str(user.get("acl_group_title") or "").strip()
        if not group_title:
            return []
        return self.permissions.list_group_capabilities(group_title=group_title, environment=environment)


def normalize_acl_action(action: str) -> str:
    return str(action or "").strip()


def is_valid_acl_action(action: str) -> bool:
    return bool(ACL_ACTION_PATTERN.fullmatch(action))
