from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.subscriptions.paywall import (
    CAPABILITY_CORE_LEVEL,
    CAPABILITY_WORDS_PER_SESSION,
    PaywallService,
)
from app.subscriptions.plans import SubscriptionEntitlements

_PAYWALL = PaywallService()


def filter_level_rows(
    levels: Iterable[dict[str, Any]],
    entitlements: SubscriptionEntitlements | None,
) -> list[dict[str, Any]]:
    rows = list(levels)
    if entitlements is None:
        return rows
    return [level for level in rows if _PAYWALL.can_use(entitlements, CAPABILITY_CORE_LEVEL, str(level.get("title") or ""))]


def filter_level_titles(
    level_titles: Iterable[str],
    entitlements: SubscriptionEntitlements | None,
) -> list[str]:
    titles = list(level_titles)
    if entitlements is None:
        return titles
    return [title for title in titles if _PAYWALL.can_use(entitlements, CAPABILITY_CORE_LEVEL, title)]


def filter_words_per_session_options(
    options: Iterable[int],
    entitlements: SubscriptionEntitlements | None,
) -> tuple[int, ...]:
    normalized = tuple(int(option) for option in options)
    if entitlements is None:
        return normalized
    return tuple(option for option in normalized if _PAYWALL.can_use(entitlements, CAPABILITY_WORDS_PER_SESSION, option))


def is_level_title_allowed(level_title: str, entitlements: SubscriptionEntitlements | None) -> bool:
    return entitlements is None or _PAYWALL.can_use(entitlements, CAPABILITY_CORE_LEVEL, level_title)


def is_words_per_session_allowed(words_per_session: int, entitlements: SubscriptionEntitlements | None) -> bool:
    return entitlements is None or _PAYWALL.can_use(entitlements, CAPABILITY_WORDS_PER_SESSION, words_per_session)
