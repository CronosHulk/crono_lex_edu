from __future__ import annotations

from app.application.admin.user_dictionary.errors import (
    AdminUserDictionaryReadAccessDeniedError,
    AdminUserDictionaryReadAudioNotFoundError,
    AdminUserDictionaryReadEntryNotFoundError,
    AdminUserDictionaryReadLevelIdFilterError,
    AdminUserDictionaryReadValidationError,
)
from app.application.admin.user_dictionary.read_service import AdminUserDictionaryReadService


class FakeAclPermissionRepository:
    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None:
        admin_actions = {"dictionary/list_words", "dictionary/play_audio"}
        if group_title == "admin" and action in admin_actions and environment == "web_admin":
            return "enabled"
        return "disabled"

    def list_group_capabilities(self, *, group_title: str, environment: str) -> list[str]:
        if group_title == "admin" and environment == "web_admin":
            return ["dictionary/list_words", "dictionary/play_audio"]
        return []


class FakeUserDictionaryRepository:
    def __init__(self) -> None:
        self.list_params = None

    def get_admin_filter_metadata(self) -> dict:
        return {
            "entity": "user_dictionary",
            "page_sizes": [50, 100],
            "filters": [
                {"name": "status", "options": [{"value": "ready_for_rotation"}]},
                {"name": "part_of_speech", "options": [{"value": "noun"}]},
                {"name": "level_id", "options": [{"value": "2"}, {"value": "x"}]},
            ],
        }

    def list_admin_entries(self, **kwargs) -> dict:
        self.list_params = kwargs
        return {"items": [{"id": 1, "word": "cord"}], "page": kwargs["page"], "page_size": kwargs["page_size"], "total": 1, "pages": 1}

    def get_admin_entry_detail(self, entry_id: int) -> dict | None:
        if entry_id != 1:
            return None
        return {"id": 1, "word": "cord", "failure_reason": "provider offline"}

    def get_entry_audio(self, entry_id: int) -> dict | None:
        if entry_id != 1:
            return None
        return {"id": 1, "audio_path": "runtime/user_audio/cord.mp3"}


class FakeDb:
    def __init__(self) -> None:
        self.acl_permissions = FakeAclPermissionRepository()
        self.user_dictionary = FakeUserDictionaryRepository()


def test_admin_user_dictionary_read_service_lists_entries_with_valid_filters() -> None:
    db = FakeDb()
    service = AdminUserDictionaryReadService(db)

    result = service.list_entries(
        actor={"telegram_user_id": 1, "acl_group_title": "admin"},
        params={
            "page": "2",
            "page_size": "100",
            "search": " cord ",
            "status": ["ready_for_rotation"],
            "part_of_speech": ["noun"],
            "level_id": ["2"],
        },
    )

    assert result["items"] == [{"id": 1, "word": "cord"}]
    assert db.user_dictionary.list_params == {
        "page": 2,
        "page_size": 100,
        "search": "cord",
        "status": ["ready_for_rotation"],
        "part_of_speech": ["noun"],
        "level_id": [2],
    }


def test_admin_user_dictionary_read_service_raises_application_error_for_denied_access() -> None:
    service = AdminUserDictionaryReadService(FakeDb())

    try:
        service.list_entries(
            actor={"telegram_user_id": 1, "acl_group_title": "student"},
            params={"page": 1, "page_size": 50},
        )
    except AdminUserDictionaryReadAccessDeniedError as error:
        assert error.detail == "User dictionary access is not allowed"
    else:  # pragma: no cover
        raise AssertionError("AdminUserDictionaryReadAccessDeniedError was expected")


def test_admin_user_dictionary_read_service_rejects_unknown_status() -> None:
    service = AdminUserDictionaryReadService(FakeDb())

    try:
        service.list_entries(
            actor={"telegram_user_id": 1, "acl_group_title": "admin"},
            params={"page": 1, "page_size": 50, "status": ["weird"]},
        )
    except AdminUserDictionaryReadValidationError as error:
        assert "status contains unsupported value" in error.detail
    else:  # pragma: no cover
        raise AssertionError("AdminUserDictionaryReadValidationError was expected")


def test_admin_user_dictionary_read_service_rejects_invalid_pagination() -> None:
    service = AdminUserDictionaryReadService(FakeDb())

    try:
        service.list_entries(
            actor={"telegram_user_id": 1, "acl_group_title": "admin"},
            params={"page": "1", "page_size": "25"},
        )
    except AdminUserDictionaryReadValidationError as error:
        assert "page_size" in error.detail
    else:  # pragma: no cover
        raise AssertionError("AdminUserDictionaryReadValidationError was expected")


def test_admin_user_dictionary_read_service_preserves_filter_validation_order() -> None:
    service = AdminUserDictionaryReadService(FakeDb())

    try:
        service.list_entries(
            actor={"telegram_user_id": 1, "acl_group_title": "admin"},
            params={"page": 1, "page_size": 50, "status": ["weird"], "level_id": ["unknown"]},
        )
    except AdminUserDictionaryReadValidationError as error:
        assert "status contains unsupported value" in error.detail
    else:  # pragma: no cover
        raise AssertionError("AdminUserDictionaryReadValidationError was expected")


def test_admin_user_dictionary_read_service_rejects_invalid_level_id() -> None:
    service = AdminUserDictionaryReadService(FakeDb())

    try:
        service.list_entries(
            actor={"telegram_user_id": 1, "acl_group_title": "admin"},
            params={"page": 1, "page_size": 50, "level_id": ["x"]},
        )
    except AdminUserDictionaryReadLevelIdFilterError as error:
        assert error.detail == "level_id must contain numeric values"
    else:  # pragma: no cover
        raise AssertionError("AdminUserDictionaryReadLevelIdFilterError was expected")


def test_admin_user_dictionary_read_service_returns_entry_detail() -> None:
    service = AdminUserDictionaryReadService(FakeDb())

    result = service.get_entry_detail(
        actor={"telegram_user_id": 1, "acl_group_title": "admin"},
        entry_id=1,
    )

    assert result == {"entry": {"id": 1, "word": "cord", "failure_reason": "provider offline"}}


def test_admin_user_dictionary_read_service_raises_local_error_for_missing_entry_detail() -> None:
    service = AdminUserDictionaryReadService(FakeDb())

    try:
        service.get_entry_detail(
            actor={"telegram_user_id": 1, "acl_group_title": "admin"},
            entry_id=404,
        )
    except AdminUserDictionaryReadEntryNotFoundError as error:
        assert error.detail == "User dictionary entry was not found"
    else:  # pragma: no cover
        raise AssertionError("AdminUserDictionaryReadEntryNotFoundError was expected")


def test_admin_user_dictionary_read_service_returns_audio_path() -> None:
    service = AdminUserDictionaryReadService(FakeDb())

    result = service.get_audio_path(actor={"telegram_user_id": 1, "acl_group_title": "admin"}, entry_id=1)

    assert result == "runtime/user_audio/cord.mp3"


def test_admin_user_dictionary_read_service_raises_local_error_for_missing_audio() -> None:
    service = AdminUserDictionaryReadService(FakeDb())

    try:
        service.get_audio_path(actor={"telegram_user_id": 1, "acl_group_title": "admin"}, entry_id=404)
    except AdminUserDictionaryReadAudioNotFoundError as error:
        assert error.detail == "Audio not found"
    else:  # pragma: no cover
        raise AssertionError("AdminUserDictionaryReadAudioNotFoundError was expected")
