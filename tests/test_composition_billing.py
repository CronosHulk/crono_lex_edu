from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import ANY

from app.composition.billing import (
    configure_billing_notification_runtime,
    configure_billing_reconciliation_runtime,
    configure_billing_webhook_runtime,
)


class FakeBillingWebhookService:
    calls: list[dict[str, Any]] = []

    def __init__(
        self,
        db: object,
        time_service: object,
        *,
        billing_provider_factory: object,
        billing_receipt_fiscal_provider_factory: object,
        billing_webhook_public_key_provider_factory: object,
        monobank_webhook_adapter: object,
        monobank_signature_verifier: object,
        post_upgrade_rescan: object,
    ) -> None:
        self.__class__.calls.append(
            {
                "db": db,
                "time_service": time_service,
                "billing_provider_factory": billing_provider_factory,
                "billing_receipt_fiscal_provider_factory": billing_receipt_fiscal_provider_factory,
                "billing_webhook_public_key_provider_factory": (
                    billing_webhook_public_key_provider_factory
                ),
                "monobank_webhook_adapter": monobank_webhook_adapter,
                "monobank_signature_verifier": monobank_signature_verifier,
                "post_upgrade_rescan": post_upgrade_rescan,
            }
        )


class FakeBillingBotNotificationService:
    calls: list[dict[str, Any]] = []

    def __init__(
        self,
        db: object,
        time_service: object,
        *,
        billing_receipt_storage_provider: object,
        billing_receipt_fiscal_provider_factory: object,
    ) -> None:
        self.__class__.calls.append(
            {
                "db": db,
                "time_service": time_service,
                "billing_receipt_storage_provider": billing_receipt_storage_provider,
                "billing_receipt_fiscal_provider_factory": billing_receipt_fiscal_provider_factory,
            }
        )


class FakeBillingNotificationRuntimeService:
    calls: list[dict[str, Any]] = []

    def __init__(self, notification_service: object, *, dispatch_lock: object) -> None:
        self.__class__.calls.append(
            {"notification_service": notification_service, "dispatch_lock": dispatch_lock}
        )


class FakeBillingReconciliationService:
    calls: list[dict[str, Any]] = []

    def __init__(
        self,
        db: object,
        time_service: object,
        *,
        billing_provider_factory: object,
        billing_receipt_fiscal_provider_factory: object,
        post_upgrade_rescan: object,
    ) -> None:
        self.__class__.calls.append(
            {
                "db": db,
                "time_service": time_service,
                "billing_provider_factory": billing_provider_factory,
                "billing_receipt_fiscal_provider_factory": billing_receipt_fiscal_provider_factory,
                "post_upgrade_rescan": post_upgrade_rescan,
            }
        )


class FakeBillingReconciliationRuntimeService:
    calls: list[dict[str, Any]] = []

    def __init__(
        self,
        reconciliation_service: object,
        notification_service: object,
        *,
        dispatch_lock: object,
    ) -> None:
        self.__class__.calls.append(
            {
                "reconciliation_service": reconciliation_service,
                "notification_service": notification_service,
                "dispatch_lock": dispatch_lock,
            }
        )


def test_configure_billing_notification_runtime_builds_provider_factory_and_wires_notification_service(
    monkeypatch,
) -> None:
    FakeBillingBotNotificationService.calls = []
    FakeBillingNotificationRuntimeService.calls = []
    db = SimpleNamespace(
        settings=SimpleNamespace(app_billing_receipt_storage_dir="/tmp/billing-receipts"),
        billing=object(),
    )
    time_service = object()
    dispatch_lock = object()
    service = SimpleNamespace(time_service=time_service, dispatch_lock=dispatch_lock)
    build_factory_calls: list[dict[str, object]] = []
    provider_factory = object()

    def fake_build_billing_payment_provider_factory(**kwargs):
        build_factory_calls.append(kwargs)
        return provider_factory

    monkeypatch.setattr(
        "app.composition.billing.build_billing_payment_provider_factory",
        fake_build_billing_payment_provider_factory,
    )
    monkeypatch.setattr(
        "app.composition.billing.BillingBotNotificationService",
        FakeBillingBotNotificationService,
    )
    monkeypatch.setattr(
        "app.composition.billing.BillingNotificationRuntimeService",
        FakeBillingNotificationRuntimeService,
    )

    configure_billing_notification_runtime(service, db)

    assert service.billing_payment_provider_factory is provider_factory
    assert build_factory_calls == [{"settings": db.settings, "monobank_audit_logger": db.billing}]
    assert FakeBillingBotNotificationService.calls == [
        {
            "db": db,
            "time_service": time_service,
            "billing_receipt_storage_provider": ANY,
            "billing_receipt_fiscal_provider_factory": provider_factory,
        }
    ]
    assert FakeBillingNotificationRuntimeService.calls == [
        {
            "notification_service": service.billing_notification_service,
            "dispatch_lock": dispatch_lock,
        }
    ]


def test_configure_billing_webhook_runtime_wires_prewired_dependencies(monkeypatch) -> None:
    FakeBillingWebhookService.calls = []
    db = object()
    time_service = object()
    billing_provider_factory = object()
    signature_verifier = object()
    post_upgrade_rescan = object()
    notification_service = object()
    reconciliation_service = object()
    service = SimpleNamespace(
        time_service=time_service,
        billing_payment_provider_factory=billing_provider_factory,
        billing_notification_service=notification_service,
        billing_reconciliation_service=reconciliation_service,
    )
    monkeypatch.setattr(
        "app.composition.billing.verify_monobank_webhook_signature",
        signature_verifier,
    )
    monkeypatch.setattr(
        "app.composition.billing.BillingWebhookService",
        FakeBillingWebhookService,
    )

    configure_billing_webhook_runtime(
        service,
        db,
        post_upgrade_rescan=post_upgrade_rescan,
    )

    assert FakeBillingWebhookService.calls == [
        {
            "db": db,
            "time_service": time_service,
            "billing_provider_factory": billing_provider_factory,
            "billing_receipt_fiscal_provider_factory": billing_provider_factory,
            "billing_webhook_public_key_provider_factory": billing_provider_factory,
            "monobank_webhook_adapter": ANY,
            "monobank_signature_verifier": signature_verifier,
            "post_upgrade_rescan": post_upgrade_rescan,
        }
    ]
    assert isinstance(service.billing_webhook_service, FakeBillingWebhookService)
    assert service.billing_notification_service is notification_service
    assert service.billing_reconciliation_service is reconciliation_service


def test_configure_billing_webhook_runtime_allows_missing_provider_factory(
    monkeypatch,
) -> None:
    FakeBillingWebhookService.calls = []
    db = object()
    time_service = object()
    signature_verifier = object()
    post_upgrade_rescan = object()
    service = SimpleNamespace(
        time_service=time_service,
    )
    monkeypatch.setattr(
        "app.composition.billing.verify_monobank_webhook_signature",
        signature_verifier,
    )
    monkeypatch.setattr(
        "app.composition.billing.BillingWebhookService",
        FakeBillingWebhookService,
    )

    configure_billing_webhook_runtime(
        service,
        db,
        post_upgrade_rescan=post_upgrade_rescan,
    )

    assert not hasattr(service, "billing_payment_provider_factory")
    assert FakeBillingWebhookService.calls == [
        {
            "db": db,
            "time_service": time_service,
            "billing_provider_factory": None,
            "billing_receipt_fiscal_provider_factory": None,
            "billing_webhook_public_key_provider_factory": None,
            "monobank_webhook_adapter": ANY,
            "monobank_signature_verifier": signature_verifier,
            "post_upgrade_rescan": post_upgrade_rescan,
        }
    ]
    assert isinstance(service.billing_webhook_service, FakeBillingWebhookService)


def test_configure_billing_reconciliation_runtime_wires_provider_factory_and_alias(
    monkeypatch,
) -> None:
    FakeBillingReconciliationService.calls = []
    FakeBillingReconciliationRuntimeService.calls = []
    db = object()
    time_service = object()
    dispatch_lock = object()
    billing_provider_factory = object()
    post_upgrade_rescan = object()
    notification_service = object()
    service = SimpleNamespace(
        time_service=time_service,
        dispatch_lock=dispatch_lock,
        billing_payment_provider_factory=billing_provider_factory,
        billing_notification_service=notification_service,
    )
    monkeypatch.setattr(
        "app.composition.billing.BillingReconciliationService",
        FakeBillingReconciliationService,
    )
    monkeypatch.setattr(
        "app.composition.billing.BillingReconciliationRuntimeService",
        FakeBillingReconciliationRuntimeService,
    )

    configure_billing_reconciliation_runtime(
        service,
        db,
        post_upgrade_rescan=post_upgrade_rescan,
    )

    assert FakeBillingReconciliationService.calls == [
        {
            "db": db,
            "time_service": time_service,
            "billing_provider_factory": billing_provider_factory,
            "billing_receipt_fiscal_provider_factory": billing_provider_factory,
            "post_upgrade_rescan": post_upgrade_rescan,
        }
    ]
    assert FakeBillingReconciliationRuntimeService.calls == [
        {
            "reconciliation_service": service.billing_reconciliation_service,
            "notification_service": notification_service,
            "dispatch_lock": dispatch_lock,
        }
    ]


def test_configure_billing_reconciliation_runtime_allows_missing_provider_factory(
    monkeypatch,
) -> None:
    FakeBillingReconciliationService.calls = []
    FakeBillingReconciliationRuntimeService.calls = []
    db = object()
    time_service = object()
    dispatch_lock = object()
    post_upgrade_rescan = object()
    notification_service = object()
    service = SimpleNamespace(
        time_service=time_service,
        dispatch_lock=dispatch_lock,
        billing_notification_service=notification_service,
    )
    monkeypatch.setattr(
        "app.composition.billing.BillingReconciliationService",
        FakeBillingReconciliationService,
    )
    monkeypatch.setattr(
        "app.composition.billing.BillingReconciliationRuntimeService",
        FakeBillingReconciliationRuntimeService,
    )

    configure_billing_reconciliation_runtime(
        service,
        db,
        post_upgrade_rescan=post_upgrade_rescan,
    )

    assert not hasattr(service, "billing_payment_provider_factory")
    assert FakeBillingReconciliationService.calls == [
        {
            "db": db,
            "time_service": time_service,
            "billing_provider_factory": None,
            "billing_receipt_fiscal_provider_factory": None,
            "post_upgrade_rescan": post_upgrade_rescan,
        }
    ]
    assert FakeBillingReconciliationRuntimeService.calls == [
        {
            "reconciliation_service": service.billing_reconciliation_service,
            "notification_service": notification_service,
            "dispatch_lock": dispatch_lock,
        }
    ]
