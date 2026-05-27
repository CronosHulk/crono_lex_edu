import { beforeEach, describe, expect, it, vi } from "vitest";

import { adminApi } from "../../../api/adminApi";
import { requestAdminActionOtp } from "./actionOtpApi";

vi.mock("../../../api/adminApi", () => ({
  adminApi: vi.fn(),
}));

const mockedAdminApi = vi.mocked(adminApi);

describe("actionOtpApi", () => {
  beforeEach(() => {
    mockedAdminApi.mockClear();
  });

  it("requests OTP for a destructive admin action", () => {
    requestAdminActionOtp({ action_key: "delete_import_data" });

    expect(mockedAdminApi).toHaveBeenCalledWith("/auth/action-otp", {
      method: "POST",
      body: JSON.stringify({ action_key: "delete_import_data" }),
    });
  });
});

