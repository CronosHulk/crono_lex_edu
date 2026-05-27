from __future__ import annotations

import pytest

from app.application.admin.dictionary.errors import (
    AdminDictionaryReadAccessDeniedError,
    AdminDictionaryReadEntryNotFoundError,
    AdminDictionaryReadValidationError,
    AdminDictionaryReadVerifiedFilterError,
)
from app.application.admin.dictionary.read_service import AdminDictionaryReadService
from app.application.admin.imports.errors import (
    AdminImportReadAccessDeniedError,
    AdminImportReadNotFoundError,
    AdminImportReadValidationError,
)
from app.application.admin.imports.read_service import AdminImportReadService
from app.application.admin.logs.errors import (
    AdminLogReadAccessDeniedError,
    AdminLogReadNotFoundError,
    AdminLogReadValidationError,
)
from app.application.admin.logs.read_service import AdminLogReadService
from app.application.admin.read.errors import (
    AdminReadAccessDeniedError,
    AdminReadUnknownEntityError,
    AdminReadValidationError,
)
from app.application.admin.read.read_service import AdminReadService
from app.application.admin.users.errors import (
    AdminUserReadAccessDeniedError,
    AdminUserReadNotFoundError,
    AdminUserReadValidationError,
)
from app.application.admin.users.read_service import AdminUserReadService
from tests.test_admin_service import FakeAdminDb, build_pending_row

ACTOR = {"telegram_user_id": 1, "acl_group_title": "admin"}
DENIED_ACTOR = {"telegram_user_id": 1, "acl_group_title": "student"}


class _ActionAclPermissions:
    def __init__(self, enabled_actions: set[str]) -> None:
        self.enabled_actions = enabled_actions
        self.calls: list[tuple[str, str, str]] = []

    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None:
        self.calls.append((group_title, action, environment))
        if environment == "web_admin" and action in self.enabled_actions:
            return "enabled"
        return "disabled"

    def list_group_capabilities(self, *, group_title: str, environment: str) -> list[str]:
        if environment != "web_admin":
            return []
        return sorted(self.enabled_actions)


def test_admin_read_service_lists_import_jobs_with_valid_pagination() -> None:
    db = FakeAdminDb(build_pending_row())
    db.import_jobs = [
        {
            "id": 91,
            "telegram_user_id": 1,
            "status": "completed",
            "source_type": "bound_google_doc",
            "source_identifier": "doc-a",
        }
    ]
    service = AdminReadService(db)

    result = service.list_import_jobs(
        actor={"telegram_user_id": 1, "acl_group_title": "admin"},
        params={"page": 1, "page_size": 50, "search": "doc"},
    )

    assert result["page"] == 1
    assert result["page_size"] == 50
    assert [item["id"] for item in result["items"]] == [91]


def test_admin_read_service_gets_import_job_detail_with_status_counts() -> None:
    db = FakeAdminDb(build_pending_row())
    db.import_job = {
        "id": 91,
        "user_id": "11111111-1111-4111-8111-111111111111",
        "user_uuid": "11111111-1111-4111-8111-111111111111",
        "telegram_user_id": 1,
        "task_log_id": 13,
        "status": "completed",
        "source_type": "bound_google_doc",
        "source_identifier": "doc",
    }
    db.import_items = [
        {"id": 5, "import_job_id": 91, "lookup_word": "harbor", "status": "imported"},
        {"id": 6, "import_job_id": 91, "lookup_word": "dock", "status": "failed"},
        {"id": 7, "import_job_id": 91, "lookup_word": "shore", "status": "failed"},
    ]
    db.task_log = {"id": 13, "task_type": "bound_google_doc_sync", "status": "success"}
    service = AdminReadService(db)

    result = service.get_import_job_detail(
        actor={"telegram_user_id": 1, "acl_group_title": "admin"},
        import_job_id=91,
    )

    assert result["job"]["id"] == 91
    assert result["status_counts"] == {"imported": 1, "failed": 2}
    assert "items" not in result
    assert result["origin_task_log"]["id"] == 13
    assert result["user"]["telegram_user_id"] == 1


def test_admin_dictionary_read_service_lists_entries_with_normalized_pagination() -> None:
    db = FakeAdminDb(build_pending_row())
    db.dictionary_entries = [
        {"id": 10, "word": "harbor", "translation_uk": "гавань", "archived": False},
    ]
    service = AdminDictionaryReadService(db)

    result = service.list_dictionary_entries(
        actor=ACTOR,
        params={"page": "2", "page_size": "100", "search": " harbor "},
    )

    assert result["page"] == 2
    assert result["page_size"] == 100
    assert [item["id"] for item in result["items"]] == [10]


def test_admin_dictionary_read_service_rejects_invalid_pagination() -> None:
    service = AdminDictionaryReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminDictionaryReadValidationError) as error:
        service.list_dictionary_entries(actor=ACTOR, params={"page": "1", "page_size": "25"})

    assert "page_size" in error.value.detail


def test_admin_dictionary_read_service_rejects_missing_entry() -> None:
    service = AdminDictionaryReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminDictionaryReadEntryNotFoundError) as error:
        service.get_dictionary_entry(actor=ACTOR, entry_id=404)

    assert error.value.detail == "Dictionary entry not found"


def test_admin_dictionary_read_service_rejects_invalid_verified_filter() -> None:
    service = AdminDictionaryReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminDictionaryReadVerifiedFilterError) as error:
        service.list_dictionary_entries(actor=ACTOR, params={"verified": "invalid"})

    assert error.value.detail == "verified must be one of: all, verified, unverified"


def test_admin_dictionary_read_service_rejects_invalid_category_filter() -> None:
    service = AdminDictionaryReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminDictionaryReadValidationError) as error:
        service.list_dictionary_entries(actor=ACTOR, params={"category": "ghost"})

    assert "category" in error.value.detail


def test_admin_dictionary_read_service_preserves_denied_list_acl_detail_before_validation() -> None:
    service = AdminDictionaryReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminDictionaryReadAccessDeniedError) as error:
        service.list_dictionary_entries(actor=DENIED_ACTOR, params={"verified": "invalid"})

    assert error.value.detail == "Access denied"


def test_admin_dictionary_read_service_preserves_denied_detail_acl_before_lookup() -> None:
    service = AdminDictionaryReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminDictionaryReadAccessDeniedError) as error:
        service.get_dictionary_entry(actor=DENIED_ACTOR, entry_id=404)

    assert error.value.detail == "Access denied"


def test_admin_import_read_service_lists_import_items_with_normalized_pagination() -> None:
    db = FakeAdminDb(build_pending_row())
    db.import_items = [
        {"id": 5, "import_job_id": 91, "lookup_word": " harbor ", "status": "imported"},
    ]
    service = AdminImportReadService(db)

    result = service.list_import_items(
        actor={"telegram_user_id": 1, "acl_group_title": "admin"},
        params={"page": "2", "page_size": "100", "search": " harbor "},
    )

    assert result["page"] == 2
    assert result["page_size"] == 100
    assert [item["id"] for item in result["items"]] == [5]


def test_admin_import_read_service_rejects_invalid_job_pagination() -> None:
    service = AdminImportReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminImportReadValidationError) as error:
        service.list_import_jobs(actor=ACTOR, params={"page": "1", "page_size": "25"})

    assert "page_size" in error.value.detail


def test_admin_import_read_service_rejects_invalid_item_pagination() -> None:
    service = AdminImportReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminImportReadValidationError) as error:
        service.list_import_items(actor=ACTOR, params={"page": "1", "page_size": "25"})

    assert "page_size" in error.value.detail


def test_admin_import_read_service_rejects_unknown_job_status() -> None:
    service = AdminImportReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminImportReadValidationError) as error:
        service.list_import_jobs(
            actor={"telegram_user_id": 1, "acl_group_title": "admin"},
            params={"status": ["unknown"]},
        )

    assert "status contains unsupported value" in error.value.detail


def test_admin_import_read_service_preserves_denied_list_acl_detail_before_validation() -> None:
    service = AdminImportReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminImportReadAccessDeniedError) as error:
        service.list_import_jobs(actor=DENIED_ACTOR, params={"page": "1", "page_size": "25"})

    assert error.value.detail == "Import jobs access is not allowed"


def test_admin_import_read_service_rejects_missing_import_job_detail() -> None:
    service = AdminImportReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminImportReadNotFoundError) as error:
        service.get_import_job_detail(
            actor={"telegram_user_id": 1, "acl_group_title": "admin"},
            import_job_id=404,
        )

    assert error.value.detail == "Import job not found"


def test_admin_import_read_service_gets_filter_metadata() -> None:
    service = AdminImportReadService(FakeAdminDb(build_pending_row()))

    assert service.get_import_job_filter_metadata()["entity"] == "import_jobs"
    assert service.get_import_item_filter_metadata()["entity"] == "import_items"


def test_admin_read_service_preserves_denied_filter_metadata_acl_before_lookup() -> None:
    service = AdminReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminReadAccessDeniedError) as error:
        service.get_filter_metadata("users", actor=DENIED_ACTOR)

    assert error.value.detail == "Access denied"


def test_admin_read_service_enforces_user_dictionary_filter_acl_before_application_metadata() -> None:
    db = FakeAdminDb(build_pending_row())
    acl_permissions = _ActionAclPermissions({"dictionary/list_words"})
    db._acl_permissions_repository = acl_permissions
    metadata_called = False

    def fail_if_application_metadata_is_reached() -> dict:
        nonlocal metadata_called
        metadata_called = True
        raise AssertionError("application user_dictionary metadata should not be reached")

    db.get_admin_filter_metadata = fail_if_application_metadata_is_reached
    service = AdminReadService(db)

    with pytest.raises(AdminReadAccessDeniedError) as error:
        service.get_filter_metadata(
            "user_dictionary",
            actor={"telegram_user_id": 1, "acl_group_title": "metadata_reader"},
        )

    assert error.value.detail == "Access denied"
    assert acl_permissions.calls == [("metadata_reader", "dictionary/list_filters", "web_admin")]
    assert metadata_called is False


def test_admin_read_service_validates_filter_metadata_entity_before_acl() -> None:
    service = AdminReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminReadValidationError) as error:
        service.get_filter_metadata("billing", actor=DENIED_ACTOR)

    assert str(error.value.detail).startswith("entity_type must be one of:")


def test_admin_read_service_normalizes_filter_metadata_entity_before_dispatch() -> None:
    service = AdminReadService(FakeAdminDb(build_pending_row()))
    service.user_read_service.get_filter_metadata = lambda: {"entity": "users"}

    result = service.get_filter_metadata(" users ", actor=ACTOR)

    assert result["entity"] == "users"


def test_admin_read_service_raises_service_error_for_unknown_filter_metadata_dispatch(monkeypatch) -> None:
    service = AdminReadService(FakeAdminDb(build_pending_row()))
    monkeypatch.setattr(
        "app.application.admin.read.read_service.filter_metadata_entity_and_action",
        lambda entity_type: ("unknown", "users/list_filters"),
    )

    with pytest.raises(AdminReadUnknownEntityError) as error:
        service.get_filter_metadata("users", actor=ACTOR)

    assert error.value.detail == "Unknown entity"


def test_admin_user_read_service_lists_users_with_normalized_pagination() -> None:
    db = FakeAdminDb(build_pending_row())
    db.admin_users = [
        {
            "user_id": "11111111-1111-4111-8111-111111111111",
            "telegram_user_id": 1,
            "username": "admin",
            "acl_group_title": "super_admin",
            "status": "active",
        }
    ]
    db.ai_usage_sessions = [
        {
            "actor_user_uuid": "11111111-1111-4111-8111-111111111111",
            "estimated_cost_usd": "0.25",
            "request_count": 2,
            "total_tokens": 100,
        }
    ]
    service = AdminUserReadService(db)

    result = service.list_users(
        actor=ACTOR,
        params={"page": "2", "page_size": "100", "search": " adm ", "user_type": "admin"},
    )

    assert result["page"] == 2
    assert result["page_size"] == 100
    assert [item["telegram_user_id"] for item in result["items"]] == [1]
    assert result["items"][0]["ai_usage_summary"]["estimated_cost_usd"] == "0.25"


def test_admin_user_read_service_rejects_invalid_pagination() -> None:
    service = AdminUserReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminUserReadValidationError) as error:
        service.list_users(actor=ACTOR, params={"page": "1", "page_size": "25"})

    assert "page_size" in error.value.detail


def test_admin_user_read_service_rejects_unknown_user_type() -> None:
    service = AdminUserReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminUserReadValidationError) as error:
        service.list_users(actor=ACTOR, params={"user_type": "ghost"})

    assert "user_type" in error.value.detail


def test_admin_user_read_service_rejects_invalid_user_id_filter() -> None:
    service = AdminUserReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminUserReadValidationError) as error:
        service.list_users(actor=ACTOR, params={"user_id": "not-a-uuid"})

    assert error.value.detail == "user_id must be a valid UUID"


def test_admin_user_read_service_rejects_missing_user_detail() -> None:
    service = AdminUserReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminUserReadNotFoundError) as error:
        service.get_user_detail(actor={"telegram_user_id": 1, "acl_group_title": "admin"}, user_id=404)

    assert error.value.detail == "User not found"


def test_admin_user_read_service_preserves_denied_list_acl_detail_before_validation() -> None:
    service = AdminUserReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminUserReadAccessDeniedError) as error:
        service.list_users(actor=DENIED_ACTOR, params={"user_type": "ghost"})

    assert error.value.detail == "Access denied"


def test_admin_user_read_service_preserves_denied_login_history_acl_before_lookup() -> None:
    db = FakeAdminDb(build_pending_row())
    service = AdminUserReadService(db)

    def fail_lookup(*args: object, **kwargs: object) -> list[dict[str, object]]:
        raise AssertionError("login history lookup should not run before ACL")

    db.web_login_history.list_latest_for_user = fail_lookup

    with pytest.raises(AdminUserReadAccessDeniedError) as error:
        service.list_latest_login_history_for_user(actor=DENIED_ACTOR, user_id="1", limit=10)

    assert error.value.detail == "Access denied"


def test_admin_log_read_service_lists_login_history_with_normalized_pagination() -> None:
    db = FakeAdminDb(build_pending_row())
    db.web_login_history = [
        {"id": 1, "telegram_user_id": 1, "result": "success", "api_origin": "https://cronolex.local"},
    ]
    service = AdminLogReadService(db)

    result = service.list_login_history(
        actor=ACTOR,
        params={"page": "2", "page_size": "100", "api_origin": " cronolex "},
    )

    assert result["page"] == 2
    assert result["page_size"] == 100
    assert [item["id"] for item in result["items"]] == [1]


def test_admin_log_read_service_lists_error_logs_with_search() -> None:
    db = FakeAdminDb(build_pending_row())
    db.error_logs = [{"id": 1, "level": "warn", "text": "Task failed"}]
    service = AdminLogReadService(db)

    result = service.list_error_logs(
        actor=ACTOR,
        params={"page": "1", "page_size": "50", "level": ["warn"], "search": " task "},
    )

    assert [item["id"] for item in result["items"]] == [1]


@pytest.mark.parametrize("mode", ["login_history", "task_logs", "error_logs"])
def test_admin_log_read_service_rejects_invalid_pagination(mode: str) -> None:
    service = AdminLogReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminLogReadValidationError) as error:
        if mode == "login_history":
            service.list_login_history(actor=ACTOR, params={"page": "1", "page_size": "25"})
        elif mode == "task_logs":
            service.list_task_logs(actor=ACTOR, params={"page": "1", "page_size": "25"})
        else:
            service.list_error_logs(actor=ACTOR, params={"page": "1", "page_size": "25"})

    assert "page_size" in error.value.detail


def test_admin_log_read_service_validates_task_log_scope() -> None:
    service = AdminLogReadService(FakeAdminDb(build_pending_row()))

    result = service.list_task_logs(actor=ACTOR, params={"page": "1", "page_size": "50", "scope": "billing"})

    assert result["page"] == 1

    try:
        service.list_task_logs(actor=ACTOR, params={"page": "1", "page_size": "50", "scope": "mixed"})
    except AdminLogReadValidationError as error:
        assert "scope must be one of" in error.detail
    else:  # pragma: no cover
        raise AssertionError("AdminLogReadValidationError was expected")


def test_admin_log_read_service_validates_task_type_against_scope_reference() -> None:
    service = AdminLogReadService(FakeAdminDb(build_pending_row()))

    service.list_task_logs(
        actor=ACTOR,
        params={
            "page": "1",
            "page_size": "50",
            "scope": "operations",
            "task_type": ["post_upgrade_google_doc_rescan"],
        }
    )

    service.list_task_logs(
        actor=ACTOR,
        params={
            "page": "1",
            "page_size": "50",
            "scope": "billing",
            "task_type": ["billing_payment_reconciliation"],
        }
    )

    service.list_task_logs(
        actor=ACTOR,
        params={
            "page": "1",
            "page_size": "50",
            "scope": "billing",
            "task_type": ["billing_monobank_reconciliation"],
        }
    )

    for billing_task_type in ("billing_payment_reconciliation", "billing_monobank_reconciliation"):
        try:
            service.list_task_logs(
                actor=ACTOR,
                params={
                    "page": "1",
                    "page_size": "50",
                    "scope": "operations",
                    "task_type": [billing_task_type],
                }
            )
        except AdminLogReadValidationError as error:
            assert "task_type contains unsupported value" in error.detail
        else:  # pragma: no cover
            raise AssertionError("AdminLogReadValidationError was expected")


@pytest.mark.parametrize("mode", ["login_history", "task_logs", "error_logs"])
def test_admin_log_read_service_preserves_denied_acl_detail_before_validation(mode: str) -> None:
    service = AdminLogReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminLogReadAccessDeniedError) as error:
        if mode == "login_history":
            service.list_login_history(
                actor=DENIED_ACTOR,
                params={"page": "1", "page_size": "50", "result": ["invalid"]},
            )
        elif mode == "task_logs":
            service.list_task_logs(actor=DENIED_ACTOR, params={"page": "1", "page_size": "50", "scope": "mixed"})
        else:
            service.list_error_logs(actor=DENIED_ACTOR, params={"page": "1", "page_size": "50", "level": ["info"]})

    assert error.value.detail == "Access denied"


def test_admin_log_read_service_rejects_missing_task_log_detail() -> None:
    service = AdminLogReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminLogReadNotFoundError) as error:
        service.get_task_log_detail(actor={"telegram_user_id": 1, "acl_group_title": "admin"}, task_log_id=404)

    assert error.value.detail == "Task log not found"


def test_admin_log_read_service_validates_task_log_filter_metadata_scope() -> None:
    service = AdminLogReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminLogReadValidationError) as error:
        service.get_task_log_filter_metadata(params={"scope": "mixed"})

    assert "scope must be one of" in error.value.detail


def test_admin_read_service_maps_task_log_filter_metadata_validation_error() -> None:
    service = AdminReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminReadValidationError) as error:
        service.get_filter_metadata("task_logs", actor=ACTOR, params={"scope": "mixed"})

    assert "scope must be one of" in error.value.detail


def test_admin_read_service_rejects_non_admin_actor() -> None:
    service = AdminReadService(FakeAdminDb(build_pending_row()))

    with pytest.raises(AdminImportReadAccessDeniedError) as error:
        service.list_import_jobs(
            actor={"telegram_user_id": 1, "acl_group_title": "user"},
            params={"page": 1, "page_size": 50},
        )

    assert error.value.detail == "Import jobs access is not allowed"
