import { adminApi } from "../../../api/adminApi";

export type AIUsageParams = {
  page: number;
  pageSize: number;
  period: string;
  search: string;
};

export const aiUsageQueryKeys = {
  all: ["ai-usage"] as const,
  summary: (period: string) => [...aiUsageQueryKeys.all, "summary", period] as const,
  sessions: (params: AIUsageParams) => [...aiUsageQueryKeys.all, "sessions", params] as const,
};

export function fetchAIUsageSummary(period: string) {
  return adminApi(`/ai-usage/summary?period=${encodeURIComponent(period)}`);
}

export function fetchAIUsageSessions(params: AIUsageParams) {
  return adminApi(`/ai-usage/sessions?${aiUsageSearchParams(params).toString()}`);
}

export function deleteAIUsageSessions(payload: unknown) {
  return adminApi("/ai-usage/sessions", { method: "DELETE", body: JSON.stringify(payload) });
}

function aiUsageSearchParams(params: AIUsageParams): URLSearchParams {
  return new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
    period: params.period,
    search: params.search,
  });
}
