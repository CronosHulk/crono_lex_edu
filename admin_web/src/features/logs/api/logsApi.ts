import { adminApi } from "../../../api/adminApi";

export type TaskLogScope = "all" | "billing" | "operations";

export type TaskLogsParams = {
  page: number;
  pageSize: number;
  search: string;
  scope?: TaskLogScope;
  statuses: string[];
  taskTypes: string[];
};

export type ErrorLogsParams = {
  levels: string[];
  page: number;
  pageSize: number;
  search: string;
};

export const logsQueryKeys = {
  all: ["logs"] as const,
  taskLogs: () => [...logsQueryKeys.all, "task-logs"] as const,
  taskLogFilters: (scope: TaskLogScope = "operations") => [...logsQueryKeys.taskLogs(), "filter-metadata", scope] as const,
  taskLogList: (params: TaskLogsParams) => [...logsQueryKeys.taskLogs(), "list", params] as const,
  taskLogDetail: (taskLogId: string | number | null | undefined) => [...logsQueryKeys.taskLogs(), "detail", String(taskLogId || "")] as const,
  errorLogs: () => [...logsQueryKeys.all, "error-log"] as const,
  errorLogFilters: () => [...logsQueryKeys.errorLogs(), "filter-metadata"] as const,
  errorLogList: (params: ErrorLogsParams) => [...logsQueryKeys.errorLogs(), "list", params] as const,
};

export function fetchTaskLogFilters(scope: TaskLogScope = "operations") {
  return adminApi(`/task_logs/filter-metadata?scope=${encodeURIComponent(scope)}`);
}

export function fetchTaskLogs(params: TaskLogsParams) {
  return adminApi(`/task-logs?${taskLogsSearchParams(params).toString()}`);
}

export function fetchTaskLogDetail(taskLogId: string | number) {
  return adminApi(`/task-logs/${encodeURIComponent(String(taskLogId))}`);
}

export function fetchErrorLogFilters() {
  return adminApi("/error_log/filter-metadata");
}

export function fetchErrorLogs(params: ErrorLogsParams) {
  return adminApi(`/error-log?${errorLogsSearchParams(params).toString()}`);
}

function taskLogsSearchParams(params: TaskLogsParams): URLSearchParams {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
    search: params.search,
    scope: params.scope || "operations",
  });
  params.taskTypes.forEach((value) => query.append("task_type", value));
  params.statuses.forEach((value) => query.append("status", value));
  return query;
}

function errorLogsSearchParams(params: ErrorLogsParams): URLSearchParams {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
    search: params.search,
  });
  params.levels.forEach((value) => query.append("level", value));
  return query;
}
