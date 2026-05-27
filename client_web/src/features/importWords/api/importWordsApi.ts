import { useEffect } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { CLIENT_API_BASE, clientApi } from "../../../api/clientApi";
import { learningWordsKey } from "../../learning/api/learningApi";
import { settingsKey } from "../../settings/api/settingsApi";

export const importWordsQueryKeys = {
  all: ["import-words"] as const,
  items: (page: number, pageSize: number, statusCategory: string) =>
    [...importWordsQueryKeys.all, "items", page, pageSize, statusCategory] as const,
  jobItems: (jobId: number | null, page: number, pageSize: number, statusCategory: string) =>
    [...importWordsQueryKeys.all, "job-items", jobId, page, pageSize, statusCategory] as const,
};

export type ImportWordsSubmitPayload = {
  source_url?: string | null;
  text_content?: string | null;
  file_name?: string | null;
};

export function useSubmitImportWords() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ImportWordsSubmitPayload) =>
      clientApi<{ job: { id: number }; results: unknown }>("/imports", {
        method: "POST",
        body: JSON.stringify(payload),
    }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: importWordsQueryKeys.all });
      queryClient.invalidateQueries({ queryKey: [...importWordsQueryKeys.all, "job-items", data.job.id] });
      queryClient.invalidateQueries({ queryKey: learningWordsKey });
      queryClient.invalidateQueries({ queryKey: settingsKey });
    },
  });
}

export function useUnbindImportGoogleDoc() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => clientApi("/imports/google-doc-binding", { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKey });
      queryClient.invalidateQueries({ queryKey: importWordsQueryKeys.all });
    },
  });
}

export function useImportItems(page: number, pageSize: number, statusCategory: string, enabled = true) {
  return useQuery({
    queryKey: importWordsQueryKeys.items(page, pageSize, statusCategory),
    queryFn: () => clientApi(`/imports/items?${importJobItemsSearchParams(page, pageSize, statusCategory).toString()}`),
    enabled,
    placeholderData: keepPreviousData,
    retry: false,
  });
}

export function useImportJobItems(jobId: number | null, page: number, pageSize: number, statusCategory: string) {
  return useQuery({
    queryKey: importWordsQueryKeys.jobItems(jobId, page, pageSize, statusCategory),
    queryFn: () => clientApi(`/imports/${jobId}/items?${importJobItemsSearchParams(page, pageSize, statusCategory).toString()}`),
    enabled: Boolean(jobId),
    placeholderData: keepPreviousData,
    retry: false,
  });
}

export function useImportJobEvents(jobId: number | null) {
  const queryClient = useQueryClient();
  useEffect(() => {
    if (!jobId) return undefined;
    const events = new EventSource(`${CLIENT_API_BASE}/imports/events?job_id=${jobId}`);
    const invalidateJobResults = () => {
      queryClient.invalidateQueries({ queryKey: [...importWordsQueryKeys.all, "job-items", jobId] });
    };
    const invalidateCompletedImport = () => {
      invalidateJobResults();
      queryClient.invalidateQueries({ queryKey: learningWordsKey });
      queryClient.invalidateQueries({ queryKey: settingsKey });
    };

    events.addEventListener("processing", invalidateJobResults);
    events.addEventListener("items_changed", invalidateJobResults);
    events.addEventListener("completed", invalidateCompletedImport);
    events.addEventListener("failed", invalidateCompletedImport);

    return () => events.close();
  }, [jobId, queryClient]);
}

function importJobItemsSearchParams(page: number, pageSize: number, statusCategory: string): URLSearchParams {
  return new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    status_category: statusCategory,
  });
}
