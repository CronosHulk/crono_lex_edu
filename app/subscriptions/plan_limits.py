from __future__ import annotations

from typing import Any

from app.subscriptions.plans import (
    IMPORT_MODE_AI_NEW_WORDS,
    IMPORT_MODE_LOOKUP_ONLY,
    PLAN_FREE,
    PLAN_PERMANENT_PREMIUM,
    PLAN_PREMIUM,
    PLAN_PREMIUM_PLUS,
    PLAN_TEACHER_FREE,
    PLAN_TEACHER_PREMIUM,
)

PLAN_LIMITS_SETTINGS_KEY = "subscriptions.plan_limits"
CUSTOMER_PLAN_KEYS = (PLAN_FREE, PLAN_PREMIUM, PLAN_PREMIUM_PLUS)
ALL_PLAN_KEYS = (
    PLAN_FREE,
    PLAN_PREMIUM,
    PLAN_PREMIUM_PLUS,
    PLAN_PERMANENT_PREMIUM,
    PLAN_TEACHER_FREE,
    PLAN_TEACHER_PREMIUM,
)
PLAN_IMPORT_MODES = {IMPORT_MODE_LOOKUP_ONLY, IMPORT_MODE_AI_NEW_WORDS}
PLAN_LEVEL_OPTIONS = {"A1", "A2", "B1", "B2", "C1", "C2"}
PLAN_WORD_COUNT_OPTIONS = {5, 10, 15, 20, 30, 40}
PLAN_REMINDERS_PER_DAY_OPTIONS = {1, 2, 3, 4}

DEFAULT_PLAN_LIMITS = {
    PLAN_FREE: {
        "level_titles": ["A1", "A2"],
        "words_per_session_options": [5, 10, 15],
        "reminders_per_day": 1,
        "import_mode": IMPORT_MODE_LOOKUP_ONLY,
        "new_import_words_per_week": 0,
        "homework_access": False,
        "listening_training": False,
        "reading_training": False,
    },
    PLAN_PREMIUM: {
        "level_titles": None,
        "words_per_session_options": None,
        "reminders_per_day": 4,
        "import_mode": IMPORT_MODE_AI_NEW_WORDS,
        "new_import_words_per_week": None,
        "homework_access": False,
        "listening_training": False,
        "reading_training": False,
    },
    PLAN_PREMIUM_PLUS: {
        "level_titles": None,
        "words_per_session_options": None,
        "reminders_per_day": 4,
        "import_mode": IMPORT_MODE_AI_NEW_WORDS,
        "new_import_words_per_week": None,
        "homework_access": False,
        "listening_training": True,
        "reading_training": True,
    },
    PLAN_PERMANENT_PREMIUM: {
        "level_titles": None,
        "words_per_session_options": None,
        "reminders_per_day": 4,
        "import_mode": IMPORT_MODE_AI_NEW_WORDS,
        "new_import_words_per_week": None,
        "homework_access": True,
        "listening_training": True,
        "reading_training": True,
    },
    PLAN_TEACHER_FREE: {
        "level_titles": None,
        "words_per_session_options": None,
        "reminders_per_day": 4,
        "import_mode": IMPORT_MODE_AI_NEW_WORDS,
        "new_import_words_per_week": None,
        "homework_access": True,
        "listening_training": True,
        "reading_training": True,
    },
    PLAN_TEACHER_PREMIUM: {
        "level_titles": None,
        "words_per_session_options": None,
        "reminders_per_day": 4,
        "import_mode": IMPORT_MODE_AI_NEW_WORDS,
        "new_import_words_per_week": None,
        "homework_access": True,
        "listening_training": True,
        "reading_training": True,
    },
}
PLAN_LIMIT_FIELDS = set(next(iter(DEFAULT_PLAN_LIMITS.values())))


class PlanLimitSettingsValidationError(ValueError):
    pass


def read_plan_limit_settings(db: Any) -> dict[str, dict[str, Any]]:
    repository = getattr(db, "app_settings", None)
    stored = repository.get_value(PLAN_LIMITS_SETTINGS_KEY) if repository is not None else None
    return normalize_plan_limit_settings(stored or {}, partial=True)


def normalize_plan_limit_settings(value: Any, *, partial: bool = False) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        raise PlanLimitSettingsValidationError("plan_limits must be an object")
    unknown_plans = set(value) - set(ALL_PLAN_KEYS)
    if unknown_plans:
        raise PlanLimitSettingsValidationError(f"Unsupported plan_limits plans: {', '.join(sorted(unknown_plans))}")
    normalized = _clone_default_limits() if partial else {}
    for plan_key, raw_limits in value.items():
        base = normalized.get(plan_key, dict(DEFAULT_PLAN_LIMITS[plan_key])) if partial else {}
        normalized[plan_key] = normalize_single_plan_limits(raw_limits, plan_key=plan_key, base=base, partial=partial)
    return normalized


def normalize_single_plan_limits(
    value: Any,
    *,
    plan_key: str,
    base: dict[str, Any] | None = None,
    partial: bool = False,
) -> dict[str, Any]:
    if plan_key not in ALL_PLAN_KEYS:
        raise PlanLimitSettingsValidationError(f"Unsupported plan: {plan_key}")
    if not isinstance(value, dict):
        raise PlanLimitSettingsValidationError(f"plan_limits.{plan_key} must be an object")
    unknown_fields = set(value) - PLAN_LIMIT_FIELDS
    if unknown_fields:
        raise PlanLimitSettingsValidationError(
            f"Unsupported plan_limits.{plan_key} fields: {', '.join(sorted(unknown_fields))}",
        )
    normalized = dict(DEFAULT_PLAN_LIMITS[plan_key] if base is None else base) if partial else {}
    for field_name, raw in value.items():
        if field_name == "level_titles":
            normalized[field_name] = _normalize_nullable_allowed_list(raw, PLAN_LEVEL_OPTIONS, f"plan_limits.{plan_key}.{field_name}")
        elif field_name == "words_per_session_options":
            normalized[field_name] = _normalize_nullable_allowed_int_list(raw, PLAN_WORD_COUNT_OPTIONS, f"plan_limits.{plan_key}.{field_name}")
        elif field_name == "reminders_per_day":
            normalized[field_name] = int(_ensure_allowed_plan_value(_normalize_int(raw, field_name), PLAN_REMINDERS_PER_DAY_OPTIONS, field_name))
        elif field_name == "import_mode":
            normalized[field_name] = _ensure_allowed_plan_value(str(raw).strip(), PLAN_IMPORT_MODES, field_name)
        elif field_name == "new_import_words_per_week":
            normalized[field_name] = _normalize_nullable_non_negative_int(raw, field_name)
        elif field_name in {"homework_access", "listening_training", "reading_training"}:
            normalized[field_name] = _normalize_bool(raw, field_name)
    if not partial:
        for field_name, default_value in DEFAULT_PLAN_LIMITS[plan_key].items():
            normalized.setdefault(field_name, default_value)
    return normalized


def _clone_default_limits() -> dict[str, dict[str, Any]]:
    return {plan_key: dict(limits) for plan_key, limits in DEFAULT_PLAN_LIMITS.items()}


def _normalize_nullable_allowed_list(raw: Any, allowed_values: set[str], field_name: str) -> list[str] | None:
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise PlanLimitSettingsValidationError(f"{field_name} must be a list or null")
    values = [_ensure_allowed_plan_value(str(item).strip(), allowed_values, field_name) for item in raw]
    return _deduplicate(values)


def _normalize_nullable_allowed_int_list(raw: Any, allowed_values: set[int], field_name: str) -> list[int] | None:
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise PlanLimitSettingsValidationError(f"{field_name} must be a list or null")
    values = [int(_ensure_allowed_plan_value(_normalize_int(item, field_name), allowed_values, field_name)) for item in raw]
    return _deduplicate(values)


def _normalize_nullable_non_negative_int(raw: Any, field_name: str) -> int | None:
    if raw is None:
        return None
    value = _normalize_int(raw, field_name)
    if value < 0:
        raise PlanLimitSettingsValidationError(f"{field_name} must be at least 0")
    return value


def _normalize_int(raw: Any, field_name: str) -> int:
    if isinstance(raw, bool):
        raise PlanLimitSettingsValidationError(f"{field_name} must be an integer")
    try:
        return int(raw)
    except (TypeError, ValueError) as error:
        raise PlanLimitSettingsValidationError(f"{field_name} must be an integer") from error


def _normalize_bool(raw: Any, field_name: str) -> bool:
    if isinstance(raw, bool):
        return raw
    raise PlanLimitSettingsValidationError(f"{field_name} must be a boolean")


def _ensure_allowed_plan_value(value: Any, allowed_values: set[Any], field_name: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise PlanLimitSettingsValidationError(f"{field_name} is required")
    if len(text) > 100:
        raise PlanLimitSettingsValidationError(f"{field_name} must be at most 100 characters")
    allowed = {str(item) for item in allowed_values}
    if text not in allowed:
        expected = ", ".join(sorted(allowed))
        raise PlanLimitSettingsValidationError(f"{field_name} must be one of: {expected}")
    return text


def _deduplicate(values: list[Any]) -> list[Any]:
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
