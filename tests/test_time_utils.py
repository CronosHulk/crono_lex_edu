from __future__ import annotations

from datetime import UTC, datetime

from app.time_utils import TimeService, format_project_datetime, round_datetime_up_to_minutes


def test_format_datetime_returns_dash_for_none() -> None:
    service = TimeService("Europe/Kyiv")

    assert service.format_datetime(None) == "-"


def test_format_datetime_formats_naive_datetime() -> None:
    service = TimeService("Europe/Kyiv")

    result = service.format_datetime(datetime(2026, 4, 1, 12, 30, 45))

    assert result == "2026-04-01 12:30:45"


def test_format_datetime_converts_timezone_aware_value() -> None:
    service = TimeService("Europe/Kyiv")

    result = service.format_datetime(datetime(2026, 4, 1, 9, 0, 0, tzinfo=UTC))

    assert result == "2026-04-01 12:00:00"


def test_format_project_datetime_uses_project_format() -> None:
    result = format_project_datetime(datetime(2026, 12, 1, 0, 1, 2))

    assert result == "2026-12-01 00:01:02"


def test_round_datetime_up_to_minutes_rounds_seconds_and_minutes_up() -> None:
    result = round_datetime_up_to_minutes(datetime(2026, 4, 1, 10, 1, 5), 10)

    assert result == datetime(2026, 4, 1, 10, 10, 0)


def test_round_datetime_up_to_minutes_keeps_existing_boundary() -> None:
    result = round_datetime_up_to_minutes(datetime(2026, 4, 1, 10, 10, 0), 10)

    assert result == datetime(2026, 4, 1, 10, 10, 0)
