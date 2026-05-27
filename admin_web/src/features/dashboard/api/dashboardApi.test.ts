import { beforeEach, describe, expect, it, vi } from "vitest";

import { adminApi } from "../../../api/adminApi";
import { assignTeacherStudent, dashboardQueryKeys, fetchDashboardSummary } from "./dashboardApi";

vi.mock("../../../api/adminApi", () => ({
  adminApi: vi.fn(),
}));

const mockedAdminApi = vi.mocked(adminApi);

describe("dashboardApi", () => {
  beforeEach(() => {
    mockedAdminApi.mockClear();
  });

  it("fetches dashboard summary", () => {
    fetchDashboardSummary();

    expect(mockedAdminApi).toHaveBeenCalledWith("/dashboard/summary");
  });

  it("assigns a student to a teacher by uuid", () => {
    assignTeacherStudent({
      teacherUserId: "11111111-1111-4111-8111-111111111111",
      studentUserId: "22222222-2222-4222-8222-222222222222",
    });

    expect(mockedAdminApi).toHaveBeenCalledWith("/dashboard/teacher-assignments", {
      method: "POST",
      body: JSON.stringify({
        teacher_user_id: "11111111-1111-4111-8111-111111111111",
        student_user_id: "22222222-2222-4222-8222-222222222222",
      }),
    });
  });

  it("creates stable query keys", () => {
    expect(dashboardQueryKeys.all).toEqual(["dashboard"]);
    expect(dashboardQueryKeys.summary()).toEqual(["dashboard", "summary"]);
  });
});
