from __future__ import annotations

from typing import Any, Protocol

from app.application.admin.dictionary.read_service import (
    AdminDictionaryReadDatabasePort,
    AdminDictionaryReadService,
)
from app.application.admin.entity.entity_service import filter_metadata_entity_and_action
from app.application.admin.entity.errors import AdminEntityValidationError
from app.application.admin.imports.read_service import (
    AdminImportReadDatabasePort,
    AdminImportReadService,
)
from app.application.admin.logs.errors import AdminLogReadValidationError
from app.application.admin.logs.read_service import AdminLogReadDatabasePort, AdminLogReadService
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)
from app.application.admin.read.errors import (
    AdminReadAccessDeniedError,
    AdminReadError,
    AdminReadUnknownEntityError,
    AdminReadValidationError,
)
from app.application.admin.user_dictionary.errors import (
    AdminUserDictionaryReadAccessDeniedError,
    AdminUserDictionaryReadError,
    AdminUserDictionaryReadValidationError,
)
from app.application.admin.user_dictionary.read_service import (
    AdminUserDictionaryReadDatabasePort,
    AdminUserDictionaryReadService,
)
from app.application.admin.users.read_service import (
    AdminUserReadDatabasePort,
    AdminUserReadService,
)


class AdminReadDatabasePort(
    AdminDictionaryReadDatabasePort,
    AdminImportReadDatabasePort,
    AdminLogReadDatabasePort,
    AdminUserDictionaryReadDatabasePort,
    AdminUserReadDatabasePort,
    Protocol,
):
    pass


class AdminReadService:
    def __init__(self, db: AdminReadDatabasePort) -> None:
        self.db = db
        self.dictionary_read_service = AdminDictionaryReadService(db)
        self.import_read_service = AdminImportReadService(db)
        self.log_read_service = AdminLogReadService(db)
        self.user_dictionary_read_service = AdminUserDictionaryReadService(db)
        self.user_read_service = AdminUserReadService(db)

    def list_dictionary_entries(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        return self.dictionary_read_service.list_dictionary_entries(actor=actor, params=params)

    def get_dictionary_entry(self, *, actor: dict[str, Any], entry_id: int) -> dict[str, Any]:
        return self.dictionary_read_service.get_dictionary_entry(actor=actor, entry_id=entry_id)

    def get_filter_metadata(
        self,
        entity_type: str,
        *,
        actor: dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            entity_type, action = filter_metadata_entity_and_action(entity_type)
        except AdminEntityValidationError as error:
            raise AdminReadValidationError(error.detail) from error
        self._require_admin_access(actor, action=action)
        if entity_type == "user_dictionary":
            try:
                return self.user_dictionary_read_service.get_filter_metadata(actor=actor)
            except AdminUserDictionaryReadError as error:
                raise _admin_read_error_from_user_dictionary_read_error(error) from error
        if entity_type == "dictionary":
            return self.dictionary_read_service.get_filter_metadata()
        if entity_type == "users":
            return self.user_read_service.get_filter_metadata()
        if entity_type == "task_logs":
            try:
                return self.log_read_service.get_task_log_filter_metadata(params=params)
            except AdminLogReadValidationError as error:
                raise AdminReadValidationError(error.detail) from error
        if entity_type == "error_log":
            return self.log_read_service.get_error_log_filter_metadata()
        if entity_type == "import_jobs":
            return self.import_read_service.get_import_job_filter_metadata()
        if entity_type == "import_items":
            return self.import_read_service.get_import_item_filter_metadata()
        raise AdminReadUnknownEntityError()

    def list_users(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        return self.user_read_service.list_users(actor=actor, params=params)

    def list_latest_login_history_for_user(self, *, actor: dict[str, Any], user_id: int, limit: int = 10) -> dict[str, Any]:
        return self.user_read_service.list_latest_login_history_for_user(actor=actor, user_id=user_id, limit=limit)

    def get_user_detail(self, *, actor: dict[str, Any], user_id: int) -> dict[str, Any]:
        return self.user_read_service.get_user_detail(actor=actor, user_id=user_id)

    def list_login_history(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        return self.log_read_service.list_login_history(actor=actor, params=params)

    def list_task_logs(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        return self.log_read_service.list_task_logs(actor=actor, params=params)

    def list_import_jobs(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        return self.import_read_service.list_import_jobs(actor=actor, params=params)

    def list_import_items(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        return self.import_read_service.list_import_items(actor=actor, params=params)

    def list_user_dictionary_entries(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        return self.user_dictionary_read_service.list_entries(actor=actor, params=params)

    def get_user_dictionary_entry_detail(self, *, actor: dict[str, Any], entry_id: int) -> dict[str, Any]:
        return self.user_dictionary_read_service.get_entry_detail(actor=actor, entry_id=entry_id)

    def get_user_dictionary_audio_path(self, *, actor: dict[str, Any], entry_id: int) -> str:
        return self.user_dictionary_read_service.get_audio_path(actor=actor, entry_id=entry_id)

    def get_task_log_detail(self, *, actor: dict[str, Any], task_log_id: int) -> dict[str, Any]:
        return self.log_read_service.get_task_log_detail(actor=actor, task_log_id=task_log_id)

    def list_error_logs(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        return self.log_read_service.list_error_logs(actor=actor, params=params)

    def get_import_job_detail(self, *, actor: dict[str, Any], import_job_id: int) -> dict[str, Any]:
        return self.import_read_service.get_import_job_detail(actor=actor, import_job_id=import_job_id)

    def _require_admin_access(self, actor: dict[str, Any], *, action: str, detail: str = "Access denied") -> None:
        try:
            require_admin_access_allowed(self.db, actor, action=action, detail=detail)
        except AdminPermissionDeniedError as error:
            raise AdminReadAccessDeniedError(error.detail) from error


def _admin_read_error_from_user_dictionary_read_error(error: AdminUserDictionaryReadError) -> AdminReadError:
    if isinstance(error, AdminUserDictionaryReadAccessDeniedError):
        return AdminReadAccessDeniedError(error.detail)
    if isinstance(error, AdminUserDictionaryReadValidationError):
        return AdminReadValidationError(error.detail)
    return AdminReadError(error.detail)
