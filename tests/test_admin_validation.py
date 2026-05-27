from __future__ import annotations

from fastapi import HTTPException
from pydantic import ValidationError

import app.validation.pagination as validation_pagination
import app.validation.request_values as request_values
from app.admin_api.exercise_texts.schemas import ExerciseTextCreateRequest
from app.admin_api.router import (
    AdminAuthStartRequest,
    AdminDictionaryVerifyRequest,
    AdminSetLearningRoleRequest,
    AdminSetRoleRequest,
    AdminSetSubscriptionRequest,
    AdminSettingsUpdateRequest,
    AdminUserDictionaryBulkActionRequest,
    AdminUserDictionaryPromoteRequest,
)
from app.api_helpers.request_validation import ensure_allowed_values, ensure_project_datetime_string
from app.application.admin.dictionary.validators import (
    AdminExamplesValidationError,
    normalize_examples_json,
)
from app.application.admin.settings.errors import AdminSettingsValidationError
from app.application.admin.settings.validators import normalize_settings_payload


def test_pagination_core_rejects_unknown_page_size_with_local_error() -> None:
    try:
        validation_pagination.normalize_pagination(
            {"page": "1", "page_size": "25"},
            default_page_size=50,
            allowed_page_sizes={50, 100},
        )
    except request_values.RequestValueValidationError as error:
        assert error.detail == "page_size must be one of: 100, 50"
    else:  # pragma: no cover
        raise AssertionError("RequestValueValidationError was expected")


def test_normalize_examples_json_accepts_multiline_text() -> None:
    examples = normalize_examples_json(" One.\n\nTwo. ", max_count=3)

    assert examples == ["One.", "Two."]


def test_normalize_examples_json_rejects_non_ascii_when_required() -> None:
    try:
        normalize_examples_json(["Слово."], max_count=3, ascii_only=True)
    except AdminExamplesValidationError as error:
        assert error.detail == "examples_json items must contain only ASCII characters"
    else:  # pragma: no cover
        raise AssertionError("AdminExamplesValidationError was expected")


def test_allowed_values_reject_unknown_filter_value() -> None:
    try:
        ensure_allowed_values(["a1", "foo"], {"a1", "b2", "c2"}, "level")
    except HTTPException as error:
        assert error.status_code == 400
        assert "level contains unsupported value 'foo'" in str(error.detail)
    else:  # pragma: no cover
        raise AssertionError("HTTPException was expected")


def test_request_value_core_rejects_unknown_filter_value_with_local_error() -> None:
    try:
        request_values.ensure_allowed_values(["a1", "foo"], {"a1", "b2", "c2"}, "level")
    except request_values.RequestValueValidationError as error:
        assert error.detail == "level contains unsupported value 'foo'. Expected one of: a1, b2, c2"
    else:  # pragma: no cover
        raise AssertionError("RequestValueValidationError was expected")


def test_request_value_core_normalizes_filter_values() -> None:
    assert request_values.normalize_filter_values(None) == []
    assert request_values.normalize_filter_values(" warn, fatal, warn, ") == ["warn", "fatal"]
    assert request_values.normalize_filter_values(("debug", "debug", "fatal")) == ["debug", "fatal"]
    assert request_values.normalize_filter_values(["a1", " ", "b2", "a1"]) == ["a1", "b2"]


def test_project_datetime_accepts_single_project_format() -> None:
    assert ensure_project_datetime_string("2026-12-01 00:01:02", "created") == "2026-12-01 00:01:02"


def test_request_value_core_accepts_single_project_datetime_format() -> None:
    assert request_values.ensure_project_datetime_string("2026-12-01 00:01:02", "created") == "2026-12-01 00:01:02"


def test_project_datetime_rejects_iso_separator() -> None:
    try:
        ensure_project_datetime_string("2026-12-01T00:01:02", "created")
    except HTTPException as error:
        assert error.status_code == 400
        assert error.detail == "created must use YYYY-MM-DD HH:MM:SS format"
    else:  # pragma: no cover
        raise AssertionError("HTTPException was expected")


def test_request_value_core_rejects_iso_separator_with_local_error() -> None:
    try:
        request_values.ensure_project_datetime_string("2026-12-01T00:01:02", "created")
    except request_values.RequestValueValidationError as error:
        assert error.detail == "created must use YYYY-MM-DD HH:MM:SS format"
    else:  # pragma: no cover
        raise AssertionError("RequestValueValidationError was expected")


def test_admin_set_role_request_rejects_unknown_role() -> None:
    try:
        AdminSetRoleRequest(role="super_admin")
    except ValidationError as error:
        assert "role must be one of" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValidationError was expected")


def test_admin_set_learning_role_request_rejects_unknown_role() -> None:
    assert AdminSetLearningRoleRequest(learning_role="teacher").learning_role == "teacher"

    try:
        AdminSetLearningRoleRequest(learning_role="admin")
    except ValidationError as error:
        assert "learning_role must be one of" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValidationError was expected")


def test_admin_set_subscription_request_rejects_unknown_plan() -> None:
    assert AdminSetSubscriptionRequest(plan_key="premium_plus").plan_key == "premium_plus"

    try:
        AdminSetSubscriptionRequest(plan_key="free_trial")
    except ValidationError as error:
        assert "plan_key must be one of" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValidationError was expected")


def test_admin_settings_payload_normalizes_plan_limits() -> None:
    payload = normalize_settings_payload(
        {
            "plan_limits": {
                "premium_plus": {
                    "level_titles": None,
                    "words_per_session_options": None,
                    "reminders_per_day": 4,
                    "import_mode": "ai_new_words",
                    "new_import_words_per_week": 50,
                    "listening_training": True,
                    "reading_training": True,
                }
            }
        }
    )

    assert payload["plan_limits"]["premium_plus"]["listening_training"] is True


def test_admin_settings_payload_normalizes_billing_settings() -> None:
    payload = normalize_settings_payload(
        {
            "billing_settings": {
                "enabled_period_months": [1, 3],
                "plan_prices_uah": {"premium": {"1": 10}},
                "webhook_wait_seconds": 20,
            }
        }
    )

    assert payload["billing_settings"]["enabled_period_months"] == [1, 3]
    assert payload["billing_settings"]["plan_prices_uah"]["premium"]["1"] == 10


def test_admin_settings_payload_rejects_billing_monobank_mode() -> None:
    try:
        normalize_settings_payload({"billing_settings": {"monobank_mode": "test"}})
    except AdminSettingsValidationError as error:
        assert "Use OTP-protected billing provider settings endpoint" in str(error.detail)
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsValidationError was expected")


def test_admin_settings_payload_rejects_unknown_billing_field() -> None:
    try:
        normalize_settings_payload({"billing_settings": {"monobank_token": "secret"}})
    except AdminSettingsValidationError as error:
        assert "Unsupported billing_settings fields" in str(error.detail)
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsValidationError was expected")


def test_admin_settings_request_allows_support_settings() -> None:
    payload = AdminSettingsUpdateRequest(
        support_settings={
            "is_enabled": True,
            "support_url": "https://send.monobank.ua/jar/custom",
        }
    ).model_dump(exclude_unset=True)

    assert payload["support_settings"]["support_url"] == "https://send.monobank.ua/jar/custom"


def test_admin_settings_request_allows_import_weekday_presets() -> None:
    payload = AdminSettingsUpdateRequest(
        import_settings={
            "google_doc_sync_weekdays": [0, 2, 4],
        }
    ).model_dump(exclude_unset=True)

    assert payload["import_settings"]["google_doc_sync_weekdays"] == [0, 2, 4]


def test_admin_settings_payload_rejects_string_boolean_plan_limit() -> None:
    try:
        normalize_settings_payload({"plan_limits": {"free": {"listening_training": "false"}}})
    except AdminSettingsValidationError as error:
        assert "listening_training" in str(error.detail)
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsValidationError was expected")


def test_admin_settings_payload_rejects_unknown_plan_limit_value() -> None:
    try:
        normalize_settings_payload({"plan_limits": {"free": {"level_titles": ["A1", "Z9"]}}})
    except AdminSettingsValidationError as error:
        assert "level_titles" in str(error.detail)
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsValidationError was expected")


def test_admin_settings_payload_allows_new_word_count_plan_limit() -> None:
    payload = normalize_settings_payload({"plan_limits": {"premium": {"words_per_session_options": [30, 40]}}})

    assert payload["plan_limits"]["premium"]["words_per_session_options"] == [30, 40]


def test_admin_dictionary_verify_request_rejects_empty_ids() -> None:
    assert AdminDictionaryVerifyRequest(entry_ids=[2, 2, 3]).entry_ids == [2, 3]

    try:
        AdminDictionaryVerifyRequest(entry_ids=[])
    except ValidationError as error:
        assert "List should have at least 1 item" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValidationError was expected")


def test_admin_user_dictionary_promote_request_rejects_invalid_ids() -> None:
    assert AdminUserDictionaryPromoteRequest(entry_ids=[5, 5, 6]).entry_ids == [5, 6]

    try:
        AdminUserDictionaryPromoteRequest(entry_ids=[0])
    except ValidationError as error:
        assert "entry_ids must be a positive integer" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValidationError was expected")


def test_exercise_text_create_request_rejects_invalid_topic_ids() -> None:
    assert ExerciseTextCreateRequest(topic_ids=[7, 7, 8]).topic_ids == [7, 8]

    try:
        ExerciseTextCreateRequest(topic_ids=[0])
    except ValidationError as error:
        assert "topic_ids must be a positive integer" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValidationError was expected")


def test_admin_user_dictionary_bulk_action_request_rejects_unknown_action() -> None:
    try:
        AdminUserDictionaryBulkActionRequest(action="explode", entry_ids=[1])
    except ValidationError as error:
        assert "action" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValidationError was expected")


def test_admin_auth_start_request_rejects_extra_fields() -> None:
    try:
        AdminAuthStartRequest(username="admin", remember_me=True)
    except ValidationError as error:
        assert "Extra inputs are not permitted" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValidationError was expected")
