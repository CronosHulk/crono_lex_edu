from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.external_providers.pricing_snapshots import sync_due_provider_pricing_snapshots
from app.external_providers.usage import openai_usage_from_response


def test_openai_usage_from_response_uses_provider_tokens_and_cost() -> None:
    usage = openai_usage_from_response(
        response_json={"usage": {"input_tokens": 1000, "output_tokens": 200}},
        model="gpt-5.4-mini",
        prompt_text="ignored",
        output_text="ignored",
    )

    assert usage.request_count == 1
    assert usage.input_tokens == 1000
    assert usage.output_tokens == 200
    assert usage.total_tokens == 1200
    assert usage.estimated_cost_usd == Decimal("0.001650")


class FakeAIUsageSessionRepository:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def accumulate(self, **kwargs):
        for row in self.rows:
            if (
                row["batch_key"] == kwargs["batch_key"]
                and row["task_key"] == kwargs["task_key"]
                and row["provider_key"] == kwargs["provider_key"]
                and row["model"] == kwargs["model"]
            ):
                row["request_count"] += kwargs["request_count"]
                row["input_tokens"] += kwargs["input_tokens"]
                row["output_tokens"] += kwargs["output_tokens"]
                row["total_tokens"] += kwargs["total_tokens"]
                row["estimated_cost_usd"] = str(
                    Decimal(str(row["estimated_cost_usd"])) + Decimal(str(kwargs["estimated_cost_usd"]))
                )
                return row
        self.rows.append(dict(kwargs))
        return self.rows[-1]


def test_usage_session_accumulation_shape_for_import_batches() -> None:
    repository = FakeAIUsageSessionRepository()
    current_time = datetime(2026, 5, 1, 12, 0, 0)

    for _ in range(2):
        repository.accumulate(
            task_key="user_import.word_details",
            task_scope="client_web",
            provider_key="openai",
            model="gpt-5.4-mini",
            actor_type="telegram_user",
            actor_user_uuid="00000000-0000-4000-8000-000000000042",
            batch_key="import_job:10:word_details",
            request_count=1,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            estimated_cost_usd="0.0003",
            started=current_time,
            finished=current_time,
            created=current_time,
            updated=current_time,
        )

    assert len(repository.rows) == 1
    assert repository.rows[0]["request_count"] == 2
    assert repository.rows[0]["total_tokens"] == 300
    assert repository.rows[0]["estimated_cost_usd"] == "0.0006"


class FakePricingSnapshotRepository:
    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.latest = None

    def latest_observed_at(self):
        return self.latest

    def create_many(self, rows):
        self.rows.extend(dict(row) for row in rows)
        self.latest = rows[0]["observed_at"] if rows else self.latest
        return rows


class FakePricingDatabase:
    def __init__(self) -> None:
        self.ai_provider_pricing_snapshots = FakePricingSnapshotRepository()


def test_weekly_provider_pricing_snapshot_sync_is_due_based() -> None:
    db = FakePricingDatabase()
    current_time = datetime(2026, 5, 1, 12, 0, 0)

    first = sync_due_provider_pricing_snapshots(db, current_time)
    second = sync_due_provider_pricing_snapshots(db, current_time)

    assert first == {"created": 2, "skipped": False}
    assert second == {"created": 0, "skipped": True, "reason": "not_due"}
    assert [row["model"] for row in db.ai_provider_pricing_snapshots.rows] == ["gpt-5.4", "gpt-5.4-mini"]
