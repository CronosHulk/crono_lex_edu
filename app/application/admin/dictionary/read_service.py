from __future__ import annotations

from collections.abc import Callable
from typing import Any, ParamSpec, Protocol, TypeVar

import app.validation.pagination as validation_pagination
import app.validation.request_values as request_values
from app.acl.processor import AclPermissionReader
from app.application.admin.dictionary.errors import (
    AdminDictionaryReadAccessDeniedError,
    AdminDictionaryReadEntryNotFoundError,
    AdminDictionaryReadValidationError,
    AdminDictionaryReadVerifiedFilterError,
)
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)

DEFAULT_PAGE_SIZE = 50
ALLOWED_PAGE_SIZES = {50, 100}
ALLOWED_VERIFIED_FILTERS = {"all", "verified", "unverified"}
P = ParamSpec("P")
T = TypeVar("T")


class AdminDictionaryReadRepositoryPort(Protocol):
    def get_filter_metadata(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def list_entries(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def get_entry(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None: ...


class AdminDictionaryReadDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    admin_dictionary: AdminDictionaryReadRepositoryPort


class AdminDictionaryReadService:
    def __init__(self, db: AdminDictionaryReadDatabasePort) -> None:
        self.db = db

    def list_dictionary_entries(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        self._require_admin_access(actor, action="dictionary/list_words")
        page, page_size = _dictionary_read_validation(
            validation_pagination.normalize_pagination,
            params,
            default_page_size=DEFAULT_PAGE_SIZE,
            allowed_page_sizes=ALLOWED_PAGE_SIZES,
        )
        metadata = self.db.admin_dictionary.get_filter_metadata()
        return self.db.admin_dictionary.list_entries(
            page=page,
            page_size=page_size,
            archived=str(params.get("archived") or "false").lower() == "true",
            search=_dictionary_read_validation(
                request_values.ensure_text,
                params.get("search"),
                "search",
                max_length=120,
            ),
            entry_type=_dictionary_read_validation(
                request_values.validate_filter_metadata_values,
                metadata,
                "entry_type",
                params.get("entry_type"),
            ),
            part_of_speech=_dictionary_read_validation(
                request_values.validate_filter_metadata_values,
                metadata,
                "part_of_speech",
                params.get("part_of_speech"),
            ),
            category=_dictionary_read_validation(
                request_values.validate_filter_metadata_values,
                metadata,
                "category",
                params.get("category"),
            ),
            verified=validate_dictionary_verified_filter(params.get("verified")),
        )

    def get_dictionary_entry(self, *, actor: dict[str, Any], entry_id: int) -> dict[str, Any]:
        self._require_admin_access(actor, action="dictionary/view_word")
        entry = self.db.admin_dictionary.get_entry(entry_id)
        if entry is None:
            raise AdminDictionaryReadEntryNotFoundError()
        return entry

    def get_filter_metadata(self) -> dict[str, Any]:
        return self.db.admin_dictionary.get_filter_metadata()

    def _require_admin_access(self, actor: dict[str, Any], *, action: str, detail: str = "Access denied") -> None:
        try:
            require_admin_access_allowed(self.db, actor, action=action, detail=detail)
        except AdminPermissionDeniedError as error:
            raise AdminDictionaryReadAccessDeniedError(error.detail) from error


def validate_dictionary_verified_filter(value: Any) -> str | None:
    if value in (None, "", "all"):
        return None
    normalized = _dictionary_read_validation(request_values.ensure_text, value, "verified", max_length=32)
    if normalized not in ALLOWED_VERIFIED_FILTERS:
        raise AdminDictionaryReadVerifiedFilterError()
    return normalized


def _dictionary_read_validation(validator: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        return validator(*args, **kwargs)
    except request_values.RequestValueValidationError as error:
        raise AdminDictionaryReadValidationError(error.detail) from error
