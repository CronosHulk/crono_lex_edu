from __future__ import annotations

from typing import Any

import pytest

from app.billing.services.history_service import (
    BillingPaymentHistoryProfileNotFoundError,
    BillingPaymentHistoryService,
)


class FakeUserProfiles:
    def __init__(self, profile: dict[str, Any] | None = None) -> None:
        self.profile = profile
        self.lookup_calls: list[int] = []

    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        self.lookup_calls.append(telegram_user_id)
        return self.profile


class FakeBillingRepository:
    def __init__(self) -> None:
        self.client_payment_calls: list[dict[str, Any]] = []

    def list_client_payments_for_user(self, user_uuid: str, *, page: int, page_size: int) -> dict[str, Any]:
        self.client_payment_calls.append({"user_uuid": user_uuid, "page": page, "page_size": page_size})
        return {"items": [], "total": 0, "page": page, "page_size": page_size, "pages": 0}


class FakeDb:
    def __init__(self, profile: dict[str, Any] | None = None) -> None:
        self.user_profiles = FakeUserProfiles(profile)
        self.billing = FakeBillingRepository()


def test_billing_history_uses_user_uuid_and_normalizes_pagination() -> None:
    db = FakeDb()
    service = BillingPaymentHistoryService(db)

    result = service.list_client_payments({"telegram_user_id": "42", "user_uuid": "user-uuid"}, page=0, page_size=100)

    assert result == {"items": [], "total": 0, "page": 1, "page_size": 50, "pages": 0}
    assert db.user_profiles.lookup_calls == []
    assert db.billing.client_payment_calls == [{"user_uuid": "user-uuid", "page": 1, "page_size": 50}]


def test_billing_history_falls_back_to_profile_uuid() -> None:
    db = FakeDb({"id": "profile-uuid"})
    service = BillingPaymentHistoryService(db)

    service.list_client_payments({"telegram_user_id": "42"}, page=2, page_size=20)

    assert db.user_profiles.lookup_calls == [42]
    assert db.billing.client_payment_calls == [{"user_uuid": "profile-uuid", "page": 2, "page_size": 20}]


def test_billing_history_raises_non_http_missing_profile_error() -> None:
    db = FakeDb(None)
    service = BillingPaymentHistoryService(db)

    with pytest.raises(BillingPaymentHistoryProfileNotFoundError) as exc_info:
        service.list_client_payments({"telegram_user_id": "42"}, page=1, page_size=20)

    assert exc_info.value.detail == "User profile not found"
    assert str(exc_info.value) == "User profile not found"
    assert not hasattr(exc_info.value, "status_code")
