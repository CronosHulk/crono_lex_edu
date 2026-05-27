export type AdminRoute =
  | "ai_usage"
  | "billing"
  | "billing_monobank_audit"
  | "billing_payments"
  | "billing_settings"
  | "billing_task_logs"
  | "dashboard"
  | "dictionary"
  | "dictionary_edit"
  | "error_log"
  | "exercise_texts"
  | "import_items"
  | "import_job_detail"
  | "import_jobs"
  | "login_history"
  | "settings"
  | "settings_analytics"
  | "settings_import"
  | "settings_password"
  | "settings_plans"
  | "settings_profile"
  | "settings_providers"
  | "task_log_detail"
  | "task_logs"
  | "user_dictionary"
  | "user_dictionary_detail"
  | "user_detail"
  | "users";

export type AdminRoutePathContext = {
  dictionaryEntryId?: number | null;
  importJobId?: number | null;
  taskLogId?: number | null;
  userDictionaryEntryId?: number | null;
  userId?: string | number | null;
};

export type MagicRequest = {
  token: string;
  next: string;
};

const DEFAULT_MAGIC_NEXT = "/admin/user-dictionary";

export function activeFromPath(value: unknown): AdminRoute {
  const path = pathnameOnly(value);
  if (path.match(/\/dictionary\/\d+\/edit/)) return "dictionary_edit";
  if (path.includes("/exercise-texts")) return "exercise_texts";
  if (path.includes("/import-jobs/")) return "import_job_detail";
  if (path.match(/\/users\/[^/]+\/login-history/)) return "login_history";
  if (path.match(/\/user-dictionary\/entries\/\d+/)) return "user_dictionary_detail";
  if (path.includes("/user-dictionary")) return "user_dictionary";
  if (path.includes("/import-jobs")) return "import_jobs";
  if (path.includes("/import-items")) return "import_items";
  if (path.match(/\/users\/[^/]+/)) return "user_detail";
  if (path.match(/\/task-logs\/\d+/)) return "task_log_detail";
  if (path.includes("/ai-usage")) return "ai_usage";
  if (path.includes("/billing/monobank-audit")) return "billing_monobank_audit";
  if (path.includes("/billing/task-logs")) return "billing_task_logs";
  if (path.includes("/billing/settings")) return "billing_settings";
  if (path.includes("/billing/payments")) return "billing_payments";
  if (path.includes("/billing")) return "billing_payments";
  if (path.includes("/dashboard")) return "dashboard";
  if (path.includes("/users")) return "users";
  if (path.includes("/task-logs")) return "task_logs";
  if (path.includes("/error-log")) return "error_log";
  if (path.includes("/settings/providers")) return "settings_providers";
  if (path.includes("/settings/analytics")) return "settings_analytics";
  if (path.includes("/settings/import")) return "settings_import";
  if (path.includes("/settings/plans")) return "settings_plans";
  if (path.includes("/settings/password")) return "settings_password";
  if (path.includes("/settings")) return "settings_profile";
  return "dictionary";
}

function pathnameOnly(value: unknown): string {
  return String(value || "").split(/[?#]/, 1)[0];
}

export function pathForAdminRoute(route: AdminRoute, context: AdminRoutePathContext = {}): string {
  if (route === "dashboard") return "/admin/dashboard";
  if (route === "ai_usage") return "/admin/ai-usage";
  if (route === "billing" || route === "billing_payments") return "/admin/billing/payments";
  if (route === "billing_monobank_audit") return "/admin/billing/monobank-audit";
  if (route === "billing_task_logs") return "/admin/billing/task-logs";
  if (route === "billing_settings") return "/admin/billing/settings";
  if (route === "dictionary_edit" && context.dictionaryEntryId) return `/admin/dictionary/${context.dictionaryEntryId}/edit`;
  if (route === "dictionary_edit") return "/admin";
  if (route === "dictionary") return "/admin";
  if (route === "error_log") return "/admin/error-log";
  if (route === "exercise_texts") return "/admin/exercise-texts";
  if (route === "import_items") return "/admin/import-items";
  if (route === "import_job_detail" && context.importJobId) return `/admin/import-jobs/${context.importJobId}`;
  if (route === "import_jobs" || route === "import_job_detail") return "/admin/import-jobs";
  if (route === "login_history" && context.userId) return `/admin/users/${context.userId}/login-history`;
  if (route === "login_history") return "/admin/users";
  if (route === "settings" || route === "settings_profile") return "/admin/settings";
  if (route === "settings_analytics") return "/admin/settings/analytics";
  if (route === "settings_providers") return "/admin/settings/providers";
  if (route === "settings_import") return "/admin/settings/import";
  if (route === "settings_plans") return "/admin/settings/plans";
  if (route === "settings_password") return "/admin/settings/password";
  if (route === "task_log_detail" && context.taskLogId) return `/admin/task-logs/${context.taskLogId}`;
  if (route === "task_logs" || route === "task_log_detail") return "/admin/task-logs";
  if (route === "user_dictionary_detail" && context.userDictionaryEntryId) return `/admin/user-dictionary/entries/${context.userDictionaryEntryId}`;
  if (route === "user_dictionary_detail") return "/admin/user-dictionary";
  if (route === "user_dictionary") return "/admin/user-dictionary";
  if (route === "user_detail" && context.userId) return `/admin/users/${context.userId}`;
  return "/admin/users";
}

export function billingPathFromLegacySearch(searchParams: URLSearchParams): string {
  const nextSearch = new URLSearchParams(searchParams);
  const tab = nextSearch.get("tab");
  nextSearch.delete("tab");
  let route: AdminRoute = "billing_payments";
  if (tab === "monobank_audit") route = "billing_monobank_audit";
  if (tab === "task_logs") route = "billing_task_logs";
  if (tab === "settings") route = "billing_settings";
  const query = nextSearch.toString();
  return `${pathForAdminRoute(route)}${query ? `?${query}` : ""}`;
}

export function importJobIdFromPath(value: unknown): number | null {
  return numericPathId(value, /\/import-jobs\/(\d+)/);
}

export function dictionaryEntryIdFromPath(value: unknown): number | null {
  return numericPathId(value, /\/dictionary\/(\d+)\/edit/);
}

export function userIdFromPath(value: unknown): string | null {
  return stringPathId(value, /\/users\/([^/]+)/);
}

export function loginHistoryUserIdFromPath(value: unknown): string | null {
  return stringPathId(value, /\/users\/([^/]+)\/login-history/);
}

export function taskLogIdFromPath(value: unknown): number | null {
  return numericPathId(value, /\/task-logs\/(\d+)/);
}

export function userDictionaryEntryIdFromPath(value: unknown): number | null {
  return numericPathId(value, /\/user-dictionary\/entries\/(\d+)/);
}

export function readMagicRequest(input: URL | URLSearchParams | string | { search?: string; href?: string } = ""): MagicRequest | null {
  const params = searchParamsFromInput(input);
  const token = params.get("token");
  if (!token) return null;

  return {
    token,
    next: params.get("next") || DEFAULT_MAGIC_NEXT
  };
}

function numericPathId(value: unknown, pattern: RegExp): number | null {
  const match = String(value || "").match(pattern);
  return match ? Number(match[1]) : null;
}

function stringPathId(value: unknown, pattern: RegExp): string | null {
  const match = String(value || "").match(pattern);
  return match ? decodeURIComponent(match[1]) : null;
}

function searchParamsFromInput(input: URL | URLSearchParams | string | { search?: string; href?: string }): URLSearchParams {
  if (input instanceof URLSearchParams) return input;
  if (input instanceof URL) return input.searchParams;

  const source = typeof input === "string" ? input : input.search || input.href || "";
  if (source.startsWith("?")) return new URLSearchParams(source);

  const queryStart = source.indexOf("?");
  if (queryStart >= 0) return new URLSearchParams(source.slice(queryStart));

  return new URLSearchParams(source);
}
