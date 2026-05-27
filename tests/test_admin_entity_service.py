from __future__ import annotations

import pytest

from app.application.admin.dictionary.errors import (
    AdminDictionaryActionAccessDeniedError,
    AdminDictionaryActionAssignedEntryError,
    AdminDictionaryActionEntityNotFoundError,
)
from app.application.admin.entity.entity_service import AdminEntityService
from app.application.admin.entity.errors import (
    AdminEntityAccessDeniedError,
    AdminEntityConflictError,
    AdminEntityInvalidIdError,
    AdminEntityNotFoundError,
    AdminEntityValidationError,
)
from app.application.admin.users.errors import (
    AdminUserActionAccessDeniedError,
    AdminUserActionNotFoundError,
)


class FakeUserActionService:
    def __init__(self) -> None:
        self.archive_calls: list[dict] = []
        self.delete_calls: list[dict] = []

    def archive(self, *, actor: dict, user_id: str) -> dict[str, str]:
        self.archive_calls.append({"actor": actor, "user_id": user_id})
        return {"status": "archived"}

    def delete(self, *, actor: dict, user_id: str) -> dict[str, str]:
        self.delete_calls.append({"actor": actor, "user_id": user_id})
        return {"status": "deleted"}


class FakeDictionaryActionService:
    def __init__(self) -> None:
        self.archive_calls: list[dict] = []
        self.delete_calls: list[dict] = []

    def archive_entry(self, *, actor: dict, entry_id: int) -> dict[str, str]:
        self.archive_calls.append({"actor": actor, "entry_id": entry_id})
        return {"status": "archived"}

    def delete_entry(self, *, actor: dict, entry_id: int) -> dict[str, str]:
        self.delete_calls.append({"actor": actor, "entry_id": entry_id})
        return {"status": "deleted"}


class MissingDictionaryActionService(FakeDictionaryActionService):
    def archive_entry(self, *, actor: dict, entry_id: int) -> dict[str, str]:
        self.archive_calls.append({"actor": actor, "entry_id": entry_id})
        raise AdminDictionaryActionEntityNotFoundError()


class AssignedDictionaryActionService(FakeDictionaryActionService):
    def delete_entry(self, *, actor: dict, entry_id: int) -> dict[str, str]:
        self.delete_calls.append({"actor": actor, "entry_id": entry_id})
        raise AdminDictionaryActionAssignedEntryError()


class AccessDeniedDictionaryActionService(FakeDictionaryActionService):
    def delete_entry(self, *, actor: dict, entry_id: int) -> dict[str, str]:
        self.delete_calls.append({"actor": actor, "entry_id": entry_id})
        raise AdminDictionaryActionAccessDeniedError("Delete is not allowed")


class MissingUserActionService(FakeUserActionService):
    def archive(self, *, actor: dict, user_id: str) -> dict[str, str]:
        self.archive_calls.append({"actor": actor, "user_id": user_id})
        raise AdminUserActionNotFoundError("Entity not found")


class AccessDeniedUserActionService(FakeUserActionService):
    def delete(self, *, actor: dict, user_id: str) -> dict[str, str]:
        self.delete_calls.append({"actor": actor, "user_id": user_id})
        raise AdminUserActionAccessDeniedError("Delete is not allowed")


def build_service(
    dictionary_actions: FakeDictionaryActionService | None = None,
    *,
    user_actions: FakeUserActionService | None = None,
) -> tuple[AdminEntityService, FakeUserActionService, FakeDictionaryActionService]:
    user_actions = user_actions or FakeUserActionService()
    dictionary_actions = dictionary_actions or FakeDictionaryActionService()
    return (
        AdminEntityService(
            user_action_service=user_actions,
            dictionary_action_service=dictionary_actions,
        ),
        user_actions,
        dictionary_actions,
    )


def test_filter_metadata_action_maps_known_entities() -> None:
    service, _user_actions, _dictionary_actions = build_service()

    assert service.filter_metadata_action("dictionary") == "dictionary/list_filters"
    assert service.filter_metadata_action("users") == "users/list_filters"
    assert service.filter_metadata_action("task_logs") == "logs/list_task_log_filters"
    assert service.filter_metadata_action("error_log") == "logs/list_error_log_filters"
    assert service.filter_metadata_action("import_jobs") == "imports/list_job_filters"
    assert service.filter_metadata_action("import_items") == "imports/list_item_filters"
    assert service.filter_metadata_action("user_dictionary") == "dictionary/list_filters"


def test_filter_metadata_action_rejects_unknown_entity() -> None:
    service, _user_actions, _dictionary_actions = build_service()

    with pytest.raises(AdminEntityValidationError) as error:
        service.filter_metadata_action("billing")

    assert str(error.value.detail).startswith("entity_type must be one of:")


def test_archive_entity_delegates_user_archive() -> None:
    service, user_actions, dictionary_actions = build_service()
    actor = {"telegram_user_id": 1}

    result = service.archive_entity(actor=actor, entity_type="users", entity_id="42")

    assert result == {"status": "archived"}
    assert user_actions.archive_calls == [{"actor": actor, "user_id": "42"}]
    assert dictionary_actions.archive_calls == []


def test_delete_entity_delegates_dictionary_delete_with_integer_id() -> None:
    service, user_actions, dictionary_actions = build_service()
    actor = {"telegram_user_id": 1}

    result = service.delete_entity(actor=actor, entity_type="dictionary", entity_id="12")

    assert result == {"status": "deleted"}
    assert dictionary_actions.delete_calls == [{"actor": actor, "entry_id": 12}]
    assert user_actions.delete_calls == []


def test_dictionary_entity_rejects_non_integer_id() -> None:
    service, _user_actions, _dictionary_actions = build_service()

    with pytest.raises(AdminEntityInvalidIdError) as error:
        service.archive_entity(actor={"telegram_user_id": 1}, entity_type="dictionary", entity_id="abc")

    assert error.value.detail == "entity_id must be an integer"


def test_dictionary_entity_maps_action_not_found_errors() -> None:
    service, _user_actions, dictionary_actions = build_service(MissingDictionaryActionService())
    actor = {"telegram_user_id": 1}

    with pytest.raises(AdminEntityNotFoundError) as error:
        service.archive_entity(actor=actor, entity_type="dictionary", entity_id="12")

    assert error.value.detail == "Entity not found"
    assert dictionary_actions.archive_calls == [{"actor": actor, "entry_id": 12}]


def test_user_entity_maps_action_not_found_errors() -> None:
    service, user_actions, _dictionary_actions = build_service(user_actions=MissingUserActionService())
    actor = {"telegram_user_id": 1}

    with pytest.raises(AdminEntityNotFoundError) as error:
        service.archive_entity(actor=actor, entity_type="users", entity_id="42")

    assert error.value.detail == "Entity not found"
    assert user_actions.archive_calls == [{"actor": actor, "user_id": "42"}]


def test_dictionary_entity_maps_action_conflict_errors() -> None:
    service, _user_actions, dictionary_actions = build_service(AssignedDictionaryActionService())
    actor = {"telegram_user_id": 1}

    with pytest.raises(AdminEntityConflictError) as error:
        service.delete_entity(actor=actor, entity_type="dictionary", entity_id="12")

    assert error.value.detail == "Dictionary entry is assigned to users and cannot be deleted"
    assert dictionary_actions.delete_calls == [{"actor": actor, "entry_id": 12}]


def test_dictionary_entity_maps_action_access_denied_errors() -> None:
    service, _user_actions, dictionary_actions = build_service(AccessDeniedDictionaryActionService())
    actor = {"telegram_user_id": 1}

    with pytest.raises(AdminEntityAccessDeniedError) as error:
        service.delete_entity(actor=actor, entity_type="dictionary", entity_id="12")

    assert error.value.detail == "Delete is not allowed"
    assert dictionary_actions.delete_calls == [{"actor": actor, "entry_id": 12}]


def test_user_entity_maps_action_access_denied_errors() -> None:
    service, user_actions, _dictionary_actions = build_service(user_actions=AccessDeniedUserActionService())
    actor = {"telegram_user_id": 1}

    with pytest.raises(AdminEntityAccessDeniedError) as error:
        service.delete_entity(actor=actor, entity_type="users", entity_id="42")

    assert error.value.detail == "Delete is not allowed"
    assert user_actions.delete_calls == [{"actor": actor, "user_id": "42"}]
