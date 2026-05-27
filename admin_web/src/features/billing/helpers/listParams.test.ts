import { describe, expect, it } from "vitest";

import {
  applyBillingPaymentsParamUpdates,
  applyBillingTaskLogsParamUpdates,
  applyMonobankAuditParamUpdates,
  billingPaymentsParamsFromSearch,
  billingTabFromSearch,
  billingTaskLogsParamsFromSearch,
  monobankAuditParamsFromSearch,
} from "./listParams";

describe("billing list params", () => {
  it("reads payments params from search", () => {
    expect(billingPaymentsParamsFromSearch(new URLSearchParams("page=2&page_size=100&search=ref&status=success&provider_mode=test"))).toEqual({
      page: 2,
      pageSize: 100,
      providerModes: ["test"],
      search: "ref",
      statuses: ["success"],
    });
  });

  it("uses payment tab and pagination defaults for empty search", () => {
    expect(billingTabFromSearch(new URLSearchParams())).toBe("payments");
    expect(billingPaymentsParamsFromSearch(new URLSearchParams("page=bad&page_size=0"))).toEqual({
      page: 1,
      pageSize: 50,
      providerModes: [],
      search: "",
      statuses: [],
    });
  });

  it("reads audit tab and audit params from search", () => {
    const params = new URLSearchParams("tab=monobank_audit&direction=incoming&provider_mode=unknown");
    expect(billingTabFromSearch(params)).toBe("monobank_audit");
    expect(billingTabFromSearch(new URLSearchParams("tab=settings"))).toBe("settings");
    expect(billingTabFromSearch(new URLSearchParams("tab=task_logs"))).toBe("task_logs");
    expect(monobankAuditParamsFromSearch(params)).toEqual({
      directions: ["incoming"],
      page: 1,
      pageSize: 50,
      providerModes: ["unknown"],
      search: "",
    });
  });

  it("reads billing task log params from search", () => {
    const params = new URLSearchParams("tab=task_logs&page=2&page_size=100&search=mono&status=error&task_type=billing_monobank_reconciliation");

    expect(billingTaskLogsParamsFromSearch(params)).toEqual({
      page: 2,
      pageSize: 100,
      search: "mono",
      statuses: ["error"],
      taskTypes: ["billing_monobank_reconciliation"],
    });
    expect(billingTaskLogsParamsFromSearch(new URLSearchParams("tab=task_logs&page=bad&page_size=0"))).toEqual({
      page: 1,
      pageSize: 50,
      search: "",
      statuses: [],
      taskTypes: [],
    });
  });

  it("updates repeated payment and audit params", () => {
    const paymentParams = applyBillingPaymentsParamUpdates(new URLSearchParams("tab=monobank_audit"), {
      statuses: ["success", "failure"],
      providerModes: ["test"],
    });
    expect(paymentParams.getAll("status")).toEqual(["success", "failure"]);
    expect(paymentParams.getAll("provider_mode")).toEqual(["test"]);
    expect(paymentParams.get("tab")).toBeNull();
    expect(
      applyMonobankAuditParamUpdates(new URLSearchParams(), {
        directions: ["incoming"],
        providerModes: ["unknown"],
      }).toString(),
    ).toBe("direction=incoming&provider_mode=unknown");
    expect(
      applyBillingTaskLogsParamUpdates(new URLSearchParams(), {
        page: 2,
        pageSize: 100,
        search: "retry",
        statuses: ["fatal"],
        taskTypes: ["subscription_daily_maintenance"],
      }).toString(),
    ).toBe("page=2&page_size=100&search=retry&status=fatal&task_type=subscription_daily_maintenance");
  });

  it("sets and clears scalar params", () => {
    expect(
      applyBillingPaymentsParamUpdates(new URLSearchParams("page=2&page_size=100&search=old"), {
        page: 1,
        pageSize: 50,
        search: "",
      }).toString(),
    ).toBe("");
    expect(
      applyMonobankAuditParamUpdates(new URLSearchParams("tab=monobank_audit"), {
        page: 2,
        pageSize: 100,
        search: "hook",
      }).toString(),
    ).toBe("page=2&page_size=100&search=hook");
    expect(
      applyBillingTaskLogsParamUpdates(new URLSearchParams("tab=task_logs&page=2&page_size=100&search=retry&status=fatal&task_type=billing"), {
        page: 1,
        pageSize: 50,
        search: "",
        statuses: undefined,
        taskTypes: [],
      }).toString(),
    ).toBe("");
    expect(
      applyBillingTaskLogsParamUpdates(new URLSearchParams("tab=task_logs&page=2&page_size=100&search=retry&status=fatal&task_type=billing"), {}).toString(),
    ).toBe("page=2&page_size=100&search=retry&status=fatal&task_type=billing");
  });
});
