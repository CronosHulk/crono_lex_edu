import { describe, expect, it } from "vitest";
import {
  activeFromPath,
  billingPathFromLegacySearch,
  dictionaryEntryIdFromPath,
  importJobIdFromPath,
  loginHistoryUserIdFromPath,
  pathForAdminRoute,
  readMagicRequest,
  taskLogIdFromPath,
  userDictionaryEntryIdFromPath,
  userIdFromPath,
} from "./routes";

describe("activeFromPath", () => {
  it("maps detail routes before list routes", () => {
    const userId = "11111111-1111-4111-8111-111111111111";
    expect(activeFromPath("/admin/dictionary/6/edit")).toBe("dictionary_edit");
    expect(activeFromPath("/admin/import-jobs/7")).toBe("import_job_detail");
    expect(activeFromPath(`/admin/users/${userId}/login-history`)).toBe("login_history");
    expect(activeFromPath(`/admin/users/${userId}`)).toBe("user_detail");
    expect(activeFromPath("/admin/task-logs/12")).toBe("task_log_detail");
    expect(activeFromPath("/admin/user-dictionary/entries/12")).toBe("user_dictionary_detail");
  });

  it("maps list routes", () => {
    expect(activeFromPath("/admin/dashboard")).toBe("dashboard");
    expect(activeFromPath("/admin/import-jobs")).toBe("import_jobs");
    expect(activeFromPath("/admin/import-items")).toBe("import_items");
    expect(activeFromPath("/admin/exercise-texts")).toBe("exercise_texts");
    expect(activeFromPath("/admin/user-dictionary")).toBe("user_dictionary");
    expect(activeFromPath("/admin/users")).toBe("users");
    expect(activeFromPath("/admin/task-logs")).toBe("task_logs");
    expect(activeFromPath("/admin/ai-usage")).toBe("ai_usage");
    expect(activeFromPath("/admin/billing")).toBe("billing_payments");
    expect(activeFromPath("/admin/billing/payments")).toBe("billing_payments");
    expect(activeFromPath("/admin/billing/monobank-audit")).toBe("billing_monobank_audit");
    expect(activeFromPath("/admin/billing/task-logs")).toBe("billing_task_logs");
    expect(activeFromPath("/admin/billing/settings")).toBe("billing_settings");
    expect(activeFromPath("/admin/error-log")).toBe("error_log");
    expect(activeFromPath("/admin/settings")).toBe("settings_profile");
    expect(activeFromPath("/admin/settings/analytics")).toBe("settings_analytics");
    expect(activeFromPath("/admin/settings/providers")).toBe("settings_providers");
    expect(activeFromPath("/admin/settings/import")).toBe("settings_import");
    expect(activeFromPath("/admin/settings/plans")).toBe("settings_plans");
    expect(activeFromPath("/admin/settings/password")).toBe("settings_password");
  });

  it("falls back to dictionary for unknown or empty paths", () => {
    expect(activeFromPath("/admin")).toBe("dictionary");
    expect(activeFromPath("/admin/video-pipeline/jobs")).toBe("dictionary");
    expect(activeFromPath("/admin/video-pipeline/jobs/12")).toBe("dictionary");
    expect(activeFromPath(null)).toBe("dictionary");
  });

  it("ignores query and hash contents when resolving the active route", () => {
    expect(activeFromPath("/admin/error-log?search=/video-pipeline/publishing-posts")).toBe("error_log");
    expect(activeFromPath("/admin/task-logs#/video-pipeline/publishing-posts")).toBe("task_logs");
  });
});

describe("path id helpers", () => {
  it("reads ids from matching routes", () => {
    const userId = "11111111-1111-4111-8111-111111111111";
    expect(importJobIdFromPath("/admin/import-jobs/10")).toBe(10);
    expect(dictionaryEntryIdFromPath("/admin/dictionary/9/edit")).toBe(9);
    expect(userIdFromPath(`/admin/users/${userId}`)).toBe(userId);
    expect(loginHistoryUserIdFromPath(`/admin/users/${userId}/login-history`)).toBe(userId);
    expect(taskLogIdFromPath("/admin/task-logs/12")).toBe(12);
    expect(userDictionaryEntryIdFromPath("/admin/user-dictionary/entries/12")).toBe(12);
  });

  it("returns null when routes do not contain matching ids", () => {
    expect(importJobIdFromPath("/admin/import-jobs/new")).toBeNull();
    expect(dictionaryEntryIdFromPath("/admin/dictionary/new/edit")).toBeNull();
    expect(userIdFromPath("/admin/task-logs/11")).toBeNull();
    expect(userIdFromPath(undefined)).toBeNull();
    expect(loginHistoryUserIdFromPath("/admin/users/11")).toBeNull();
    expect(taskLogIdFromPath(undefined)).toBeNull();
    expect(userDictionaryEntryIdFromPath("/admin/user-dictionary")).toBeNull();
  });
});

describe("pathForAdminRoute", () => {
  it("builds stable paths for list and placeholder routes", () => {
    expect(pathForAdminRoute("dashboard")).toBe("/admin/dashboard");
    expect(pathForAdminRoute("dictionary")).toBe("/admin");
    expect(pathForAdminRoute("dictionary_edit")).toBe("/admin");
    expect(pathForAdminRoute("exercise_texts")).toBe("/admin/exercise-texts");
    expect(pathForAdminRoute("import_jobs")).toBe("/admin/import-jobs");
    expect(pathForAdminRoute("import_items")).toBe("/admin/import-items");
    expect(pathForAdminRoute("user_dictionary")).toBe("/admin/user-dictionary");
    expect(pathForAdminRoute("user_dictionary_detail", { userDictionaryEntryId: 12 })).toBe("/admin/user-dictionary/entries/12");
    expect(pathForAdminRoute("user_dictionary_detail")).toBe("/admin/user-dictionary");
    expect(pathForAdminRoute("task_logs")).toBe("/admin/task-logs");
    expect(pathForAdminRoute("ai_usage")).toBe("/admin/ai-usage");
    expect(pathForAdminRoute("billing")).toBe("/admin/billing/payments");
    expect(pathForAdminRoute("billing_payments")).toBe("/admin/billing/payments");
    expect(pathForAdminRoute("billing_monobank_audit")).toBe("/admin/billing/monobank-audit");
    expect(pathForAdminRoute("billing_task_logs")).toBe("/admin/billing/task-logs");
    expect(pathForAdminRoute("billing_settings")).toBe("/admin/billing/settings");
    expect(pathForAdminRoute("error_log")).toBe("/admin/error-log");
    expect(pathForAdminRoute("settings")).toBe("/admin/settings");
    expect(pathForAdminRoute("settings_profile")).toBe("/admin/settings");
    expect(pathForAdminRoute("settings_analytics")).toBe("/admin/settings/analytics");
    expect(pathForAdminRoute("settings_providers")).toBe("/admin/settings/providers");
    expect(pathForAdminRoute("settings_import")).toBe("/admin/settings/import");
    expect(pathForAdminRoute("settings_plans")).toBe("/admin/settings/plans");
    expect(pathForAdminRoute("settings_password")).toBe("/admin/settings/password");
    expect(pathForAdminRoute("users")).toBe("/admin/users");
  });

  it("builds detail paths when ids are available and falls back to list paths", () => {
    expect(pathForAdminRoute("import_job_detail", { importJobId: 7 })).toBe("/admin/import-jobs/7");
    expect(pathForAdminRoute("dictionary_edit", { dictionaryEntryId: 6 })).toBe("/admin/dictionary/6/edit");
    expect(pathForAdminRoute("import_job_detail")).toBe("/admin/import-jobs");
    expect(pathForAdminRoute("login_history", { userId: "11111111-1111-4111-8111-111111111111" })).toBe(
      "/admin/users/11111111-1111-4111-8111-111111111111/login-history"
    );
    expect(pathForAdminRoute("login_history")).toBe("/admin/users");
    expect(pathForAdminRoute("task_log_detail", { taskLogId: 10 })).toBe("/admin/task-logs/10");
    expect(pathForAdminRoute("task_log_detail")).toBe("/admin/task-logs");
    expect(pathForAdminRoute("user_detail", { userId: "11111111-1111-4111-8111-111111111111" })).toBe(
      "/admin/users/11111111-1111-4111-8111-111111111111"
    );
  });
});

describe("billingPathFromLegacySearch", () => {
  it("maps legacy billing tabs to route-backed sidebar sections", () => {
    expect(billingPathFromLegacySearch(new URLSearchParams())).toBe("/admin/billing/payments");
    expect(billingPathFromLegacySearch(new URLSearchParams("tab=monobank_audit&provider_mode=test"))).toBe(
      "/admin/billing/monobank-audit?provider_mode=test"
    );
    expect(billingPathFromLegacySearch(new URLSearchParams("tab=task_logs&status=fatal"))).toBe(
      "/admin/billing/task-logs?status=fatal"
    );
    expect(billingPathFromLegacySearch(new URLSearchParams("tab=settings"))).toBe("/admin/billing/settings");
  });
});

describe("readMagicRequest", () => {
  it("reads token and next from URLSearchParams input", () => {
    expect(readMagicRequest(new URLSearchParams("token=abc&next=/admin/users"))).toEqual({
      token: "abc",
      next: "/admin/users"
    });
  });

  it("reads token and default next from URL input", () => {
    expect(readMagicRequest(new URL("https://example.test/admin/magic?token=abc"))).toEqual({
      token: "abc",
      next: "/admin/user-dictionary"
    });
  });

  it("reads query strings and paths with query strings", () => {
    expect(readMagicRequest("?token=query")).toEqual({
      token: "query",
      next: "/admin/user-dictionary"
    });
    expect(readMagicRequest("token=bare")).toEqual({
      token: "bare",
      next: "/admin/user-dictionary"
    });
    expect(readMagicRequest("/admin/magic?token=path&next=/admin/task-logs")).toEqual({
      token: "path",
      next: "/admin/task-logs"
    });
  });

  it("reads object search or href values", () => {
    expect(readMagicRequest({ search: "?token=search" })).toEqual({
      token: "search",
      next: "/admin/user-dictionary"
    });
    expect(readMagicRequest({ href: "/admin/magic?token=href" })).toEqual({
      token: "href",
      next: "/admin/user-dictionary"
    });
  });

  it("returns null when the token is missing", () => {
    expect(readMagicRequest("next=/admin/users")).toBeNull();
    expect(readMagicRequest({})).toBeNull();
    expect(readMagicRequest()).toBeNull();
  });
});
