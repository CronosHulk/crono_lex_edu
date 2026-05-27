from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.client_api.internal_auth import build_internal_api_guard
from app.security.internal_api_tokens import (
    InternalApiTokenNotConfiguredError,
    InvalidInternalApiTokenError,
    read_internal_api_token,
    validate_internal_api_token,
)


def test_read_internal_api_token_normalizes_configured_token() -> None:
    service = SimpleNamespace(db=SimpleNamespace(settings=SimpleNamespace(app_internal_api_token=" internal ")))

    assert read_internal_api_token(service) == "internal"


def test_validate_internal_api_token_accepts_matching_token() -> None:
    assert validate_internal_api_token(expected="internal", token="internal") is None


def test_validate_internal_api_token_rejects_missing_configuration() -> None:
    with pytest.raises(InternalApiTokenNotConfiguredError) as error:
        validate_internal_api_token(expected="", token="internal")

    assert error.value.status_code == 503
    assert error.value.detail == "Internal API token is not configured"


@pytest.mark.parametrize("token", [None, "", "wrong"])
def test_validate_internal_api_token_rejects_invalid_token(token: str | None) -> None:
    with pytest.raises(InvalidInternalApiTokenError) as error:
        validate_internal_api_token(expected="internal", token=token)

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid internal API token"


def test_internal_api_guard_maps_missing_configuration_to_http_error() -> None:
    guard = build_internal_api_guard(_service_with_token(""))

    with pytest.raises(HTTPException) as error:
        guard("internal")

    assert error.value.status_code == 503
    assert error.value.detail == "Internal API token is not configured"


def test_internal_api_guard_maps_invalid_token_to_http_error() -> None:
    guard = build_internal_api_guard(_service_with_token("internal"))

    with pytest.raises(HTTPException) as error:
        guard("wrong")

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid internal API token"


def test_internal_api_guard_accepts_matching_token() -> None:
    guard = build_internal_api_guard(_service_with_token("internal"))

    assert guard("internal") is None


def _service_with_token(token: str) -> SimpleNamespace:
    return SimpleNamespace(db=SimpleNamespace(settings=SimpleNamespace(app_internal_api_token=token)))
