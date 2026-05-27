from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.models import AIProviderPricingSnapshot
from app.orm import SessionManager


def pricing_snapshot_to_dict(row: AIProviderPricingSnapshot) -> dict[str, Any]:
    return {
        "id": row.id,
        "provider_key": row.provider_key,
        "model": row.model,
        "unit": row.unit,
        "input_usd_per_1m": str(row.input_usd_per_1m or Decimal("0")),
        "output_usd_per_1m": str(row.output_usd_per_1m or Decimal("0")),
        "source": row.source,
        "observed_at": row.observed_at,
        "created": row.created,
    }


class AIProviderPricingSnapshotRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def create_many(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []
        with self.session_manager.session() as session:
            snapshots = [AIProviderPricingSnapshot(**row) for row in rows]
            session.add_all(snapshots)
            session.flush()
            return [pricing_snapshot_to_dict(row) for row in snapshots]

    def latest_observed_at(self) -> datetime | None:
        with self.session_manager.session() as session:
            return session.scalar(
                select(AIProviderPricingSnapshot.observed_at).order_by(
                    AIProviderPricingSnapshot.observed_at.desc(),
                    AIProviderPricingSnapshot.id.desc(),
                ).limit(1)
            )
