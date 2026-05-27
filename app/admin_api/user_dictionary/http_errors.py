from __future__ import annotations

from fastapi import HTTPException

from app.application.admin.user_dictionary.errors import (
    AdminUserDictionaryActionAccessDeniedError,
    AdminUserDictionaryActionError,
    AdminUserDictionaryActionNotFoundError,
    AdminUserDictionaryReadAccessDeniedError,
    AdminUserDictionaryReadError,
    AdminUserDictionaryReadNotFoundError,
    AdminUserDictionaryReadValidationError,
)


def admin_user_dictionary_read_http_exception(error: AdminUserDictionaryReadError) -> HTTPException:
    return HTTPException(status_code=admin_user_dictionary_read_error_status_code(error), detail=error.detail)


def admin_user_dictionary_action_http_exception(error: AdminUserDictionaryActionError) -> HTTPException:
    return HTTPException(status_code=admin_user_dictionary_action_error_status_code(error), detail=error.detail)


def admin_user_dictionary_read_error_status_code(error: AdminUserDictionaryReadError) -> int:
    if isinstance(error, AdminUserDictionaryReadAccessDeniedError):
        return 403
    if isinstance(error, AdminUserDictionaryReadNotFoundError):
        return 404
    if isinstance(error, AdminUserDictionaryReadValidationError):
        return 422
    return 400


def admin_user_dictionary_action_error_status_code(error: AdminUserDictionaryActionError) -> int:
    if isinstance(error, AdminUserDictionaryActionAccessDeniedError):
        return 403
    if isinstance(error, AdminUserDictionaryActionNotFoundError):
        return 404
    return 400
