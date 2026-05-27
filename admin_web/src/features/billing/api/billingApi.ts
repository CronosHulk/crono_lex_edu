import { adminApi } from "../../../api/adminApi";

export type BillingPaymentsParams = {
  page: number;
  pageSize: number;
  providerModes: string[];
  search: string;
  statuses: string[];
};

export type MonobankAuditParams = {
  directions: string[];
  page: number;
  pageSize: number;
  providerModes: string[];
  search: string;
};

export const billingQueryKeys = {
  all: ["billing"] as const,
  payments: () => [...billingQueryKeys.all, "payments"] as const,
  paymentList: (params: BillingPaymentsParams) => [...billingQueryKeys.payments(), "list", params] as const,
  paymentDetail: (paymentId: string | number | null | undefined) => [...billingQueryKeys.payments(), "detail", String(paymentId || "")] as const,
  monobankAudit: () => [...billingQueryKeys.all, "monobank-audit"] as const,
  monobankAuditList: (params: MonobankAuditParams) => [...billingQueryKeys.monobankAudit(), "list", params] as const,
  monobankAuditDetail: (auditLogId: string | number | null | undefined) => [...billingQueryKeys.monobankAudit(), "detail", String(auditLogId || "")] as const,
};

export function fetchBillingPayments(params: BillingPaymentsParams) {
  return adminApi(`/billing/payments?${billingPaymentsSearchParams(params).toString()}`);
}

export function fetchBillingPaymentDetail(paymentId: string | number) {
  return adminApi(`/billing/payments/${encodeURIComponent(String(paymentId))}`);
}

export function fetchMonobankAuditLogs(params: MonobankAuditParams) {
  return adminApi(`/billing/monobank-audit?${monobankAuditSearchParams(params).toString()}`);
}

export function fetchMonobankAuditDetail(auditLogId: string | number) {
  return adminApi(`/billing/monobank-audit/${encodeURIComponent(String(auditLogId))}`);
}

function billingPaymentsSearchParams(params: BillingPaymentsParams): URLSearchParams {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
    search: params.search,
  });
  params.providerModes.forEach((value) => query.append("provider_mode", value));
  params.statuses.forEach((value) => query.append("status", value));
  return query;
}

function monobankAuditSearchParams(params: MonobankAuditParams): URLSearchParams {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
    search: params.search,
  });
  params.directions.forEach((value) => query.append("direction", value));
  params.providerModes.forEach((value) => query.append("provider_mode", value));
  return query;
}

