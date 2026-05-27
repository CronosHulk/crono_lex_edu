from __future__ import annotations


def validate_password_complexity(password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters")
    if not any(ch.isascii() and ch.isalpha() for ch in password):
        raise ValueError("Password must contain Latin letters")
    if not any(ch.isdigit() for ch in password):
        raise ValueError("Password must contain digits")
