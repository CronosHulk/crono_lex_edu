from __future__ import annotations


def build_single_choice_label(label: str, is_selected: bool) -> str:
    return f"✓ {label}" if is_selected else label


def build_button_row_widths(
    option_count: int,
    trailing_full_width_buttons: int = 0,
    compact_row_width: int = 2,
) -> list[int]:
    if option_count < 0:
        option_count = 0
    rows: list[int] = []
    full_rows, remainder = divmod(option_count, compact_row_width)
    rows.extend([compact_row_width] * full_rows)
    if remainder:
        rows.append(remainder)
    rows.extend([1] * max(trailing_full_width_buttons, 0))
    return rows
