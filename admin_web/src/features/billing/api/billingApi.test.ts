import { beforeEach, describe, expect, it, vi } from "vitest";

import { adminApi } from "../../../api/adminApi";
import {
  billingQueryKeys,
  fetchBillingPaymentDetail,
  fetchBillingPayments,
  fetchMonobankAuditDetail,
  fetchMonobankAuditLogs,
} from "./billingApi";

vi.mock("../../../api/adminApi", () => ({
  adminApi: vi.fn(),
}));

const mockedAdminApi = vi.mocked(adminApi);

describe("billingApi", () => {
  beforeEach(() => {
    mockedAdminApi.mockClear();
  });

  it("builds payment list and detail requests", () => {
    fetchBillingPayments({
      page: 2,
      pageSize: 100,
      providerModes: ["test"],
      search: "order",
      statuses: ["success", "failure"],
    });
    fetchBillingPaymentDetail(42);

    expect(mockedAdminApi).toHaveBeenNthCalledWith(
      1,
      "/billing/payments?page=2&page_size=100&search=order&provider_mode=test&status=success&status=failure",
    );
    expect(mockedAdminApi).toHaveBeenNthCalledWith(2, "/billing/payments/42");
  });

  it("builds monobank audit list and detail requests", () => {
    fetchMonobankAuditLogs({
      directions: ["incoming"],
      page: 3,
      pageSize: 50,
      providerModes: ["unknown"],
      search: "webhook",
    });
    fetchMonobankAuditDetail(7);

    expect(mockedAdminApi).toHaveBeenNthCalledWith(
      1,
      "/billing/monobank-audit?page=3&page_size=50&search=webhook&direction=incoming&provider_mode=unknown",
    );
    expect(mockedAdminApi).toHaveBeenNthCalledWith(2, "/billing/monobank-audit/7");
  });

  it("creates stable query keys", () => {
    const paymentParams = { page: 1, pageSize: 50, providerModes: ["test"], search: "", statuses: ["success"] };
    const auditParams = { directions: ["incoming"], page: 1, pageSize: 50, providerModes: ["unknown"], search: "" };

    expect(billingQueryKeys.paymentList(paymentParams)).toEqual(["billing", "payments", "list", paymentParams]);
    expect(billingQueryKeys.paymentDetail(42)).toEqual(["billing", "payments", "detail", "42"]);
    expect(billingQueryKeys.paymentDetail(null)).toEqual(["billing", "payments", "detail", ""]);
    expect(billingQueryKeys.monobankAuditList(auditParams)).toEqual(["billing", "monobank-audit", "list", auditParams]);
    expect(billingQueryKeys.monobankAuditDetail(7)).toEqual(["billing", "monobank-audit", "detail", "7"]);
    expect(billingQueryKeys.monobankAuditDetail(null)).toEqual(["billing", "monobank-audit", "detail", ""]);
  });
});

