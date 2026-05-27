from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.acl.processor import AclProcessor
from app.admin_api.http_permissions import (
    ensure_admin_actor,
    ensure_super_admin_actor,
    require_acl_access,
)
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    ensure_admin_actor_allowed,
    ensure_super_admin_actor_allowed,
    require_acl_access_allowed,
)


class FakeAclPermissions:
    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None:
        if (group_title, action, environment) == ("admin", "users/delete", "web_admin"):
            return "disabled"
        if (group_title, action, environment) == ("admin", "users/list", "web_admin"):
            return "enabled"
        return None

    def list_group_capabilities(self, *, group_title: str, environment: str) -> list[str]:
        return []


def test_application_admin_permissions_raise_local_denied_error() -> None:
    with pytest.raises(AdminPermissionDeniedError) as error:
        require_acl_access_allowed(
            AclProcessor(FakeAclPermissions()),
            {"telegram_user_id": 1, "acl_group_title": "admin"},
            action="users/delete",
            environment="web_admin",
            detail="Only super admin can delete users",
        )

    assert error.value.detail == "Only super admin can delete users"


def test_application_admin_permissions_allow_valid_acl_decision() -> None:
    require_acl_access_allowed(
        AclProcessor(FakeAclPermissions()),
        {"telegram_user_id": 1, "acl_group_title": "admin"},
        action="users/list",
        environment="web_admin",
    )


def test_admin_role_checks_raise_local_denied_error() -> None:
    with pytest.raises(AdminPermissionDeniedError) as admin_error:
        ensure_admin_actor_allowed({"telegram_user_id": 1, "acl_group_title": "student"})
    with pytest.raises(AdminPermissionDeniedError) as super_admin_error:
        ensure_super_admin_actor_allowed({"telegram_user_id": 1, "acl_group_title": "admin"})

    assert admin_error.value.detail == "Admin access required"
    assert super_admin_error.value.detail == "Action is allowed only for super_admin"


def test_admin_permission_http_wrapper_preserves_http_exception_contract() -> None:
    with pytest.raises(HTTPException) as acl_error:
        require_acl_access(
            AclProcessor(FakeAclPermissions()),
            {"telegram_user_id": 1, "acl_group_title": "admin"},
            action="users/delete",
            environment="web_admin",
            detail="Only super admin can delete users",
        )
    with pytest.raises(HTTPException) as admin_error:
        ensure_admin_actor({"telegram_user_id": 1, "acl_group_title": "student"})
    with pytest.raises(HTTPException) as super_admin_error:
        ensure_super_admin_actor({"telegram_user_id": 1, "acl_group_title": "admin"})

    assert acl_error.value.status_code == 403
    assert acl_error.value.detail == "Only super admin can delete users"
    assert admin_error.value.status_code == 403
    assert admin_error.value.detail == "Admin access required"
    assert super_admin_error.value.status_code == 403
    assert super_admin_error.value.detail == "Action is allowed only for super_admin"
