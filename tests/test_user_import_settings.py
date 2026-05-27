from __future__ import annotations

import pytest

from app.user_import.runtime_settings import (
    UserImportRuntimeSettingsValidationError,
    normalize_user_import_runtime_settings,
)
from app.user_import.settings import (
    USER_IMPORT_AUDIO_SCHEDULE_STATE_KEY,
    USER_IMPORT_BUILD_FAILED_RETRY_COOLDOWN_HOURS,
    USER_IMPORT_DETAILS_SCHEDULE_STATE_KEY,
    USER_IMPORT_MAX_DOC_SYNCS_PER_RUN,
    USER_IMPORT_MAX_JOBS_PER_RUN,
    USER_IMPORT_PROCESSING_CLAIM_MINUTES,
    USER_IMPORT_RETRY_DELAYS_SECONDS,
    WORDNIK_RUNTIME_STATE_KEY,
)


def test_user_import_runtime_settings_match_existing_limits() -> None:
    assert USER_IMPORT_RETRY_DELAYS_SECONDS == (2, 2, 2)
    assert USER_IMPORT_PROCESSING_CLAIM_MINUTES == 15
    assert USER_IMPORT_BUILD_FAILED_RETRY_COOLDOWN_HOURS == 24
    assert USER_IMPORT_MAX_DOC_SYNCS_PER_RUN == 10
    assert USER_IMPORT_MAX_JOBS_PER_RUN == 10


def test_user_import_runtime_state_keys_are_stable() -> None:
    assert WORDNIK_RUNTIME_STATE_KEY == "user_import_wordnik_quota"
    assert USER_IMPORT_DETAILS_SCHEDULE_STATE_KEY == "user_import_details_schedule"
    assert USER_IMPORT_AUDIO_SCHEDULE_STATE_KEY == "user_import_audio_schedule"


def test_user_import_runtime_settings_include_audio_schedule_defaults() -> None:
    settings = normalize_user_import_runtime_settings({}, partial=True)

    assert settings["audio_build_hour"] == 2
    assert settings["audio_build_weekdays"] is None


def test_user_import_runtime_settings_reject_invalid_interval() -> None:
    with pytest.raises(UserImportRuntimeSettingsValidationError):
        normalize_user_import_runtime_settings({"google_doc_sync_interval_days": 8}, partial=True)


def test_user_import_runtime_settings_reject_unknown_weekday_preset() -> None:
    with pytest.raises(UserImportRuntimeSettingsValidationError):
        normalize_user_import_runtime_settings({"google_doc_sync_weekdays": [0, 1]}, partial=True)
