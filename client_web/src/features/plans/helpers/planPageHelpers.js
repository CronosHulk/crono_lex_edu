import { formatDisplayDate, formatDisplayDateTime } from "@cronolex/shared";

const PAYMENT_TERMINAL_MAINTENANCE_TIMEZONE = "Europe/Kyiv";
const PAYMENT_TERMINAL_MAINTENANCE_START_MINUTES = 23 * 60 + 30;
const PAYMENT_TERMINAL_MAINTENANCE_END_MINUTES = 30;
const BILLING_PROVIDER_MONOBANK = "monobank";

export function normalizePlanReturnTo(value) {
  const target = String(value || "").trim();
  if (!target.startsWith("/") || target.startsWith("//")) return "";
  return target;
}

export function deliverableTaxUrlReceipts(payment) {
  const seen = new Set();
  return (payment.receipts || []).filter((receipt) => {
    const taxUrl = String(receipt.tax_url || "").trim();
    if (!taxUrl || isTaxCabinetReceiptUrl(taxUrl) || seen.has(taxUrl)) return false;
    seen.add(taxUrl);
    return true;
  });
}

export function hasStoredReceiptFile(payment) {
  return (payment.receipts || []).some((receipt) => receipt.status === "done" && receipt.has_file);
}

export function hasPendingReceipt(payment) {
  if (payment.status !== "success") return false;
  if (deliverableTaxUrlReceipts(payment).length || hasStoredReceiptFile(payment)) return false;
  const receipts = payment.receipts || [];
  if (!receipts.length) return true;
  return receipts.some((receipt) => (
    receipt.receipt_type === "fiscal_check"
    && receipt.status !== "failed"
    && receipt.status !== "unavailable"
  ));
}

export function hasActivePaidSubscription(subscription) {
  return (
    subscription?.plan_key
    && subscription.plan_key !== "free"
    && Number(subscription.remaining_seconds || 0) > 0
  );
}

export function buildOrderPreview(billing, plan, period) {
  const planKey = typeof plan === "string" ? plan : plan?.key;
  const preview = typeof plan === "object" ? plan?.order_previews?.[String(period)] : null;
  if (preview?.amount_minor != null) {
    return {
      amountUah: Number(preview.amount_minor) / 100,
      periodMonths: Number(period),
      grantedPeriodMonths: Number(preview.granted_period_months || period),
      quoteKind: preview.kind,
    };
  }
  const amountUah = billing?.plan_prices_uah?.[planKey]?.[String(period)];
  if (amountUah == null) return null;
  return { amountUah: Number(amountUah), periodMonths: Number(period) };
}

export function bestPlanPeriod(billing, plan, periodOptions) {
  if (!plan || plan.key === "free") return periodOptions[0] || 1;
  let bestPeriod = periodOptions[0] || 1;
  let bestMonthlyAmount = Number.POSITIVE_INFINITY;
  for (const period of periodOptions) {
    const order = buildOrderPreview(billing, plan, period);
    if (!order || order.quoteKind === "upgrade") continue;
    const monthlyAmount = order.amountUah / Math.max(order.periodMonths, 1);
    if (monthlyAmount <= bestMonthlyAmount) {
      bestMonthlyAmount = monthlyAmount;
      bestPeriod = period;
    }
  }
  return bestPeriod;
}

export function formatAmount(amountUah) {
  const value = Number(amountUah);
  const formatted = Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/\.?0+$/, "");
  return `${formatted} грн`;
}

export function formatPeriod(period) {
  return `${period} міс.`;
}

export function formatOrderSummary(order) {
  const base = `${formatAmount(order.amountUah)} · ${formatPeriod(order.periodMonths)}`;
  if (Number(order.grantedPeriodMonths || order.periodMonths) > Number(order.periodMonths)) {
    return `${base} · нараховано ${formatPeriod(order.grantedPeriodMonths)}`;
  }
  return base;
}

export function formatCheckoutError(error, t) {
  return t("paymentServiceUnavailable", { detail: normalizeProviderNeutralError(error?.message || "") });
}

const PROVIDER_ERROR_DETAILS = {
  "Monobank checkout is disabled": "Payment provider checkout is disabled",
  "Monobank checkout is temporarily unavailable": "Payment checkout is temporarily unavailable",
};

function normalizeProviderNeutralError(detail) {
  const text = String(detail || "");
  return PROVIDER_ERROR_DETAILS[text] || PROVIDER_ERROR_DETAILS[text.trim()] || text;
}

export function formatPaymentTitle(payment) {
  const base = `${payment.plan_key} · ${formatAmount(payment.amount_uah)} · ${formatPeriod(payment.period_months)}`;
  if (Number(payment.granted_period_months || payment.period_months) > Number(payment.period_months)) {
    return `${base} · нараховано ${formatPeriod(payment.granted_period_months)}`;
  }
  return base;
}

export function formatPaymentDate(value, intlLocale) {
  return formatDisplayDateTime(value, intlLocale);
}

export function formatSubscriptionDate(value, intlLocale) {
  return formatDisplayDate(value, intlLocale);
}

export function isPaymentTerminalMaintenanceTime(value, billingProvider = "") {
  if (billingProvider !== BILLING_PROVIDER_MONOBANK) {
    return false;
  }
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: PAYMENT_TERMINAL_MAINTENANCE_TIMEZONE,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(value);
  const hour = Number(parts.find((part) => part.type === "hour")?.value || 0);
  const minute = Number(parts.find((part) => part.type === "minute")?.value || 0);
  const totalMinutes = hour * 60 + minute;
  return totalMinutes >= PAYMENT_TERMINAL_MAINTENANCE_START_MINUTES || totalMinutes < PAYMENT_TERMINAL_MAINTENANCE_END_MINUTES;
}

export function formatPaymentStatus(status, t) {
  return ({
    success: t("paymentStatusSuccess"),
    failure: t("paymentStatusFailure"),
    reversed: t("paymentStatusReversed"),
    expired: t("paymentStatusExpired"),
    processing: t("paymentStatusProcessing"),
    invoice_created: t("paymentStatusInvoiceCreated"),
    created: t("paymentStatusCreated"),
  })[status] || status;
}

function isTaxCabinetReceiptUrl(value) {
  try {
    return new URL(value).hostname === "cabinet.tax.gov.ua";
  } catch {
    return false;
  }
}
