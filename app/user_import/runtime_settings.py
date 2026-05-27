from __future__ import annotations

from typing import Any

USER_IMPORT_RUNTIME_SETTINGS_KEY = "user_import.runtime_settings"
DEFAULT_IMPORT_RUNTIME_SETTINGS = {
    "enrich_after_google_doc_import_enabled": False,
    "embedding_build_enabled": False,
    "attribute_build_hour": 2,
    "attribute_build_weekdays": None,
    "audio_build_hour": 2,
    "audio_build_weekdays": None,
    "google_doc_sync_hour": 0,
    "google_doc_sync_interval_days": 3,
    "google_doc_sync_weekdays": None,
    "max_import_entries_per_submission": 100,
    "scheduler_tick_minutes": 10,
    "validation_batch_size": 10,
}
IMPORT_SYNC_INTERVAL_DAY_OPTIONS = {1, 2, 3, 4, 5, 6, 7}
IMPORT_SCHEDULE_WEEKDAY_OPTIONS = {0, 1, 2, 3, 4, 5, 6}
IMPORT_SCHEDULE_WEEKDAY_PRESETS = {
    (0, 1, 2, 3, 4, 5, 6),
    (0, 2, 4),
    (1, 3, 5),
    (0, 3),
}
IMPORT_ENTRY_LIMIT_OPTIONS = {10, 25, 50, 100, 150, 200}
IMPORT_SCHEDULER_TICK_MINUTE_OPTIONS = {1, 5, 10, 30, 60}
VALIDATION_BATCH_SIZE_OPTIONS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}


class UserImportRuntimeSettingsValidationError(ValueError):
    pass


def read_user_import_runtime_settings(db: Any) -> dict[str, Any]:
    repository = getattr(db, "app_settings", None)
    if repository is None:
        if not callable(getattr(db, "session", None)):
            return normalize_user_import_runtime_settings({}, partial=True)
        try:
            from app.data_access.app_settings import AppSettingRepository
            repository = AppSettingRepository(db)
        except ImportError:
            pass
    stored = (
        repository.get_value(USER_IMPORT_RUNTIME_SETTINGS_KEY) if repository is not None else None
    )
    return normalize_user_import_runtime_settings(stored or {}, partial=True)


def normalize_user_import_runtime_settings(value: Any, *, partial: bool = False) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise UserImportRuntimeSettingsValidationError("import_settings must be an object")
    allowed_fields = set(DEFAULT_IMPORT_RUNTIME_SETTINGS)
    unknown_fields = set(value) - allowed_fields
    if unknown_fields:
        unknown_list = ", ".join(sorted(unknown_fields))
        raise UserImportRuntimeSettingsValidationError(f"Unsupported import_settings fields: {unknown_list}")
    base = dict(DEFAULT_IMPORT_RUNTIME_SETTINGS) if partial else {}
    for key, raw in value.items():
        if key in {"enrich_after_google_doc_import_enabled", "embedding_build_enabled"}:
            if not isinstance(raw, bool):
                raise UserImportRuntimeSettingsValidationError(f"{key} must be boolean")
            base[key] = raw
        elif key in {"attribute_build_hour", "audio_build_hour", "google_doc_sync_hour"}:
            base[key] = _normalize_hour(raw, key)
        elif key == "google_doc_sync_interval_days":
            base[key] = int(
                _ensure_allowed_import_value(
                    _normalize_positive_int(raw, key),
                    IMPORT_SYNC_INTERVAL_DAY_OPTIONS,
                    key,
                )
            )
        elif key in {"attribute_build_weekdays", "audio_build_weekdays", "google_doc_sync_weekdays"}:
            base[key] = _normalize_schedule_weekdays(raw, key)
        elif key == "max_import_entries_per_submission":
            base[key] = int(
                _ensure_allowed_import_value(
                    _normalize_positive_int(raw, key),
                    IMPORT_ENTRY_LIMIT_OPTIONS,
                    key,
                )
            )
        elif key == "scheduler_tick_minutes":
            base[key] = int(
                _ensure_allowed_import_value(
                    _normalize_positive_int(raw, key),
                    IMPORT_SCHEDULER_TICK_MINUTE_OPTIONS,
                    key,
                )
            )
        elif key == "validation_batch_size":
            base[key] = int(
                _ensure_allowed_import_value(
                    _normalize_positive_int(raw, key),
                    VALIDATION_BATCH_SIZE_OPTIONS,
                    key,
                )
            )
    return base


def _normalize_schedule_weekdays(raw: Any, field_name: str) -> list[int] | None:
    if raw is None:
        return None
    if not isinstance(raw, list) or not raw:
        raise UserImportRuntimeSettingsValidationError(f"{field_name} must be a non-empty list")
    normalized = []
    for item in raw:
        normalized.append(
            int(
                _ensure_allowed_import_value(
                    _normalize_positive_int(item, field_name, allow_zero=True),
                    IMPORT_SCHEDULE_WEEKDAY_OPTIONS,
                    field_name,
                )
            )
        )
    unique = tuple(sorted(set(normalized)))
    if len(unique) != len(normalized):
        raise UserImportRuntimeSettingsValidationError(f"{field_name} must not contain duplicates")
    if unique not in IMPORT_SCHEDULE_WEEKDAY_PRESETS:
        raise UserImportRuntimeSettingsValidationError(f"{field_name} must match a supported weekday preset")
    return list(unique)


def _normalize_hour(raw: Any, field_name: str) -> int:
    value = _normalize_positive_int(raw, field_name, allow_zero=True)
    if value > 23:
        raise UserImportRuntimeSettingsValidationError(f"{field_name} must be between 0 and 23")
    return value


def _normalize_positive_int(raw: Any, field_name: str, *, allow_zero: bool = False) -> int:
    if isinstance(raw, bool):
        raise UserImportRuntimeSettingsValidationError(f"{field_name} must be an integer")
    try:
        value = int(raw)
    except (TypeError, ValueError) as error:
        raise UserImportRuntimeSettingsValidationError(f"{field_name} must be an integer") from error
    if value < 0 or (value == 0 and not allow_zero):
        boundary = "0" if allow_zero else "1"
        raise UserImportRuntimeSettingsValidationError(f"{field_name} must be at least {boundary}")
    return value


def _ensure_allowed_import_value(value: Any, allowed_values: set[Any], field_name: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise UserImportRuntimeSettingsValidationError(f"{field_name} is required")
    if len(text) > 100:
        raise UserImportRuntimeSettingsValidationError(f"{field_name} must be at most 100 characters")
    allowed = {str(item) for item in allowed_values}
    if text not in allowed:
        expected = ", ".join(sorted(allowed))
        raise UserImportRuntimeSettingsValidationError(f"{field_name} must be one of: {expected}")
    return text
