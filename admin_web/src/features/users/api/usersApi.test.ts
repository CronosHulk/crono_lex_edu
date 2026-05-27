import { beforeEach, describe, expect, it, vi } from "vitest";

import { adminApi } from "../../../api/adminApi";
import {
  archiveUserById,
  deleteUserById,
  fetchFullLoginHistory,
  fetchLatestLoginHistory,
  fetchUserDetail,
  fetchUserFilterMetadata,
  fetchUsers,
  resetUserPasswordById,
  unassignTeacherStudent,
  updateUserLearningRole,
  updateUserRole,
  updateUserSubscription,
  updateUserSubscriptionTrial,
  usersQueryKeys,
} from "./usersApi";

vi.mock("../../../api/adminApi", () => ({
  adminApi: vi.fn(),
}));

const mockedAdminApi = vi.mocked(adminApi);

describe("usersApi", () => {
  beforeEach(() => {
    mockedAdminApi.mockClear();
  });

  it("builds users list requests with pagination and repeated role filters", () => {
    fetchUsers({ archived: false, page: 2, pageSize: 100, roles: ["admin", "admin_editor"], search: "ada", userId: "111", userType: "admin" });

    expect(mockedAdminApi).toHaveBeenCalledWith("/users?page=2&page_size=100&archived=false&search=ada&user_id=111&user_type=admin&role=admin&role=admin_editor");
  });

  it("omits the user id filter when it is empty", () => {
    fetchUsers({ archived: true, page: 1, pageSize: 50, roles: [], search: "", userId: "", userType: "student" });

    expect(mockedAdminApi).toHaveBeenCalledWith("/users?page=1&page_size=50&archived=true&search=&user_type=student");
  });

  it("calls user metadata, detail, and login history endpoints", () => {
    fetchUserFilterMetadata();
    fetchUserDetail(42);
    fetchLatestLoginHistory(42);
    fetchFullLoginHistory(42);

    expect(mockedAdminApi).toHaveBeenNthCalledWith(1, "/users/filter-metadata");
    expect(mockedAdminApi).toHaveBeenNthCalledWith(2, "/users/42");
    expect(mockedAdminApi).toHaveBeenNthCalledWith(3, "/users/42/login-history?limit=10");
    expect(mockedAdminApi).toHaveBeenNthCalledWith(4, "/login-history?user_id=42");
  });

  it("calls user mutation endpoints", () => {
    updateUserRole({ targetId: 42, role: "admin_editor" });
    updateUserLearningRole({ targetId: 42, learningRole: "teacher" });
    updateUserSubscription({ targetId: 42, planKey: "premium" });
    updateUserSubscriptionTrial({ targetId: 42, isTrialEnabled: true });
    unassignTeacherStudent(42);
    archiveUserById(42);
    deleteUserById(42);
    resetUserPasswordById(42);

    expect(mockedAdminApi).toHaveBeenNthCalledWith(1, "/users/42/roles", {
      method: "POST",
      body: JSON.stringify({ role: "admin_editor" }),
    });
    expect(mockedAdminApi).toHaveBeenNthCalledWith(2, "/users/42/learning-role", {
      method: "POST",
      body: JSON.stringify({ learning_role: "teacher" }),
    });
    expect(mockedAdminApi).toHaveBeenNthCalledWith(3, "/users/42/subscription", {
      method: "POST",
      body: JSON.stringify({ plan_key: "premium" }),
    });
    expect(mockedAdminApi).toHaveBeenNthCalledWith(4, "/users/42/subscription-trial", {
      method: "POST",
      body: JSON.stringify({ is_trial_enabled: true }),
    });
    expect(mockedAdminApi).toHaveBeenNthCalledWith(5, "/dashboard/teacher-assignments/42", { method: "DELETE" });
    expect(mockedAdminApi).toHaveBeenNthCalledWith(6, "/users/42/archive", { method: "POST", body: "{}" });
    expect(mockedAdminApi).toHaveBeenNthCalledWith(7, "/users/42", { method: "DELETE" });
    expect(mockedAdminApi).toHaveBeenNthCalledWith(8, "/users/42/password-reset", { method: "POST", body: "{}" });
  });

  it("creates stable query keys", () => {
    const params = {
      archived: true,
      page: 1,
      pageSize: 50,
      roles: ["student"],
      search: "",
      userId: "",
      userType: "student" as const,
    };

    expect(usersQueryKeys.filterMetadata()).toEqual(["users", "filter-metadata"]);
    expect(usersQueryKeys.list(params)).toEqual(["users", "list", params]);
    expect(usersQueryKeys.detail(42)).toEqual(["users", "detail", "42"]);
    expect(usersQueryKeys.detail(null)).toEqual(["users", "detail", ""]);
    expect(usersQueryKeys.loginHistory(42, 10)).toEqual(["users", "login-history", "42", 10]);
    expect(usersQueryKeys.loginHistory(undefined)).toEqual(["users", "login-history", "", "all"]);
  });
});
