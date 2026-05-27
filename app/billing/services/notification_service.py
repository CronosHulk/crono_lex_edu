from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.billing.helpers.receipt_notifications import (
    build_payment_notification_screen,
    build_receipt_admin_alert_screen,
    build_receipt_delivery_screen,
    build_receipt_retry_description,
)
from app.billing.runtime_settings import read_billing_runtime_settings
from app.billing.services.provider_port import BillingReceiptFiscalProviderFactory
from app.billing.services.receipt_retrieval_service import (
    BillingReceiptRetrievalBillingPort,
    BillingReceiptRetrievalDatabasePort,
    BillingReceiptRetrievalService,
    receipt_is_deliverable,
)
from app.billing.services.receipt_storage_port import BillingReceiptStorageProvider
from app.contracts import ImportDispatchNotificationModel
from app.domain.billing.constants import BILLING_TERMINAL_STATUSES
from app.time_utils import TimeService

BILLING_RECEIPT_RETRY_TASK_TYPE = "billing_receipt_retry"
BILLING_RECEIPT_RETRY_STATE_KEY = "billing.receipt_retry"
BILLING_RECEIPT_RETRY_LEGACY_STATE_KEY = "billing.monobank_receipt_retry"


class UserProfileReader(Protocol):
    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None: ...


class BillingBotNotificationBillingPort(BillingReceiptRetrievalBillingPort, Protocol):
    def claim_due_bot_notifications(
        self,
        *,
        current_time: datetime,
        limit: int = 50,
        claim_timeout_minutes: int = 10,
    ) -> list[dict[str, Any]]: ...

    def get_payment_by_id(self, payment_id: int) -> dict[str, Any] | None: ...

    def mark_bot_notification_sent(
        self, notification_id: int, *, current_time: datetime
    ) -> None: ...

    def mark_bot_notification_skipped(
        self,
        notification_id: int,
        *,
        error_text: str,
        current_time: datetime,
    ) -> None: ...

    def mark_bot_notification_failed(
        self,
        notification_id: int,
        *,
        error_text: str,
        current_time: datetime,
    ) -> None: ...

    def set_bot_notification_receipt_ids(
        self,
        notification_id: int,
        receipt_ids: list[int],
        *,
        current_time: datetime,
    ) -> None: ...

    def get_bot_notification_by_id(self, notification_id: int) -> dict[str, Any] | None: ...

    def mark_receipt_deliveries_sent_by_ids(
        self,
        receipt_ids: list[int],
        *,
        current_time: datetime,
    ) -> None: ...

    def mark_receipt_delivery_sent(self, receipt_id: int, *, current_time: datetime) -> None: ...

    def mark_receipt_delivery_failed(
        self,
        receipt_id: int,
        *,
        error_text: str,
        current_time: datetime,
    ) -> None: ...

    def list_success_payments_requiring_receipt_retry(
        self,
        *,
        current_time: datetime,
        limit: int = 100,
        max_attempts: int | None = None,
    ) -> list[dict[str, Any]]: ...

    def create_payment_event(
        self,
        *,
        payment_id: int | None,
        event_type: str,
        source: str,
        provider_status: str | None,
        payload_json: dict[str, Any],
        current_time: datetime,
    ) -> dict[str, Any]: ...

    def claim_due_receipt_delivery_notifications(
        self,
        *,
        current_time: datetime,
        limit: int = 50,
        claim_timeout_minutes: int = 10,
        exclude_receipt_ids: set[int] | None = None,
    ) -> list[dict[str, Any]]: ...

    def claim_receipts_requiring_admin_alert(
        self,
        *,
        current_time: datetime,
        max_retry_count: int,
        limit: int = 50,
        claim_timeout_minutes: int = 10,
    ) -> list[dict[str, Any]]: ...

    def mark_receipt_admin_alert_sent(self, receipt_id: int, *, current_time: datetime) -> None: ...

    def mark_receipt_admin_alert_failed(
        self,
        receipt_id: int,
        *,
        error_text: str,
        current_time: datetime,
    ) -> None: ...


class BillingBotNotificationTaskLogPort(Protocol):
    def create(
        self,
        *,
        task_type: str,
        status: str,
        current_time: datetime,
        description: str | None = None,
    ) -> dict[str, Any]: ...

    def update(
        self,
        task_log_id: int,
        *,
        status: str,
        current_time: datetime,
        description: str | None = None,
        error_text: str | None = None,
        result_json: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None: ...


class BillingBotNotificationAppSettingsPort(Protocol):
    def get_value(self, key: str) -> dict[str, Any] | None: ...


class BillingBotNotificationRuntimeStatePort(Protocol):
    def get(self, key: str) -> dict[str, Any] | None: ...

    def set(self, key: str, value_json: dict[str, Any], current_time: datetime) -> None: ...


class BillingBotNotificationDatabasePort(BillingReceiptRetrievalDatabasePort, Protocol):
    billing: BillingBotNotificationBillingPort
    user_profiles: UserProfileReader
    task_logs: BillingBotNotificationTaskLogPort
    app_settings: BillingBotNotificationAppSettingsPort
    app_runtime_state: BillingBotNotificationRuntimeStatePort


class BillingBotNotificationService:
    def __init__(
        self,
        db: BillingBotNotificationDatabasePort,
        time_service: TimeService,
        billing_receipt_storage_provider: BillingReceiptStorageProvider,
        *,
        user_profiles: UserProfileReader | None = None,
        billing_receipt_fiscal_provider_factory: BillingReceiptFiscalProviderFactory
        | None = None,
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.billing_receipt_storage_provider = billing_receipt_storage_provider
        self.user_profiles = user_profiles or db.user_profiles
        self.billing_receipt_fiscal_provider_factory = billing_receipt_fiscal_provider_factory
        self.receipt_retrieval = BillingReceiptRetrievalService(
            db,
            time_service,
            billing_provider_factory=billing_receipt_fiscal_provider_factory,
        )

    def dispatch_due_billing_notifications(self) -> list[ImportDispatchNotificationModel]:
        current_time = self.time_service.now()
        notifications: list[ImportDispatchNotificationModel] = []
        for row in self.db.billing.claim_due_bot_notifications(current_time=current_time):
            notification_id = int(row["id"])
            try:
                payment = self.db.billing.get_payment_by_id(int(row["payment_id"]))
                if payment is None:
                    self.db.billing.mark_bot_notification_skipped(
                        notification_id,
                        error_text="Billing payment was not found",
                        current_time=current_time,
                    )
                    continue
                payment_snapshot = apply_notification_status_snapshot(payment, row)
                profile = self.user_profiles.get_profile(int(payment["telegram_user_id"]))
                chat_id = profile.get("chat_id") if profile is not None else None
                if chat_id is None:
                    self.db.billing.mark_bot_notification_skipped(
                        notification_id,
                        error_text="User profile does not have a Telegram chat_id",
                        current_time=current_time,
                    )
                    continue
                receipts = self.db.billing.list_payment_receipts(int(payment_snapshot["id"]))
                self.db.billing.set_bot_notification_receipt_ids(
                    notification_id,
                    [],
                    current_time=current_time,
                )
                notifications.append(
                    ImportDispatchNotificationModel(
                        telegram_user_id=int(payment["telegram_user_id"]),
                        chat_id=int(chat_id),
                        screen=build_payment_notification_screen(payment_snapshot, receipts),
                        disable_notification=False,
                        delivery_kind="billing_bot_notification",
                        delivery_id=notification_id,
                    )
                )
            except Exception as error:
                self.db.billing.mark_bot_notification_failed(
                    notification_id,
                    error_text=f"{type(error).__name__}: {error}"[:1000],
                    current_time=current_time,
                )
        return [
            *notifications,
            *self._dispatch_due_receipt_deliveries(
                current_time=current_time,
                exclude_receipt_ids=set(),
            ),
            *self._dispatch_due_receipt_admin_alerts(current_time=current_time),
        ]

    def save_bot_notification_delivery_result(
        self,
        notification_id: int,
        *,
        is_sent: bool,
        error_text: str | None,
    ) -> None:
        current_time = self.time_service.now()
        if is_sent:
            self.db.billing.mark_bot_notification_sent(notification_id, current_time=current_time)
            notification = self.db.billing.get_bot_notification_by_id(notification_id)
            if (
                notification is not None
                and str(notification.get("status_snapshot") or "") == "success"
            ):
                self.db.billing.mark_receipt_deliveries_sent_by_ids(
                    notification.get("receipt_ids", []),
                    current_time=current_time,
                )
            return
        self.db.billing.mark_bot_notification_failed(
            notification_id,
            error_text=error_text or "Telegram delivery failed",
            current_time=current_time,
        )

    def save_receipt_delivery_result(
        self,
        receipt_id: int,
        *,
        is_sent: bool,
        error_text: str | None,
    ) -> None:
        current_time = self.time_service.now()
        if is_sent:
            self.db.billing.mark_receipt_delivery_sent(receipt_id, current_time=current_time)
            return
        self.db.billing.mark_receipt_delivery_failed(
            receipt_id,
            error_text=error_text or "Telegram delivery failed",
            current_time=current_time,
        )

    def save_receipt_admin_alert_result(
        self,
        receipt_id: int,
        *,
        is_sent: bool,
        error_text: str | None,
    ) -> None:
        current_time = self.time_service.now()
        if is_sent:
            self.db.billing.mark_receipt_admin_alert_sent(receipt_id, current_time=current_time)
            return
        self.db.billing.mark_receipt_admin_alert_failed(
            receipt_id,
            error_text=error_text or "Telegram admin alert delivery failed",
            current_time=current_time,
        )

    def process_due_receipt_retries(self, *, limit: int = 100) -> dict[str, Any]:
        from app.billing.services.reconciliation_service import (
            mark_interval_run,
            should_run_interval,
        )

        current_time = self.time_service.now()
        settings = read_billing_runtime_settings(self.db)
        if not should_run_interval(
            self.db,
            BILLING_RECEIPT_RETRY_STATE_KEY,
            current_time=current_time,
            interval_seconds=int(settings["receipt_retry_interval_seconds"]),
            legacy_key=BILLING_RECEIPT_RETRY_LEGACY_STATE_KEY,
        ):
            return {"skipped": True, "reason": "not_due"}
        task_log = self.db.task_logs.create(
            task_type=BILLING_RECEIPT_RETRY_TASK_TYPE,
            status="processing",
            current_time=current_time,
            description="Retrying billing receipt retrieval for successful payments.",
        )
        try:
            payments = self.db.billing.list_success_payments_requiring_receipt_retry(
                current_time=current_time,
                limit=limit,
                max_attempts=int(settings["receipt_retry_max_attempts"]),
            )
            summary: dict[str, Any] = {
                "checked_count": 0,
                "done_count": 0,
                "pending_count": 0,
                "exhausted_count": 0,
                "error_count": 0,
            }
            for payment in payments:
                summary["checked_count"] += 1
                try:
                    receipts = self.receipt_retrieval.ensure_success_receipts(
                        payment,
                        source_place="receipt_retry_worker",
                        retry_delay_seconds=int(settings["receipt_retry_delay_seconds"]),
                        max_attempts=int(settings["receipt_retry_max_attempts"]),
                    )
                except Exception as error:
                    summary["error_count"] += 1
                    self.db.billing.create_payment_event(
                        payment_id=int(payment["id"]),
                        event_type="receipt_retry_error",
                        source="billing_receipt_retry",
                        provider_status=None,
                        payload_json={
                            "error_type": type(error).__name__,
                            "error_text": str(error)[:1000],
                        },
                        current_time=self.time_service.now(),
                    )
                    continue
                if any(receipt_is_deliverable(row) for row in receipts):
                    summary["done_count"] += 1
                    continue
                if any(
                    int(row.get("retry_count") or 0) >= int(settings["receipt_retry_max_attempts"])
                    for row in receipts
                ):
                    summary["exhausted_count"] += 1
                else:
                    summary["pending_count"] += 1
            self.db.task_logs.update(
                int(task_log["id"]),
                status="success",
                current_time=self.time_service.now(),
                description=build_receipt_retry_description(summary),
                result_json=summary,
            )
            mark_interval_run(self.db, BILLING_RECEIPT_RETRY_STATE_KEY, current_time=current_time)
            return {**summary, "task_log_id": task_log["id"]}
        except Exception as error:
            self.db.task_logs.update(
                int(task_log["id"]),
                status="fatal",
                current_time=self.time_service.now(),
                description="Failed to retry billing receipt retrieval.",
                error_text=str(error),
                result_json={},
            )
            raise

    def _dispatch_due_receipt_deliveries(
        self,
        *,
        current_time: Any,
        exclude_receipt_ids: set[int] | None = None,
    ) -> list[ImportDispatchNotificationModel]:
        notifications: list[ImportDispatchNotificationModel] = []
        for receipt in self.db.billing.claim_due_receipt_delivery_notifications(
            current_time=current_time,
            exclude_receipt_ids=exclude_receipt_ids or set(),
        ):
            payment = self.db.billing.get_payment_by_id(int(receipt["payment_id"]))
            if payment is None:
                self.db.billing.mark_receipt_delivery_failed(
                    int(receipt["id"]),
                    error_text="Billing payment was not found",
                    current_time=current_time,
                )
                continue
            profile = self.user_profiles.get_profile(int(payment["telegram_user_id"]))
            chat_id = profile.get("chat_id") if profile is not None else None
            if chat_id is None:
                self.db.billing.mark_receipt_delivery_failed(
                    int(receipt["id"]),
                    error_text="User profile does not have a Telegram chat_id",
                    current_time=current_time,
                )
                continue
            try:
                notifications.append(
                    ImportDispatchNotificationModel(
                        telegram_user_id=int(payment["telegram_user_id"]),
                        chat_id=int(chat_id),
                        screen=build_receipt_delivery_screen(
                            payment,
                            receipt,
                            billing_receipt_storage_provider=self.billing_receipt_storage_provider,
                        ),
                        disable_notification=False,
                        delivery_kind="billing_receipt_delivery",
                        delivery_id=int(receipt["id"]),
                    )
                )
            except Exception as error:
                self.db.billing.mark_receipt_delivery_failed(
                    int(receipt["id"]),
                    error_text=f"{type(error).__name__}: {error}"[:1000],
                    current_time=current_time,
                )
        return notifications

    def _dispatch_due_receipt_admin_alerts(
        self, *, current_time: Any
    ) -> list[ImportDispatchNotificationModel]:
        settings = read_billing_runtime_settings(self.db)
        list_admins = getattr(self.user_profiles, "list_super_admin_profiles", None)
        if list_admins is None:
            return []
        notifications: list[ImportDispatchNotificationModel] = []
        for receipt in self.db.billing.claim_receipts_requiring_admin_alert(
            current_time=current_time,
            max_retry_count=int(settings["receipt_retry_max_attempts"]),
        ):
            payment = self.db.billing.get_payment_by_id(int(receipt["payment_id"]))
            if payment is None:
                self.db.billing.mark_receipt_admin_alert_failed(
                    int(receipt["id"]),
                    error_text="Billing payment was not found",
                    current_time=current_time,
                )
                continue
            admin_profiles = list_admins()
            deliverable_admin_profiles = [
                row
                for row in admin_profiles
                if row.get("chat_id") is not None and row.get("telegram_user_id") is not None
            ]
            if not deliverable_admin_profiles:
                self.db.billing.mark_receipt_admin_alert_failed(
                    int(receipt["id"]),
                    error_text="No superadmin Telegram chat_id is available",
                    current_time=current_time,
                )
                continue
            self.db.billing.create_payment_event(
                payment_id=int(payment["id"]),
                event_type="receipt_retry_exhausted_admin_alert",
                source="billing_receipt_retry",
                provider_status=str(payment.get("status") or ""),
                payload_json={
                    "receipt_id": receipt["id"],
                    "admin_count": len(deliverable_admin_profiles),
                },
                current_time=current_time,
            )
            for admin_profile in deliverable_admin_profiles:
                notifications.append(
                    ImportDispatchNotificationModel(
                        telegram_user_id=int(admin_profile["telegram_user_id"]),
                        chat_id=int(admin_profile["chat_id"]),
                        screen=build_receipt_admin_alert_screen(payment, receipt),
                        disable_notification=False,
                        delivery_kind="billing_receipt_admin_alert",
                        delivery_id=int(receipt["id"]),
                    )
                )
        return notifications


def apply_notification_status_snapshot(
    payment: dict[str, Any], notification: dict[str, Any]
) -> dict[str, Any]:
    status_snapshot = str(notification.get("status_snapshot") or "").strip()
    if status_snapshot not in BILLING_TERMINAL_STATUSES:
        return payment
    return {**payment, "status": status_snapshot}
