from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.application.scheduled_runtime.billing_notification_service import (
    BillingNotificationRuntimeService,
)
from app.application.scheduled_runtime.billing_reconciliation_service import (
    BillingReconciliationRuntimeService,
)
from app.application.scheduled_runtime.subscription_maintenance_service import (
    SubscriptionMaintenanceRuntimeService,
)
from app.billing.providers.monobank.signature import verify_monobank_webhook_signature
from app.billing.providers.monobank.webhook_adapter import MonobankWebhookAdapter
from app.billing.providers.registry import build_billing_payment_provider_factory
from app.billing.services.notification_service import BillingBotNotificationService
from app.billing.services.reconciliation_service import BillingReconciliationService
from app.billing.services.webhook_service import BillingWebhookService
from app.composition.billing_receipt_storage import build_billing_receipt_storage_provider
from app.data_access.billing import BillingRepository
from app.subscriptions.entitlements import SubscriptionEntitlementService
from app.subscriptions.maintenance import SubscriptionMaintenanceService
from app.subscriptions.user_entitlements import UserEntitlementResolver

_MONOBANK_WEBHOOK_PUBLIC_KEY_CACHE: dict[str, str] = {}


def configure_subscription_runtime(service: Any, db: Any) -> None:
    service.subscription_entitlement_service = SubscriptionEntitlementService()
    service.user_entitlement_resolver = UserEntitlementResolver(
        db,
        service.subscription_entitlement_service,
    )
    service.subscription_maintenance_service = SubscriptionMaintenanceService(db)
    service.subscription_maintenance_runtime_service = SubscriptionMaintenanceRuntimeService(
        service.subscription_maintenance_service,
        service.time_service,
        dispatch_lock=service.dispatch_lock,
    )


def configure_billing_notification_runtime(service: Any, db: Any) -> None:
    billing_repo = getattr(db, "billing", None) or BillingRepository(db)
    service.billing_payment_provider_factory = build_billing_payment_provider_factory(
        settings=db.settings,
        monobank_audit_logger=billing_repo,
    )
    billing_receipt_storage_provider = build_billing_receipt_storage_provider(settings=db.settings)
    service.billing_notification_service = BillingBotNotificationService(
        db,
        service.time_service,
        billing_receipt_storage_provider=billing_receipt_storage_provider,
        billing_receipt_fiscal_provider_factory=service.billing_payment_provider_factory,
    )
    service.billing_notification_runtime_service = BillingNotificationRuntimeService(
        service.billing_notification_service,
        dispatch_lock=service.dispatch_lock,
    )


def configure_billing_webhook_runtime(
    service: Any,
    db: Any,
    *,
    post_upgrade_rescan: Callable[..., Any],
) -> None:
    billing_provider_factory = getattr(service, "billing_payment_provider_factory", None)
    service.billing_webhook_service = BillingWebhookService(
        db,
        service.time_service,
        billing_provider_factory=billing_provider_factory,
        billing_receipt_fiscal_provider_factory=billing_provider_factory,
        billing_webhook_public_key_provider_factory=billing_provider_factory,
        monobank_webhook_adapter=MonobankWebhookAdapter(
            billing_webhook_public_key_provider_factory=billing_provider_factory,
            monobank_signature_verifier=verify_monobank_webhook_signature,
            public_key_cache=_MONOBANK_WEBHOOK_PUBLIC_KEY_CACHE,
        ),
        monobank_signature_verifier=verify_monobank_webhook_signature,
        post_upgrade_rescan=post_upgrade_rescan,
    )


def configure_billing_reconciliation_runtime(
    service: Any,
    db: Any,
    *,
    post_upgrade_rescan: Callable[..., Any],
) -> None:
    service.billing_reconciliation_service = BillingReconciliationService(
        db,
        service.time_service,
        billing_provider_factory=getattr(service, "billing_payment_provider_factory", None),
        billing_receipt_fiscal_provider_factory=getattr(
            service, "billing_payment_provider_factory", None
        ),
        post_upgrade_rescan=post_upgrade_rescan,
    )
    service.billing_reconciliation_runtime_service = BillingReconciliationRuntimeService(
        service.billing_reconciliation_service,
        service.billing_notification_service,
        dispatch_lock=service.dispatch_lock,
    )
