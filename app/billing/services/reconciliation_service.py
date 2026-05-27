from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Protocol, cast

from app.billing.services.fiscal_check_delivery import ensure_success_fiscal_checks_with_event
from app.billing.services.payment_status import (
    BillingPaymentStatusBillingPort,
    BillingPaymentStatusDatabasePort,
    PostUpgradeRescanCallback,
    apply_provider_status_payload,
    apply_subscription_purchase_projection,
    maybe_queue_post_upgrade_google_doc_rescan,
)
from app.billing.services.provider_port import (
    BillingInvoiceStatusProviderFactory,
    BillingInvoiceStatusProviderPort,
    BillingProviderAuditContext,
    BillingReceiptFiscalProviderFactory,
    require_billing_invoice_status_provider_factory,
)
from app.billing.services.provider_runtime import resolve_payment_provider_runtime
from app.billing.services.receipt_retrieval_service import (
    BillingReceiptRetrievalBillingPort,
    BillingReceiptRetrievalDatabasePort,
    BillingReceiptRetrievalService,
)
from app.domain.billing.constants import BILLING_TERMINAL_STATUSES
from app.time_utils import TimeService

BILLING_RECONCILIATION_TASK_TYPE = "billing_payment_reconciliation"
BILLING_SUBSCRIPTION_RECOVERY_TASK_TYPE = "billing_subscription_purchase_recovery"
BILLING_SUCCESS_RECHECK_TASK_TYPE = "billing_payment_success_recheck"
BILLING_SUBSCRIPTION_RECOVERY_STATE_KEY = "billing.subscription_purchase_recovery"
BILLING_SUCCESS_RECHECK_STATE_KEY = "billing.payment_success_recheck"
BILLING_SUCCESS_RECHECK_LEGACY_STATE_KEY = "billing.monobank_success_recheck"


class BillingReconciliationTaskLogPort(Protocol):
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


class BillingReconciliationAppSettingsPort(Protocol):
    def get_value(self, key: str) -> dict[str, Any] | None: ...


class BillingReconciliationRuntimeStatePort(Protocol):
    def get(self, key: str) -> dict[str, Any] | None: ...

    def set(self, key: str, value_json: dict[str, Any], current_time: datetime) -> None: ...


class BillingReconciliationProjectedPaymentsBillingPort(Protocol):
    def list_active_subscription_purchase_payments_requiring_projection(
        self,
        *,
        current_time: datetime,
        limit: int = 100,
    ) -> list[dict[str, Any]]: ...


class BillingReconciliationBillingPort(
    BillingPaymentStatusBillingPort, BillingReceiptRetrievalBillingPort, Protocol
):
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

    def list_non_terminal_payments(self, *, limit: int = 100) -> list[dict[str, Any]]: ...

    def list_success_payments_requiring_subscription_recovery_today(
        self,
        *,
        current_time: datetime,
        limit: int = 100,
    ) -> list[dict[str, Any]]: ...

    def list_success_payments_due_for_recheck(
        self,
        *,
        current_time: datetime,
        window_days: int,
        interval_days: int,
        limit: int = 100,
    ) -> list[dict[str, Any]]: ...

    def mark_payment_success_rechecked(
        self, payment_id: int, *, current_time: datetime
    ) -> None: ...


class BillingReconciliationDatabasePort(
    BillingPaymentStatusDatabasePort,
    BillingReceiptRetrievalDatabasePort,
    Protocol,
):
    billing: BillingReconciliationBillingPort
    task_logs: BillingReconciliationTaskLogPort
    app_settings: BillingReconciliationAppSettingsPort
    app_runtime_state: BillingReconciliationRuntimeStatePort


class BillingReconciliationIntervalDatabasePort(Protocol):
    app_runtime_state: BillingReconciliationRuntimeStatePort


class BillingReconciliationService:
    def __init__(
        self,
        db: BillingReconciliationDatabasePort,
        time_service: TimeService,
        *,
        billing_provider_factory: BillingInvoiceStatusProviderFactory | None = None,
        billing_receipt_fiscal_provider_factory: BillingReceiptFiscalProviderFactory
        | None = None,
        post_upgrade_rescan: PostUpgradeRescanCallback | None = None,
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.billing_invoice_status_provider_factory = (
            billing_provider_factory
        )
        self.billing_receipt_fiscal_provider_factory = (
            billing_receipt_fiscal_provider_factory
            or cast(BillingReceiptFiscalProviderFactory | None, billing_provider_factory)
        )
        self.post_upgrade_rescan = post_upgrade_rescan
        self.receipt_retrieval = BillingReceiptRetrievalService(
            db,
            time_service,
            billing_provider_factory=self.billing_receipt_fiscal_provider_factory,
        )

    def process_non_terminal_payments(self, *, limit: int = 100) -> dict[str, Any]:
        current_time = self.time_service.now()
        task_log = self.db.task_logs.create(
            task_type=BILLING_RECONCILIATION_TASK_TYPE,
            status="processing",
            current_time=current_time,
            description="Processing non-terminal billing payments.",
        )
        try:
            summary = self._process_payments(limit=limit)
        except Exception as error:
            self.db.task_logs.update(
                int(task_log["id"]),
                status="fatal",
                current_time=self.time_service.now(),
                description="Failed to process non-terminal billing payments.",
                error_text=str(error),
                result_json={},
            )
            raise
        self.db.task_logs.update(
            int(task_log["id"]),
            status="success",
            current_time=self.time_service.now(),
            description=build_reconciliation_description(summary),
            result_json=summary,
        )
        return {**summary, "task_log_id": task_log["id"]}

    def process_due_internal_recovery(self, *, limit: int = 100) -> dict[str, Any]:
        current_time = self.time_service.now()
        settings = self._runtime_settings()
        if not should_run_interval(
            self.db,
            BILLING_SUBSCRIPTION_RECOVERY_STATE_KEY,
            current_time=current_time,
            interval_seconds=int(settings["subscription_recovery_interval_seconds"]),
        ):
            return {"skipped": True, "reason": "not_due"}
        task_log = self.db.task_logs.create(
            task_type=BILLING_SUBSCRIPTION_RECOVERY_TASK_TYPE,
            status="processing",
            current_time=current_time,
            description="Recovering successful billing payments without subscription purchase ledger.",
        )
        try:
            payments = self.db.billing.list_success_payments_requiring_subscription_recovery_today(
                current_time=current_time,
                limit=limit,
            )
            if hasattr(
                self.db.billing, "list_active_subscription_purchase_payments_requiring_projection"
            ):
                projected_payments_billing = cast(
                    BillingReconciliationProjectedPaymentsBillingPort, self.db.billing
                )
                projected_payments = projected_payments_billing.list_active_subscription_purchase_payments_requiring_projection(
                    current_time=current_time,
                    limit=limit,
                )
                payments = dedupe_payments([*payments, *projected_payments])[:limit]
            recovered: list[int] = []
            errors: list[dict[str, Any]] = []
            for payment in payments:
                try:
                    subscription = apply_subscription_purchase_projection(
                        self.db,
                        payment=payment,
                        current_time=current_time,
                    )
                    self.db.billing.create_payment_event(
                        payment_id=int(payment["id"]),
                        event_type="subscription_recovered",
                        source="billing_subscription_recovery",
                        provider_status="success",
                        payload_json={"subscription": subscription},
                        current_time=current_time,
                    )
                    maybe_queue_post_upgrade_google_doc_rescan(
                        self.db,
                        payment=payment,
                        subscription=subscription,
                        current_time=current_time,
                        source="billing_subscription_recovery",
                        provider_status="success",
                        post_upgrade_rescan=self.post_upgrade_rescan,
                    )
                    recovered.append(int(payment["id"]))
                except Exception as error:
                    errors.append({"payment_id": payment.get("id"), "error": str(error)})
            summary = {
                "checked_count": len(payments),
                "recovered_count": len(recovered),
                "recovered_payment_ids": recovered[:50],
                "error_count": len(errors),
            }
            if errors:
                summary["errors"] = errors[:20]
            self.db.task_logs.update(
                int(task_log["id"]),
                status="success",
                current_time=self.time_service.now(),
                description=build_subscription_recovery_description(summary),
                result_json=summary,
            )
            mark_interval_run(
                self.db, BILLING_SUBSCRIPTION_RECOVERY_STATE_KEY, current_time=current_time
            )
            return {**summary, "task_log_id": task_log["id"]}
        except Exception as error:
            self.db.task_logs.update(
                int(task_log["id"]),
                status="fatal",
                current_time=self.time_service.now(),
                description="Failed to recover successful billing payments.",
                error_text=str(error),
                result_json={},
            )
            raise

    def process_due_success_recheck(self, *, limit: int = 100) -> dict[str, Any]:
        current_time = self.time_service.now()
        settings = self._runtime_settings()
        if not should_run_daily_window(
            self.db,
            BILLING_SUCCESS_RECHECK_STATE_KEY,
            current_time=current_time,
            interval_days=int(settings["success_recheck_interval_days"]),
            run_hour=int(settings["success_recheck_hour"]),
            legacy_key=BILLING_SUCCESS_RECHECK_LEGACY_STATE_KEY,
        ):
            return {"skipped": True, "reason": "not_due"}
        task_log = self.db.task_logs.create(
            task_type=BILLING_SUCCESS_RECHECK_TASK_TYPE,
            status="processing",
            current_time=current_time,
            description="Rechecking successful billing payments for late reverse statuses.",
        )
        try:
            summary = self._process_success_recheck(
                limit=limit,
                window_days=int(settings["success_recheck_window_days"]),
                interval_days=int(settings["success_recheck_interval_days"]),
            )
            self.db.task_logs.update(
                int(task_log["id"]),
                status="success",
                current_time=self.time_service.now(),
                description=build_success_recheck_description(summary),
                result_json=summary,
            )
            mark_interval_run(self.db, BILLING_SUCCESS_RECHECK_STATE_KEY, current_time=current_time)
            return {**summary, "task_log_id": task_log["id"]}
        except Exception as error:
            self.db.task_logs.update(
                int(task_log["id"]),
                status="fatal",
                current_time=self.time_service.now(),
                description="Failed to recheck successful billing payments.",
                error_text=str(error),
                result_json={},
            )
            raise

    def _process_payments(self, *, limit: int) -> dict[str, Any]:
        payments = self.db.billing.list_non_terminal_payments(limit=limit)
        summary: dict[str, Any] = {
            "checked_count": 0,
            "updated_count": 0,
            "terminal_count": 0,
            "error_count": 0,
        }
        errors: list[dict[str, Any]] = []
        for payment in payments:
            summary["checked_count"] += 1
            previous_status = str(payment["status"])
            try:
                updated_payment = self._poll_payment(
                    payment,
                    source_place="reconciliation_worker",
                    event_source="billing_payment_reconciliation",
                )
            except Exception as error:
                summary["error_count"] += 1
                errors.append({"payment_id": payment.get("id"), "error": str(error)})
                self.db.billing.create_payment_event(
                    payment_id=int(payment["id"]),
                    event_type="reconciliation_error",
                    source="billing_payment_reconciliation",
                    provider_status=None,
                    payload_json={"error": str(error)},
                    current_time=self.time_service.now(),
                )
                continue
            if updated_payment is None:
                continue
            if str(updated_payment["status"]) != previous_status:
                summary["updated_count"] += 1
            if str(updated_payment["status"]) in BILLING_TERMINAL_STATUSES:
                summary["terminal_count"] += 1
        if errors:
            summary["errors"] = errors[:20]
        return summary

    def _process_success_recheck(
        self, *, limit: int, window_days: int, interval_days: int
    ) -> dict[str, Any]:
        payments = self.db.billing.list_success_payments_due_for_recheck(
            current_time=self.time_service.now(),
            window_days=window_days,
            interval_days=interval_days,
            limit=limit,
        )
        summary: dict[str, Any] = {
            "checked_count": 0,
            "updated_count": 0,
            "terminal_reverse_count": 0,
            "error_count": 0,
        }
        errors: list[dict[str, Any]] = []
        for payment in payments:
            summary["checked_count"] += 1
            previous_status = str(payment["status"])
            try:
                updated_payment = self._poll_payment(
                    payment,
                    source_place="success_recheck_worker",
                    event_source="billing_payment_success_recheck",
                )
                self.db.billing.mark_payment_success_rechecked(
                    int(payment["id"]), current_time=self.time_service.now()
                )
            except Exception as error:
                summary["error_count"] += 1
                errors.append({"payment_id": payment.get("id"), "error": str(error)})
                continue
            if updated_payment is None:
                continue
            if str(updated_payment["status"]) != previous_status:
                summary["updated_count"] += 1
            if previous_status == "success" and str(updated_payment["status"]) in {
                "failure",
                "reversed",
                "expired",
            }:
                summary["terminal_reverse_count"] += 1
        if errors:
            summary["errors"] = errors[:20]
        return summary

    def _poll_payment(
        self,
        payment: dict[str, Any],
        *,
        source_place: str,
        event_source: str,
    ) -> dict[str, Any] | None:
        provider_invoice_id = str(payment.get("provider_invoice_id") or "").strip()
        if not provider_invoice_id:
            return None
        provider_runtime = resolve_payment_provider_runtime(payment)
        provider = self._billing_provider(
            provider_runtime.provider_key,
            provider_runtime.provider_mode,
        )
        payload = provider.get_invoice_status(
            provider_invoice_id,
            audit_context=BillingProviderAuditContext(
                source_place=source_place,
                actor_user_uuid=payment.get("user_uuid"),
                telegram_user_id=int(payment["telegram_user_id"]),
                payment_id=int(payment["id"]),
                order_reference=payment.get("provider_reference"),
                invoice_id=provider_invoice_id,
            ),
        )
        provider_status = provider.resolve_payment_status(payload)
        updated_payment = apply_provider_status_payload(
            self.db,
            self.time_service,
            payment=payment,
            provider_status=provider_status,
            payload=payload,
            source=event_source,
            post_upgrade_rescan=self.post_upgrade_rescan,
        )
        if updated_payment is not None and updated_payment.get("status") == "success":
            ensure_success_fiscal_checks_with_event(
                db=self.db,
                time_service=self.time_service,
                receipt_retrieval=self.receipt_retrieval,
                payment=updated_payment,
                source=event_source,
                source_place=f"{source_place}_fiscal_check",
            )
        return updated_payment

    def _billing_provider(
        self, provider_key: str, provider_mode: str
    ) -> BillingInvoiceStatusProviderPort:
        return require_billing_invoice_status_provider_factory(
            self.billing_invoice_status_provider_factory
        )(provider_key=provider_key, provider_mode=provider_mode)

    def _runtime_settings(self) -> dict[str, Any]:
        from app.billing.runtime_settings import read_billing_runtime_settings

        return read_billing_runtime_settings(self.db)


def build_reconciliation_description(summary: dict[str, Any]) -> str:
    return (
        "Processed non-terminal billing payments: "
        f"checked={summary.get('checked_count', 0)}, "
        f"updated={summary.get('updated_count', 0)}, "
        f"terminal={summary.get('terminal_count', 0)}, "
        f"errors={summary.get('error_count', 0)}."
    )


def build_subscription_recovery_description(summary: dict[str, Any]) -> str:
    return (
        "Recovered successful billing payments without subscription purchase ledger: "
        f"checked={summary.get('checked_count', 0)}, "
        f"recovered={summary.get('recovered_count', 0)}, "
        f"errors={summary.get('error_count', 0)}."
    )


def build_success_recheck_description(summary: dict[str, Any]) -> str:
    return (
        "Rechecked successful billing payments: "
        f"checked={summary.get('checked_count', 0)}, "
        f"updated={summary.get('updated_count', 0)}, "
        f"reversed={summary.get('terminal_reverse_count', 0)}, "
        f"errors={summary.get('error_count', 0)}."
    )


def dedupe_payments(payments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[int] = set()
    result: list[dict[str, Any]] = []
    for payment in payments:
        payment_id = int(payment["id"])
        if payment_id in seen:
            continue
        seen.add(payment_id)
        result.append(payment)
    return result


def should_run_interval(
    db: BillingReconciliationIntervalDatabasePort,
    key: str,
    *,
    current_time: datetime,
    interval_seconds: int,
    legacy_key: str | None = None,
) -> bool:
    last_run_at = read_last_run_at(db, key, legacy_key=legacy_key)
    if last_run_at is None:
        return True
    return current_time >= last_run_at + timedelta(seconds=max(int(interval_seconds), 1))


def should_run_daily_window(
    db: BillingReconciliationIntervalDatabasePort,
    key: str,
    *,
    current_time: datetime,
    interval_days: int,
    run_hour: int,
    legacy_key: str | None = None,
) -> bool:
    if current_time.hour < int(run_hour):
        return False
    last_run_at = read_last_run_at(db, key, legacy_key=legacy_key)
    if last_run_at is None:
        return True
    return current_time.date() >= (last_run_at + timedelta(days=max(int(interval_days), 1))).date()


def mark_interval_run(
    db: BillingReconciliationIntervalDatabasePort, key: str, *, current_time: datetime
) -> None:
    if not hasattr(db, "app_runtime_state"):
        return
    db.app_runtime_state.set(
        key, {"last_run_at": current_time.isoformat()}, current_time=current_time
    )


def read_last_run_at(
    db: BillingReconciliationIntervalDatabasePort,
    key: str,
    *,
    legacy_key: str | None = None,
) -> datetime | None:
    if not hasattr(db, "app_runtime_state"):
        return None
    state = db.app_runtime_state.get(key)
    last_run_at = parse_datetime((state or {}).get("value_json", {}).get("last_run_at"))
    if last_run_at is not None or legacy_key is None:
        return last_run_at
    legacy_state = db.app_runtime_state.get(legacy_key)
    return parse_datetime((legacy_state or {}).get("value_json", {}).get("last_run_at"))


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None
