from __future__ import annotations

from collections.abc import Callable
from typing import Any, ParamSpec, Protocol, TypeVar

import app.validation.pagination as validation_pagination
import app.validation.request_values as request_values
from app.acl.processor import AclPermissionReader
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)
from app.application.admin.user_dictionary.errors import (
    AdminUserDictionaryReadAccessDeniedError,
    AdminUserDictionaryReadAudioNotFoundError,
    AdminUserDictionaryReadEntryNotFoundError,
    AdminUserDictionaryReadLevelIdFilterError,
    AdminUserDictionaryReadValidationError,
)

DEFAULT_PAGE_SIZE = 50
ALLOWED_PAGE_SIZES = {50, 100}
P = ParamSpec("P")
T = TypeVar("T")


class AdminUserDictionaryReadRepositoryPort(Protocol):
    def get_admin_filter_metadata(self) -> dict[str, Any]: ...

    def list_admin_entries(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def get_admin_entry_detail(self, entry_id: int) -> dict[str, Any] | None: ...

    def get_entry_audio(self, entry_id: int) -> dict[str, Any] | None: ...


class AdminUserDictionaryReadDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    user_dictionary: AdminUserDictionaryReadRepositoryPort


class AdminUserDictionaryReadService:
    def __init__(self, db: AdminUserDictionaryReadDatabasePort) -> None:
        self.db = db

    def list_entries(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        self._require_admin_access(
            actor,
            action="dictionary/list_words",
            detail="User dictionary access is not allowed",
        )
        page, page_size = _user_dictionary_read_validation(
            validation_pagination.normalize_pagination,
            params,
            default_page_size=DEFAULT_PAGE_SIZE,
            allowed_page_sizes=ALLOWED_PAGE_SIZES,
        )
        metadata = self.db.user_dictionary.get_admin_filter_metadata()
        return self.db.user_dictionary.list_admin_entries(
            page=page,
            page_size=page_size,
            search=_user_dictionary_read_validation(
                request_values.ensure_text,
                params.get("search"),
                "search",
                max_length=120,
            ),
            status=_user_dictionary_read_validation(
                request_values.validate_filter_metadata_values,
                metadata,
                "status",
                params.get("status"),
            ),
            part_of_speech=_user_dictionary_read_validation(
                request_values.validate_filter_metadata_values,
                metadata,
                "part_of_speech",
                params.get("part_of_speech"),
            ),
            level_id=validate_level_ids(
                _user_dictionary_read_validation(
                    request_values.validate_filter_metadata_values,
                    metadata,
                    "level_id",
                    params.get("level_id"),
                )
            ),
        )

    def get_entry_detail(self, *, actor: dict[str, Any], entry_id: int) -> dict[str, Any]:
        self._require_admin_access(
            actor,
            action="dictionary/list_words",
            detail="User dictionary access is not allowed",
        )
        entry = self.db.user_dictionary.get_admin_entry_detail(entry_id)
        if entry is None:
            raise AdminUserDictionaryReadEntryNotFoundError()
        return {"entry": entry}

    def get_audio_path(self, *, actor: dict[str, Any], entry_id: int) -> str | None:
        self._require_admin_access(actor, action="dictionary/play_audio")
        entry = self.db.user_dictionary.get_entry_audio(entry_id)
        if entry is None:
            raise AdminUserDictionaryReadAudioNotFoundError()
        return entry.get("audio_path")

    def get_filter_metadata(self, *, actor: dict[str, Any]) -> dict[str, Any]:
        self._require_admin_access(
            actor,
            action="dictionary/list_words",
            detail="User dictionary filters access is not allowed",
        )
        return self.db.user_dictionary.get_admin_filter_metadata()

    def _require_admin_access(self, actor: dict[str, Any], *, action: str, detail: str = "Access denied") -> None:
        try:
            require_admin_access_allowed(self.db, actor, action=action, detail=detail)
        except AdminPermissionDeniedError as error:
            raise AdminUserDictionaryReadAccessDeniedError(error.detail) from error


def validate_level_ids(values: Any) -> list[int]:
    if values is None:
        return []
    raw_values = values if isinstance(values, list) else [values]
    normalized: list[int] = []
    for value in raw_values:
        try:
            level_id = int(value)
        except (TypeError, ValueError) as error:
            raise AdminUserDictionaryReadLevelIdFilterError() from error
        if level_id not in normalized:
            normalized.append(level_id)
    return normalized


def _user_dictionary_read_validation(validator: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        return validator(*args, **kwargs)
    except request_values.RequestValueValidationError as error:
        raise AdminUserDictionaryReadValidationError(error.detail) from error
