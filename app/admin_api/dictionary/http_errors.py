from __future__ import annotations

from fastapi import HTTPException

from app.application.admin.dictionary.errors import (
    AdminDictionaryActionAccessDeniedError,
    AdminDictionaryActionConflictError,
    AdminDictionaryActionError,
    AdminDictionaryActionNotFoundError,
    AdminDictionaryReadAccessDeniedError,
    AdminDictionaryReadError,
    AdminDictionaryReadNotFoundError,
    AdminDictionaryReadValidationError,
    AdminDictionaryServiceAccessDeniedError,
    AdminDictionaryServiceError,
    AdminDictionaryServiceNotFoundError,
    AdminDictionaryServiceValidationError,
)


def admin_dictionary_read_http_exception(error: AdminDictionaryReadError) -> HTTPException:
    return HTTPException(status_code=admin_dictionary_read_error_status_code(error), detail=error.detail)


def admin_dictionary_service_http_exception(error: AdminDictionaryServiceError) -> HTTPException:
    return HTTPException(status_code=admin_dictionary_service_error_status_code(error), detail=error.detail)


def admin_dictionary_action_http_exception(error: AdminDictionaryActionError) -> HTTPException:
    return HTTPException(status_code=admin_dictionary_action_error_status_code(error), detail=error.detail)


def admin_dictionary_read_error_status_code(error: AdminDictionaryReadError) -> int:
    if isinstance(error, AdminDictionaryReadAccessDeniedError):
        return 403
    if isinstance(error, AdminDictionaryReadNotFoundError):
        return 404
    if isinstance(error, AdminDictionaryReadValidationError):
        return 422
    return 400


def admin_dictionary_service_error_status_code(error: AdminDictionaryServiceError) -> int:
    if isinstance(error, AdminDictionaryServiceAccessDeniedError):
        return 403
    if isinstance(error, AdminDictionaryServiceNotFoundError):
        return 404
    if isinstance(error, AdminDictionaryServiceValidationError):
        return 400
    return 400


def admin_dictionary_action_error_status_code(error: AdminDictionaryActionError) -> int:
    if isinstance(error, AdminDictionaryActionAccessDeniedError):
        return 403
    if isinstance(error, AdminDictionaryActionNotFoundError):
        return 404
    if isinstance(error, AdminDictionaryActionConflictError):
        return 409
    return 400
