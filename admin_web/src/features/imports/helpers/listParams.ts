export type ImportJobsSearchParams = {
  page: number;
  pageSize: number;
  search: string;
  sourceTypes: string[];
  statuses: string[];
};

export type ImportItemsSearchParams = {
  importJobId: string;
  page: number;
  pageSize: number;
  search: string;
  statuses: string[];
  userId: string;
};

export type ImportJobItemsSearchParams = {
  itemsPage: number;
  itemsPageSize: number;
  itemStatuses: string[];
};

export function importJobsParamsFromSearch(searchParams: URLSearchParams): ImportJobsSearchParams {
  return {
    page: positiveIntParam(searchParams.get("page"), 1),
    pageSize: positiveIntParam(searchParams.get("page_size"), 50),
    search: searchParams.get("search") || "",
    sourceTypes: searchParams.getAll("source_type"),
    statuses: searchParams.getAll("status"),
  };
}

export function importItemsParamsFromSearch(searchParams: URLSearchParams): ImportItemsSearchParams {
  return {
    importJobId: searchParams.get("import_job_id") || "",
    page: positiveIntParam(searchParams.get("page"), 1),
    pageSize: positiveIntParam(searchParams.get("page_size"), 50),
    search: searchParams.get("search") || "",
    statuses: searchParams.getAll("status"),
    userId: searchParams.get("user_id") || "",
  };
}

export function importJobItemsParamsFromSearch(searchParams: URLSearchParams): ImportJobItemsSearchParams {
  return {
    itemsPage: positiveIntParam(searchParams.get("items_page"), 1),
    itemsPageSize: positiveIntParam(searchParams.get("items_page_size"), 50),
    itemStatuses: searchParams.getAll("items_status"),
  };
}

export function applyImportJobsParamUpdates(searchParams: URLSearchParams, updates: Partial<ImportJobsSearchParams>): URLSearchParams {
  const next = new URLSearchParams(searchParams);
  if ("page" in updates) setSearchParam(next, "page", updates.page, 1);
  if ("pageSize" in updates) setSearchParam(next, "page_size", updates.pageSize, 50);
  if ("search" in updates) setSearchParam(next, "search", updates.search, "");
  if ("statuses" in updates) setRepeatedSearchParam(next, "status", updates.statuses);
  if ("sourceTypes" in updates) setRepeatedSearchParam(next, "source_type", updates.sourceTypes);
  return next;
}

export function applyImportItemsParamUpdates(searchParams: URLSearchParams, updates: Partial<ImportItemsSearchParams>): URLSearchParams {
  const next = new URLSearchParams(searchParams);
  if ("page" in updates) setSearchParam(next, "page", updates.page, 1);
  if ("pageSize" in updates) setSearchParam(next, "page_size", updates.pageSize, 50);
  if ("search" in updates) setSearchParam(next, "search", updates.search, "");
  if ("statuses" in updates) setRepeatedSearchParam(next, "status", updates.statuses);
  if ("importJobId" in updates) setSearchParam(next, "import_job_id", updates.importJobId, "");
  if ("userId" in updates) setSearchParam(next, "user_id", updates.userId, "");
  return next;
}

export function applyImportJobItemsParamUpdates(searchParams: URLSearchParams, updates: Partial<ImportJobItemsSearchParams>): URLSearchParams {
  const next = new URLSearchParams(searchParams);
  if ("itemsPage" in updates) setSearchParam(next, "items_page", updates.itemsPage, 1);
  if ("itemsPageSize" in updates) setSearchParam(next, "items_page_size", updates.itemsPageSize, 50);
  if ("itemStatuses" in updates) setRepeatedSearchParam(next, "items_status", updates.itemStatuses);
  return next;
}

function positiveIntParam(value: string | null, fallback: number): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function setSearchParam(params: URLSearchParams, key: string, value: unknown, defaultValue: unknown) {
  if (value === defaultValue || value === "" || value === null || value === undefined) {
    params.delete(key);
    return;
  }
  params.set(key, String(value));
}

function setRepeatedSearchParam(params: URLSearchParams, key: string, values: string[] | undefined) {
  params.delete(key);
  values?.forEach((value) => params.append(key, value));
}
