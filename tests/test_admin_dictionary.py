from __future__ import annotations

from app.application.admin.dictionary.dictionary_service import (
    AdminDictionaryService,
)
from app.application.admin.dictionary.errors import (
    AdminDictionaryServiceAccessDeniedError,
    AdminDictionaryServiceAudioNotFoundError,
    AdminDictionaryServiceEntryNotFoundError,
    AdminDictionaryServiceValidationError,
)
from app.time_utils import TimeService
from tests.test_admin_service import FakeAdminDb, build_pending_row

ACTOR = {"telegram_user_id": 1, "acl_group_title": "admin"}
DENIED_ACTOR = {"telegram_user_id": 1, "acl_group_title": "student"}


class FakeAudioStorageProvider:
    def delete_if_under_roots(self, audio_path, audio_roots) -> bool:
        return False


def test_admin_dictionary_service_updates_entry_with_normalized_payload() -> None:
    db = FakeAdminDb(build_pending_row())
    db.dictionary_entry = {
        "id": 10,
        "word": "old",
        "translation_uk": "старе",
        "examples_json": [],
        "entry_type": "word",
    }
    audio_storage_provider = FakeAudioStorageProvider()
    service = AdminDictionaryService(
        db,
        TimeService("Europe/Kyiv"),
        audio_storage_provider=audio_storage_provider,
    )

    result = service.update_dictionary_entry(
        actor=ACTOR,
        entry_id=10,
        payload={
            "word": " harbor ",
            "translation_uk": " гавань ",
            "phonetic_us": " /har-bor/ ",
            "examples_json": "The harbor was quiet.",
            "entry_type": "phrasal_verb",
        },
    )

    assert result["word"] == "harbor"
    assert result["translation_uk"] == "гавань"
    assert result["transcription"] == "/har-bor/"
    assert result["examples_json"] == ["The harbor was quiet."]
    assert result["entry_type"] == "phrasal_verb"
    assert db.dictionary_update_audio_storage_provider is audio_storage_provider


def test_admin_dictionary_service_rejects_missing_required_translation() -> None:
    service = AdminDictionaryService(
        FakeAdminDb(build_pending_row()),
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
    )

    try:
        service.update_dictionary_entry(actor=ACTOR, entry_id=10, payload={"word": "harbor", "translation_uk": " "})
    except AdminDictionaryServiceValidationError as error:
        assert error.detail == "translation_uk is required"
    else:  # pragma: no cover
        raise AssertionError("AdminDictionaryServiceValidationError was expected")


def test_admin_dictionary_service_rejects_unknown_entry_type() -> None:
    service = AdminDictionaryService(
        FakeAdminDb(build_pending_row()),
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
    )

    try:
        service.update_dictionary_entry(actor=ACTOR, entry_id=10, payload={"entry_type": "slang"})
    except AdminDictionaryServiceValidationError as error:
        assert "entry_type must be one of" in str(error.detail)
    else:  # pragma: no cover
        raise AssertionError("AdminDictionaryServiceValidationError was expected")


def test_admin_dictionary_service_maps_examples_validation_errors() -> None:
    service = AdminDictionaryService(
        FakeAdminDb(build_pending_row()),
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
    )

    try:
        service.update_dictionary_entry(actor=ACTOR, entry_id=10, payload={"examples_json": object()})
    except AdminDictionaryServiceValidationError as error:
        assert error.detail == "examples_json must be a list or multiline string"
    else:  # pragma: no cover
        raise AssertionError("AdminDictionaryServiceValidationError was expected")


def test_admin_dictionary_service_raises_local_error_for_missing_entry() -> None:
    service = AdminDictionaryService(
        FakeAdminDb(None),
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
    )

    try:
        service.update_dictionary_entry(actor=ACTOR, entry_id=404, payload={"word": "harbor"})
    except AdminDictionaryServiceEntryNotFoundError as error:
        assert error.detail == "Dictionary entry not found"
    else:  # pragma: no cover
        raise AssertionError("AdminDictionaryServiceEntryNotFoundError was expected")


def test_admin_dictionary_service_preserves_denied_update_acl_detail_before_validation() -> None:
    service = AdminDictionaryService(
        FakeAdminDb(build_pending_row()),
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
    )

    try:
        service.update_dictionary_entry(actor=DENIED_ACTOR, entry_id=10, payload={"entry_type": "slang"})
    except AdminDictionaryServiceAccessDeniedError as error:
        assert error.detail == "Access denied"
    else:  # pragma: no cover
        raise AssertionError("AdminDictionaryServiceAccessDeniedError was expected")


def test_admin_dictionary_service_returns_audio_path() -> None:
    db = FakeAdminDb(build_pending_row())
    db.dictionary_audio = {"id": 10, "audio_path": "runtime/audio/word.mp3"}
    service = AdminDictionaryService(
        db,
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
    )

    audio_path = service.get_audio_path(actor={"telegram_user_id": 1, "acl_group_title": "admin"}, entry_id=10)

    assert audio_path == "runtime/audio/word.mp3"


def test_admin_dictionary_service_raises_local_error_for_missing_audio() -> None:
    service = AdminDictionaryService(
        FakeAdminDb(build_pending_row()),
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
    )

    try:
        service.get_audio_path(actor={"telegram_user_id": 1, "acl_group_title": "admin"}, entry_id=404)
    except AdminDictionaryServiceAudioNotFoundError as error:
        assert error.detail == "Audio not found"
    else:  # pragma: no cover
        raise AssertionError("AdminDictionaryServiceAudioNotFoundError was expected")
