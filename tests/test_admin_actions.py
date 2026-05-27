from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.acl.processor import AclProcessor
from app.admin_api.http_permissions import (
    ensure_admin_actor,
    ensure_super_admin_actor,
    require_acl_access,
)
from app.application.admin.dictionary.action_service import AdminDictionaryActionService
from app.application.admin.dictionary.errors import (
    AdminDictionaryActionAssignedEntryError,
    AdminDictionaryActionEntityNotFoundError,
)
from app.application.admin.users.action_service import AdminUserActionService
from app.application.admin.users.errors import (
    AdminUserActionAccessDeniedError,
    AdminUserActionValidationError,
)
from app.time_utils import TimeService
from tests.test_admin_service import FakeAdminDb, build_pending_row


class FakeAclPermissions:
    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None:
        if (group_title, action, environment) == ("admin", "users/delete", "web_admin"):
            return "disabled"
        return None

    def list_group_capabilities(self, *, group_title: str, environment: str) -> list[str]:
        return []


def test_admin_http_permissions_reject_non_admins() -> None:
    try:
        ensure_admin_actor({"telegram_user_id": 1, "acl_group_title": "student"})
    except HTTPException as error:
        assert error.status_code == 403
        assert error.detail == "Admin access required"
    else:  # pragma: no cover
        raise AssertionError("HTTPException was expected")

    try:
        ensure_super_admin_actor({"telegram_user_id": 1, "acl_group_title": "admin"})
    except HTTPException as error:
        assert error.status_code == 403
        assert error.detail == "Action is allowed only for super_admin"
    else:  # pragma: no cover
        raise AssertionError("HTTPException was expected")


def test_admin_http_permissions_translate_denied_decision_to_http_exception() -> None:
    try:
        require_acl_access(
            AclProcessor(FakeAclPermissions()),
            {"telegram_user_id": 1, "acl_group_title": "admin"},
            action="users/delete",
            environment="web_admin",
            detail="Only super admin can delete users",
        )
    except HTTPException as error:
        assert error.status_code == 403
        assert error.detail == "Only super admin can delete users"
    else:  # pragma: no cover
        raise AssertionError("HTTPException was expected")


def test_admin_user_action_service_sets_allowed_role() -> None:
    db = FakeAdminDb(build_pending_row())
    service = AdminUserActionService(db, TimeService("Europe/Kyiv"))

    result = service.set_role(
        actor={"telegram_user_id": 2, "acl_group_title": "super_admin"},
        target_user_id=1,
        role="admin_editor",
    )

    assert result["acl_group_title"] == "admin_editor"


def test_admin_user_action_service_sets_learning_role() -> None:
    db = FakeAdminDb(build_pending_row())
    service = AdminUserActionService(db, TimeService("Europe/Kyiv"))

    result = service.set_learning_role(
        actor={"telegram_user_id": 2, "acl_group_title": "super_admin"},
        target_user_id=1,
        learning_role="teacher",
    )

    assert result["learning_role"] == "teacher"


def test_admin_user_action_service_sets_subscription_plan() -> None:
    db = FakeAdminDb(build_pending_row())
    service = AdminUserActionService(db, TimeService("Europe/Kyiv"))

    result = service.set_subscription(
        actor={"telegram_user_id": 2, "acl_group_title": "super_admin"},
        target_user_id="11111111-1111-4111-8111-111111111111",
        plan_key="premium",
    )

    assert result["subscription_plan_key"] == "premium"
    assert db.subscription_updates[0]["plan_key"] == "premium"


def test_admin_user_action_service_toggles_subscription_trial() -> None:
    db = FakeAdminDb(build_pending_row())
    db.admin_user["subscription_plan_key"] = "free"
    service = AdminUserActionService(db, TimeService("Europe/Kyiv"))

    enabled = service.set_subscription_trial(
        actor={"telegram_user_id": 2, "acl_group_title": "super_admin"},
        target_user_id="11111111-1111-4111-8111-111111111111",
        is_trial_enabled=True,
    )
    disabled = service.set_subscription_trial(
        actor={"telegram_user_id": 2, "acl_group_title": "super_admin"},
        target_user_id="11111111-1111-4111-8111-111111111111",
        is_trial_enabled=False,
    )

    assert enabled["trial_end"] is not None
    assert disabled["trial_end"] is None


def test_admin_user_action_service_rejects_subscription_change_for_non_super_admin() -> None:
    service = AdminUserActionService(FakeAdminDb(build_pending_row()), TimeService("Europe/Kyiv"))

    with pytest.raises(AdminUserActionAccessDeniedError) as error:
        service.set_subscription(
            actor={"telegram_user_id": 2, "acl_group_title": "admin"},
            target_user_id="11111111-1111-4111-8111-111111111111",
            plan_key="premium",
        )

    assert error.value.detail == "Subscription change is not allowed"


def test_admin_user_action_service_rejects_self_archive() -> None:
    service = AdminUserActionService(FakeAdminDb(build_pending_row()), TimeService("Europe/Kyiv"))

    with pytest.raises(AdminUserActionValidationError) as error:
        service.archive(
            actor={
                "telegram_user_id": 1,
                "user_id": "11111111-1111-4111-8111-111111111111",
                "acl_group_title": "super_admin",
            },
            user_id="11111111-1111-4111-8111-111111111111",
        )

    assert error.value.detail == "You cannot archive your own user"


def test_admin_dictionary_action_service_archives_entry() -> None:
    db = FakeAdminDb(build_pending_row())
    db.dictionary_entry = {"id": 10, "word": "harbor", "archived": False}
    service = AdminDictionaryActionService(db, TimeService("Europe/Kyiv"))

    result = service.archive_entry(actor={"telegram_user_id": 1, "acl_group_title": "super_admin"}, entry_id=10)

    assert result == {"status": "ok"}
    assert db.dictionary_entry["archived"] is True


def test_admin_dictionary_action_service_rejects_delete_for_assigned_entry() -> None:
    db = FakeAdminDb(build_pending_row())
    db.dictionary_entry = {"id": 10, "word": "harbor", "archived": False}
    db.assigned_dictionary_entry_count = 1
    service = AdminDictionaryActionService(db, TimeService("Europe/Kyiv"))

    with pytest.raises(AdminDictionaryActionAssignedEntryError) as error:
        service.delete_entry(actor={"telegram_user_id": 1, "acl_group_title": "super_admin"}, entry_id=10)

    assert "assigned to users" in str(error.value.detail)

    assert db.deleted_dictionary_entry_ids == []


def test_admin_dictionary_action_service_rejects_archive_for_missing_entry() -> None:
    service = AdminDictionaryActionService(FakeAdminDb(build_pending_row()), TimeService("Europe/Kyiv"))

    with pytest.raises(AdminDictionaryActionEntityNotFoundError) as error:
        service.archive_entry(actor={"telegram_user_id": 1, "acl_group_title": "super_admin"}, entry_id=404)

    assert error.value.detail == "Entity not found"


def test_admin_dictionary_action_service_rejects_delete_for_missing_entry() -> None:
    service = AdminDictionaryActionService(FakeAdminDb(build_pending_row()), TimeService("Europe/Kyiv"))

    with pytest.raises(AdminDictionaryActionEntityNotFoundError) as error:
        service.delete_entry(actor={"telegram_user_id": 1, "acl_group_title": "super_admin"}, entry_id=404)

    assert error.value.detail == "Entity not found"


def test_admin_dictionary_action_service_marks_entries_verified() -> None:
    db = FakeAdminDb(build_pending_row())
    db.dictionary_entries = [{"id": 10, "word": "harbor", "archived": False, "is_teacher_verified": False}]
    service = AdminDictionaryActionService(db, TimeService("Europe/Kyiv"))

    result = service.verify_entries(
        actor={
            "telegram_user_id": 1,
            "user_id": "11111111-1111-4111-8111-111111111111",
            "acl_group_title": "super_admin",
        },
        entry_ids=[10],
    )

    assert result == {"status": "ok", "verified_count": 1}
    assert db.dictionary_entries[0]["is_teacher_verified"] is True


def test_service_scoped_actions_are_available_from_atomic_modules() -> None:
    from app.application.admin.dictionary.archive_entry import archive_dictionary_entry
    from app.application.admin.dictionary.delete_entry import delete_dictionary_entry
    from app.application.admin.dictionary.verify_entries import verify_dictionary_entries
    from app.application.admin.users.archive_user import archive_user
    from app.application.admin.users.delete_user import delete_user
    from app.application.admin.users.set_learning_role import set_user_learning_role
    from app.application.admin.users.set_role import set_user_role
    from app.application.admin.users.set_subscription import set_user_subscription

    assert archive_dictionary_entry is not None
    assert delete_dictionary_entry is not None
    assert verify_dictionary_entries is not None
    assert archive_user is not None
    assert delete_user is not None
    assert set_user_learning_role is not None
    assert set_user_role is not None
    assert set_user_subscription is not None
