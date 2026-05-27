import { adminApi } from "../../../api/adminApi";

export type ImportJobsParams = {
  page: number;
  pageSize: number;
  search: string;
  sourceTypes: string[];
  statuses: string[];
};

export type ImportItemsParams = {
  importJobId: string;
  page: number;
  pageSize: number;
  search: string;
  statuses: string[];
  userId: string;
};

export type ImportJobItemsParams = {
  importJobId: string | number;
  page: number;
  pageSize: number;
  statuses?: string[];
};

export const importsQueryKeys = {
  all: ["imports"] as const,
  jobs: () => [...importsQueryKeys.all, "jobs"] as const,
  jobFilters: () => [...importsQueryKeys.jobs(), "filter-metadata"] as const,
  jobList: (params: ImportJobsParams) => [...importsQueryKeys.jobs(), "list", params] as const,
  jobDetail: (importJobId: string | number | null | undefined) => [...importsQueryKeys.jobs(), "detail", String(importJobId || "")] as const,
  jobItems: (params: ImportJobItemsParams) => [...importsQueryKeys.jobs(), "items", params] as const,
  items: () => [...importsQueryKeys.all, "items"] as const,
  itemFilters: () => [...importsQueryKeys.items(), "filter-metadata"] as const,
  itemList: (params: ImportItemsParams) => [...importsQueryKeys.items(), "list", params] as const,
};

export function fetchImportJobFilters() {
  return adminApi("/import_jobs/filter-metadata");
}

export function fetchImportJobs(params: ImportJobsParams) {
  return adminApi(`/import-jobs?${importJobsSearchParams(params).toString()}`);
}

export function fetchImportJobDetail(importJobId: string | number) {
  return adminApi(`/import-jobs/${encodeURIComponent(String(importJobId))}`);
}

export function fetchImportItemFilters() {
  return adminApi("/import_items/filter-metadata");
}

export function fetchImportItems(params: ImportItemsParams) {
  return adminApi(`/import-items?${importItemsSearchParams(params).toString()}`);
}

export function fetchImportJobItems(params: ImportJobItemsParams) {
  return adminApi(`/import-items?${importJobItemsSearchParams(params).toString()}`);
}

function importJobsSearchParams(params: ImportJobsParams): URLSearchParams {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
    search: params.search,
  });
  params.statuses.forEach((value) => query.append("status", value));
  params.sourceTypes.forEach((value) => query.append("source_type", value));
  return query;
}

function importItemsSearchParams(params: ImportItemsParams): URLSearchParams {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
    search: params.search,
  });
  params.statuses.forEach((value) => query.append("status", value));
  if (params.importJobId.trim()) query.set("import_job_id", params.importJobId.trim());
  if (params.userId.trim()) query.set("user_id", params.userId.trim());
  return query;
}

function importJobItemsSearchParams(params: ImportJobItemsParams): URLSearchParams {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
    import_job_id: String(params.importJobId),
  });
  params.statuses?.forEach((value) => query.append("status", value));
  return query;
}
