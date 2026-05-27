import { beforeEach, describe, expect, it, vi } from "vitest";

import { adminApi } from "../../../api/adminApi";
import { aiUsageQueryKeys, deleteAIUsageSessions, fetchAIUsageSessions, fetchAIUsageSummary } from "./aiUsageApi";

vi.mock("../../../api/adminApi", () => ({
  adminApi: vi.fn(),
}));

const mockedAdminApi = vi.mocked(adminApi);

describe("aiUsageApi", () => {
  beforeEach(() => {
    mockedAdminApi.mockClear();
  });

  it("builds usage summary and session requests", () => {
    fetchAIUsageSummary("week");
    fetchAIUsageSessions({ page: 2, pageSize: 50, period: "month", search: "import validation" });

    expect(mockedAdminApi).toHaveBeenNthCalledWith(1, "/ai-usage/summary?period=week");
    expect(mockedAdminApi).toHaveBeenNthCalledWith(
      2,
      "/ai-usage/sessions?page=2&page_size=50&period=month&search=import+validation",
    );
  });

  it("deletes usage sessions after OTP confirmation", () => {
    const payload = { challenge_id: 10, otp: "123456" };

    deleteAIUsageSessions(payload);

    expect(mockedAdminApi).toHaveBeenCalledWith("/ai-usage/sessions", {
      method: "DELETE",
      body: JSON.stringify(payload),
    });
  });

  it("creates stable query keys", () => {
    const params = { page: 1, pageSize: 50, period: "week", search: "" };

    expect(aiUsageQueryKeys.all).toEqual(["ai-usage"]);
    expect(aiUsageQueryKeys.summary("week")).toEqual(["ai-usage", "summary", "week"]);
    expect(aiUsageQueryKeys.sessions(params)).toEqual(["ai-usage", "sessions", params]);
  });
});
