from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Protocol

from app.domain.provider_pricing import TOKEN_PRICING

PRICING_SNAPSHOT_INTERVAL = timedelta(days=7)


class ProviderPricingSnapshotRepositoryPort(Protocol):
    def latest_observed_at(self) -> datetime | None: ...

    def create_many(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]: ...


class ProviderPricingSnapshotsDatabasePort(Protocol):
    ai_provider_pricing_snapshots: ProviderPricingSnapshotRepositoryPort | None


def sync_due_provider_pricing_snapshots(
    db: ProviderPricingSnapshotsDatabasePort,
    current_time: datetime,
) -> dict[str, Any]:
    repository = getattr(db, "ai_provider_pricing_snapshots", None)
    if repository is None:
        return {"created": 0, "skipped": True, "reason": "repository_unavailable"}

    latest_observed_at = repository.latest_observed_at()
    if latest_observed_at is not None and current_time - latest_observed_at < PRICING_SNAPSHOT_INTERVAL:
        return {"created": 0, "skipped": True, "reason": "not_due"}

    rows = [
        {
            "provider_key": item.provider_key,
            "model": item.model,
            "unit": "tokens_per_1m",
            "input_usd_per_1m": item.input_usd_per_1m,
            "output_usd_per_1m": item.output_usd_per_1m,
            "source": item.source,
            "observed_at": current_time,
            "created": current_time,
        }
        for item in TOKEN_PRICING
    ]
    created = repository.create_many(rows)
    return {"created": len(created), "skipped": False}
