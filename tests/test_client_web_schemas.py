from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.client_api.client_web.schemas import (
    ClientWebLearningAnswerRequest,
    ClientWebLearningWordPriorityRequest,
    ClientWebSettingsUpdateRequest,
)
from app.helpers.locale import normalize_interface_locale, resolve_user_locale


def test_client_web_learning_answer_accepts_four_option_indexes() -> None:
    for option_index in range(4):
        request = ClientWebLearningAnswerRequest(session_word_id=1, option_index=option_index)

        assert request.option_index == option_index


def test_client_web_learning_answer_rejects_fifth_option_index() -> None:
    with pytest.raises(ValidationError):
        ClientWebLearningAnswerRequest(session_word_id=1, option_index=4)


def test_client_web_learning_word_priority_normalizes_supported_source() -> None:
    request = ClientWebLearningWordPriorityRequest(word_source=" USER ", word_id=88)

    assert request.word_source == "user"
    assert request.word_id == 88


def test_client_web_learning_word_priority_rejects_unknown_source() -> None:
    with pytest.raises(ValidationError):
        ClientWebLearningWordPriorityRequest(word_source="external", word_id=88)


def test_client_web_learning_word_priority_rejects_invalid_word_id() -> None:
    with pytest.raises(ValidationError):
        ClientWebLearningWordPriorityRequest(word_source="core", word_id=0)


def test_client_web_settings_accepts_supported_interface_locales() -> None:
    for locale in ("uk", "ru", "pl"):
        request = ClientWebSettingsUpdateRequest(interface_locale=locale)

        assert request.interface_locale == locale


def test_client_web_settings_rejects_unknown_interface_locale() -> None:
    with pytest.raises(ValidationError):
        ClientWebSettingsUpdateRequest(interface_locale="de")


def test_resolve_user_locale_prefers_saved_interface_locale() -> None:
    assert resolve_user_locale({"interface_locale": "pl", "language_code": "uk"}) == "pl"


def test_normalize_interface_locale_accepts_supported_telegram_language_codes() -> None:
    assert normalize_interface_locale("uk-UA") == "uk"
    assert normalize_interface_locale("ru-RU") == "ru"
    assert normalize_interface_locale("pl-PL") == "pl"


def test_normalize_interface_locale_falls_back_to_uk_for_unsupported_language_codes() -> None:
    assert normalize_interface_locale("en-US") == "uk"
    assert normalize_interface_locale("de") == "uk"
    assert normalize_interface_locale(None) == "uk"


def test_resolve_user_locale_falls_back_to_normalized_telegram_language_code() -> None:
    assert resolve_user_locale({"language_code": "pl-PL"}) == "pl"
    assert resolve_user_locale({"language_code": "en-US"}) == "uk"
