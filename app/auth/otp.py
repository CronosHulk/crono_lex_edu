from __future__ import annotations


def format_otp(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) == 6:
        return f"{digits[:3]} {digits[3:]}"
    return value


def normalize_otp(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())
