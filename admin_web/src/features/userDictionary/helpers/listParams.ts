export type UserDictionaryListSearchParams = {
  levelIds: string[];
  page: number;
  pageSize: number;
  partsOfSpeech: string[];
  search: string;
  statuses: string[];
};

export function userDictionaryParamsFromSearch(searchParams: URLSearchParams): UserDictionaryListSearchParams {
  return {
    levelIds: searchParams.getAll("level_id"),
    page: positiveIntParam(searchParams.get("page"), 1),
    pageSize: positiveIntParam(searchParams.get("page_size"), 50),
    partsOfSpeech: searchParams.getAll("part_of_speech"),
    search: searchParams.get("search") || "",
    statuses: searchParams.getAll("status"),
  };
}

export function applyUserDictionaryParamUpdates(
  searchParams: URLSearchParams,
  updates: Partial<UserDictionaryListSearchParams>,
): URLSearchParams {
  const next = new URLSearchParams(searchParams);
  if ("page" in updates) setSearchParam(next, "page", updates.page, 1);
  if ("pageSize" in updates) setSearchParam(next, "page_size", updates.pageSize, 50);
  if ("search" in updates) setSearchParam(next, "search", updates.search, "");
  if ("statuses" in updates) setRepeatedSearchParam(next, "status", updates.statuses);
  if ("partsOfSpeech" in updates) setRepeatedSearchParam(next, "part_of_speech", updates.partsOfSpeech);
  if ("levelIds" in updates) setRepeatedSearchParam(next, "level_id", updates.levelIds);
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
