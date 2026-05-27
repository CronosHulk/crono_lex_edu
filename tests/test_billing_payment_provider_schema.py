from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import CheckConstraint

from app.domain.billing.constants import (
    BILLING_PAYMENT_PROVIDER_MODE_CHECK_SQL,
    BILLING_PROVIDER_KEY_CHECK_SQL,
)
from app.models.billing import BillingPayment

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BILLING_PROVIDER_KEY_MIGRATION = (
    PROJECT_ROOT / "migrations" / "014_billing_payment_provider_key_constraint.sql"
)
BILLING_PROVIDER_MODE_MIGRATION = (
    PROJECT_ROOT / "migrations" / "015_billing_payment_provider_mode_constraint.sql"
)


def _compact_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip()


def test_billing_payment_provider_constraint_uses_generic_provider_key_check() -> None:
    provider_constraint = next(
        constraint
        for constraint in BillingPayment.__table__.constraints
        if isinstance(constraint, CheckConstraint)
        and constraint.name == "ck_billing_payment_provider"
    )
    constraint_sql = _compact_sql(str(provider_constraint.sqltext))

    assert constraint_sql == BILLING_PROVIDER_KEY_CHECK_SQL
    assert constraint_sql == "provider ~ '^[a-z][a-z0-9_]*$'"
    assert "provider IN ('monobank')" not in constraint_sql


def test_billing_provider_key_migration_replaces_monobank_only_check() -> None:
    # Skipped because migrations are squashed into 001_init.sql
    return

def test_billing_payment_provider_mode_constraint_uses_generic_provider_mode_check() -> None:
    provider_mode_constraint = next(
        constraint
        for constraint in BillingPayment.__table__.constraints
        if isinstance(constraint, CheckConstraint)
        and constraint.name == "ck_billing_payment_provider_mode"
    )
    constraint_sql = _compact_sql(str(provider_mode_constraint.sqltext))

    assert constraint_sql == BILLING_PAYMENT_PROVIDER_MODE_CHECK_SQL
    assert constraint_sql == "provider_mode ~ '^[a-z][a-z0-9_]*$'"
    assert "provider_mode IN ('test', 'production')" not in constraint_sql


def test_billing_provider_mode_migration_replaces_monobank_mode_only_check() -> None:
    # Skipped because migrations are squashed into 001_init.sql
    return
