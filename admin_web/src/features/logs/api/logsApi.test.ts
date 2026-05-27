import { beforeEach, describe, expect, it, vi } from "vitest";

import { adminApi } from "../../../api/adminApi";
import {
  fetchErrorLogFilters,
  fetchErrorLogs,
  fetchTaskLogDetail,
  fetchTaskLogFilters,
  fetchTaskLogs,
  logsQueryKeys,
} from "./logsApi";

vi.mock("../../../api/adminApi", () => ({
  adminApi: vi.fn(),
}));

const mockedAdminApi = vi.mocked(adminApi);

describe("logsApi", () => {
  beforeEach(() => {
    mockedAdminApi.mockClear();
  });

  it("builds task log list requests", () => {
    fetchTaskLogs({ page: 2, pageSize: 100, search: "sync", scope: "operations", statuses: ["done"], taskTypes: ["import", "audio"] });
    fetchTaskLogs({ page: 1, pageSize: 50, search: "", statuses: [], taskTypes: [] });

    expect(mockedAdminApi).toHaveBeenNthCalledWith(1, "/task-logs?page=2&page_size=100&search=sync&scope=operations&task_type=import&task_type=audio&status=done");
    expect(mockedAdminApi).toHaveBeenNthCalledWith(2, "/task-logs?page=1&page_size=50&search=&scope=operations");
  });

  it("calls task log metadata and detail endpoints", () => {
    fetchTaskLogFilters("billing");
    fetchTaskLogDetail(42);

    expect(mockedAdminApi).toHaveBeenNthCalledWith(1, "/task_logs/filter-metadata?scope=billing");
    expect(mockedAdminApi).toHaveBeenNthCalledWith(2, "/task-logs/42");
  });

  it("builds error log requests", () => {
    fetchErrorLogFilters();
    fetchErrorLogs({ page: 3, pageSize: 50, search: "boom", levels: ["warn", "fatal"] });

    expect(mockedAdminApi).toHaveBeenNthCalledWith(1, "/error_log/filter-metadata");
    expect(mockedAdminApi).toHaveBeenNthCalledWith(2, "/error-log?page=3&page_size=50&search=boom&level=warn&level=fatal");
  });

  it("creates stable query keys", () => {
    const taskParams = { page: 1, pageSize: 50, search: "", scope: "operations" as const, statuses: ["done"], taskTypes: ["import"] };
    const errorParams = { page: 1, pageSize: 50, search: "", levels: ["warn"] };

    expect(logsQueryKeys.taskLogFilters()).toEqual(["logs", "task-logs", "filter-metadata", "operations"]);
    expect(logsQueryKeys.taskLogFilters("billing")).toEqual(["logs", "task-logs", "filter-metadata", "billing"]);
    expect(logsQueryKeys.taskLogList(taskParams)).toEqual(["logs", "task-logs", "list", taskParams]);
    expect(logsQueryKeys.taskLogDetail(42)).toEqual(["logs", "task-logs", "detail", "42"]);
    expect(logsQueryKeys.taskLogDetail(null)).toEqual(["logs", "task-logs", "detail", ""]);
    expect(logsQueryKeys.errorLogFilters()).toEqual(["logs", "error-log", "filter-metadata"]);
    expect(logsQueryKeys.errorLogList(errorParams)).toEqual(["logs", "error-log", "list", errorParams]);
  });
});
