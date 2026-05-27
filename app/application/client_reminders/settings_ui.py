from __future__ import annotations

from datetime import datetime

from app.application.client_ui.choice_controls import (
    build_button_row_widths as build_button_row_widths,
)
from app.application.client_ui.choice_controls import (
    build_single_choice_label as build_single_choice_label,
)


def format_schedule_label(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%Y-%m-%d %H:%M")
