export type BillingTab = "settings" | "payments" | "monobank_audit" | "task_logs";

export type BillingPaymentsSearchParams = {
  page: number;
  pageSize: number;
  providerModes: string[];
  search: string;
  statuses: string[];
};

export type MonobankAuditSearchParams = {
  directions: string[];
  page: number;
  pageSize: number;
  providerModes: string[];
  search: string;
};

export type BillingTaskLogsSearchParams = {
  page: number;
  pageSize: number;
  search: string;
  statuses: string[];
  taskTypes: string[];
};

export function billingTabFromSearch(searchParams: URLSearchParams): BillingTab {
  if (searchParams.get("tab") === "settings") return "settings";
  if (searchParams.get("tab") === "task_logs") return "task_logs";
  return searchParams.get("tab") === "monobank_audit" ? "monobank_audit" : "payments";
}

export function billingPaymentsParamsFromSearch(searchParams: URLSearchParams): BillingPaymentsSearchParams {
  return {
    page: positiveIntParam(searchParams.get("page"), 1),
    pageSize: positiveIntParam(searchParams.get("page_size"), 50),
    providerModes: searchParams.getAll("provider_mode"),
    search: searchParams.get("search") || "",
    statuses: searchParams.getAll("status"),
  };
}

export function monobankAuditParamsFromSearch(searchParams: URLSearchParams): MonobankAuditSearchParams {
  return {
    directions: searchParams.getAll("direction"),
    page: positiveIntParam(searchParams.get("page"), 1),
    pageSize: positiveIntParam(searchParams.get("page_size"), 50),
    providerModes: searchParams.getAll("provider_mode"),
    search: searchParams.get("search") || "",
  };
}

export function billingTaskLogsParamsFromSearch(searchParams: URLSearchParams): BillingTaskLogsSearchParams {
  return {
    page: positiveIntParam(searchParams.get("page"), 1),
    pageSize: positiveIntParam(searchParams.get("page_size"), 50),
    search: searchParams.get("search") || "",
    statuses: searchParams.getAll("status"),
    taskTypes: searchParams.getAll("task_type"),
  };
}

export function applyBillingPaymentsParamUpdates(searchParams: URLSearchParams, updates: Partial<BillingPaymentsSearchParams>): URLSearchParams {
  const next = withoutLegacyTab(searchParams);
  if ("page" in updates) setSearchParam(next, "page", updates.page, 1);
  if ("pageSize" in updates) setSearchParam(next, "page_size", updates.pageSize, 50);
  if ("search" in updates) setSearchParam(next, "search", updates.search, "");
  if ("providerModes" in updates) setRepeatedSearchParam(next, "provider_mode", updates.providerModes);
  if ("statuses" in updates) setRepeatedSearchParam(next, "status", updates.statuses);
  return next;
}

export function applyMonobankAuditParamUpdates(searchParams: URLSearchParams, updates: Partial<MonobankAuditSearchParams>): URLSearchParams {
  const next = withoutLegacyTab(searchParams);
  if ("page" in updates) setSearchParam(next, "page", updates.page, 1);
  if ("pageSize" in updates) setSearchParam(next, "page_size", updates.pageSize, 50);
  if ("search" in updates) setSearchParam(next, "search", updates.search, "");
  if ("directions" in updates) setRepeatedSearchParam(next, "direction", updates.directions);
  if ("providerModes" in updates) setRepeatedSearchParam(next, "provider_mode", updates.providerModes);
  return next;
}

export function applyBillingTaskLogsParamUpdates(searchParams: URLSearchParams, updates: Partial<BillingTaskLogsSearchParams>): URLSearchParams {
  const next = withoutLegacyTab(searchParams);
  if ("page" in updates) setSearchParam(next, "page", updates.page, 1);
  if ("pageSize" in updates) setSearchParam(next, "page_size", updates.pageSize, 50);
  if ("search" in updates) setSearchParam(next, "search", updates.search, "");
  if ("statuses" in updates) setRepeatedSearchParam(next, "status", updates.statuses);
  if ("taskTypes" in updates) setRepeatedSearchParam(next, "task_type", updates.taskTypes);
  return next;
}

function withoutLegacyTab(searchParams: URLSearchParams): URLSearchParams {
  const next = new URLSearchParams(searchParams);
  next.delete("tab");
  return next;
}

function positiveIntParam(value: string | null, fallback: number): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function setSearchParam(params: URLSearchParams, key: string, value: unknown, defaultValue: unknown) {
  if (value === defaultValue || value === "" || value === null || value === undefined) {
    params.delete(key);
    return;
  }
  params.set(key, String(value));
}

function setRepeatedSearchParam(params: URLSearchParams, key: string, values: string[] | undefined) {
  params.delete(key);
  values?.forEach((value) => params.append(key, value));
}
