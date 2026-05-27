from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec, Protocol, TypeVar

import app.validation.request_values as request_values
from app.application.admin.dictionary.errors import (
    AdminDictionaryActionAccessDeniedError,
    AdminDictionaryActionConflictError,
    AdminDictionaryActionError,
    AdminDictionaryActionNotFoundError,
)
from app.application.admin.entity.errors import (
    AdminEntityAccessDeniedError,
    AdminEntityConflictError,
    AdminEntityError,
    AdminEntityInvalidIdError,
    AdminEntityNotFoundError,
    AdminEntityUnknownError,
    AdminEntityValidationError,
)
from app.application.admin.users.errors import (
    AdminUserActionAccessDeniedError,
    AdminUserActionError,
    AdminUserActionNotFoundError,
)

ADMIN_FILTER_METADATA_ENTITIES = {
    "dictionary",
    "users",
    "task_logs",
    "error_log",
    "import_jobs",
    "import_items",
    "user_dictionary",
}
ADMIN_MUTABLE_ENTITIES = {"dictionary", "users"}
P = ParamSpec("P")
T = TypeVar("T")


class _UserActionService(Protocol):
    def archive(self, *, actor: dict, user_id: str) -> dict[str, str]: ...

    def delete(self, *, actor: dict, user_id: str) -> dict[str, str]: ...


class _DictionaryActionService(Protocol):
    def archive_entry(self, *, actor: dict, entry_id: int) -> dict[str, str]: ...

    def delete_entry(self, *, actor: dict, entry_id: int) -> dict[str, str]: ...


class AdminEntityService:
    def __init__(
        self,
        *,
        user_action_service: _UserActionService,
        dictionary_action_service: _DictionaryActionService,
    ) -> None:
        self.user_action_service = user_action_service
        self.dictionary_action_service = dictionary_action_service

    def filter_metadata_action(self, entity_type: str) -> str:
        return filter_metadata_action_for_entity(entity_type)

    def archive_entity(self, *, actor: dict, entity_type: str, entity_id: str) -> dict[str, str]:
        entity_type = _admin_entity_validation(
            request_values.ensure_allowed_value,
            entity_type,
            ADMIN_MUTABLE_ENTITIES,
            "entity_type",
        )
        if entity_type == "users":
            try:
                return self.user_action_service.archive(actor=actor, user_id=entity_id)
            except AdminUserActionError as error:
                raise _admin_entity_error_from_user_action_error(error) from error
        if entity_type == "dictionary":
            try:
                return self.dictionary_action_service.archive_entry(actor=actor, entry_id=_parse_entity_int_id(entity_id))
            except AdminDictionaryActionError as error:
                raise _admin_entity_error_from_dictionary_action_error(error) from error
        raise AdminEntityUnknownError()

    def delete_entity(self, *, actor: dict, entity_type: str, entity_id: str) -> dict[str, str]:
        entity_type = _admin_entity_validation(
            request_values.ensure_allowed_value,
            entity_type,
            ADMIN_MUTABLE_ENTITIES,
            "entity_type",
        )
        if entity_type == "users":
            try:
                return self.user_action_service.delete(actor=actor, user_id=entity_id)
            except AdminUserActionError as error:
                raise _admin_entity_error_from_user_action_error(error) from error
        if entity_type == "dictionary":
            try:
                return self.dictionary_action_service.delete_entry(actor=actor, entry_id=_parse_entity_int_id(entity_id))
            except AdminDictionaryActionError as error:
                raise _admin_entity_error_from_dictionary_action_error(error) from error
        raise AdminEntityUnknownError()


def _parse_entity_int_id(entity_id: str) -> int:
    try:
        return int(entity_id)
    except (TypeError, ValueError) as error:
        raise AdminEntityInvalidIdError() from error


def _admin_entity_error_from_dictionary_action_error(error: AdminDictionaryActionError) -> AdminEntityError:
    if isinstance(error, AdminDictionaryActionAccessDeniedError):
        return AdminEntityAccessDeniedError(error.detail)
    if isinstance(error, AdminDictionaryActionNotFoundError):
        return AdminEntityNotFoundError(error.detail)
    if isinstance(error, AdminDictionaryActionConflictError):
        return AdminEntityConflictError(error.detail)
    return AdminEntityError(error.detail)


def _admin_entity_error_from_user_action_error(error: AdminUserActionError) -> AdminEntityError:
    if isinstance(error, AdminUserActionAccessDeniedError):
        return AdminEntityAccessDeniedError(error.detail)
    if isinstance(error, AdminUserActionNotFoundError):
        return AdminEntityNotFoundError(error.detail)
    return AdminEntityError(error.detail)


def filter_metadata_entity_and_action(entity_type: str) -> tuple[str, str]:
    entity_type = _admin_entity_validation(
        request_values.ensure_allowed_value,
        entity_type,
        ADMIN_FILTER_METADATA_ENTITIES,
        "entity_type",
    )
    return entity_type, _filter_metadata_action_for_normalized_entity(entity_type)


def filter_metadata_action_for_entity(entity_type: str) -> str:
    entity_type, action = filter_metadata_entity_and_action(entity_type)
    return action


def _filter_metadata_action_for_normalized_entity(entity_type: str) -> str:
    if entity_type == "dictionary":
        return "dictionary/list_filters"
    if entity_type == "users":
        return "users/list_filters"
    if entity_type == "task_logs":
        return "logs/list_task_log_filters"
    if entity_type == "error_log":
        return "logs/list_error_log_filters"
    if entity_type == "import_jobs":
        return "imports/list_job_filters"
    if entity_type == "import_items":
        return "imports/list_item_filters"
    if entity_type == "user_dictionary":
        return "dictionary/list_filters"
    return "unknown"


def _admin_entity_validation(validator: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        return validator(*args, **kwargs)
    except request_values.RequestValueValidationError as error:
        raise AdminEntityValidationError(error.detail) from error
