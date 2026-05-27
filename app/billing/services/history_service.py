from __future__ import annotations

from typing import Any, Protocol

from app.subscriptions.user_entitlements import read_user_uuid


class BillingPaymentHistoryProfileNotFoundError(LookupError):
    def __init__(self, detail: str = "User profile not found") -> None:
        super().__init__(detail)
        self.detail = detail


class BillingHistoryUserProfilesPort(Protocol):
    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None: ...


class BillingHistoryBillingPort(Protocol):
    def list_client_payments_for_user(self, user_uuid: str, *, page: int, page_size: int) -> dict[str, Any]: ...


class BillingPaymentHistoryDatabasePort(Protocol):
    user_profiles: BillingHistoryUserProfilesPort
    billing: BillingHistoryBillingPort


class BillingPaymentHistoryService:
    def __init__(self, db: BillingPaymentHistoryDatabasePort) -> None:
        self.db = db

    def list_client_payments(self, user: dict[str, Any], *, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        user_uuid = read_user_uuid(user)
        if not user_uuid:
            profile = self.db.user_profiles.get_profile(int(user["telegram_user_id"]))
            user_uuid = read_user_uuid(profile)
        if not user_uuid:
            raise BillingPaymentHistoryProfileNotFoundError()
        normalized_page = max(int(page), 1)
        normalized_page_size = max(min(int(page_size), 50), 1)
        return self.db.billing.list_client_payments_for_user(
            str(user_uuid),
            page=normalized_page,
            page_size=normalized_page_size,
        )
