from __future__ import annotations


def amount_minor_to_uah(amount_minor: int) -> int | float:
    amount_minor = int(amount_minor)
    if amount_minor % 100 == 0:
        return amount_minor // 100
    return amount_minor / 100
