export type DictionaryListSearchParams = {
  archived: boolean;
  entryTypes: string[];
  page: number;
  pageSize: number;
  partsOfSpeech: string[];
  search: string;
  verified: "all" | "verified" | "unverified";
};

export function dictionaryListParamsFromSearch(searchParams: URLSearchParams): DictionaryListSearchParams {
  return {
    archived: searchParams.get("archived") === "true",
    entryTypes: searchParams.getAll("entry_type"),
    page: positiveIntParam(searchParams.get("page"), 1),
    pageSize: positiveIntParam(searchParams.get("page_size"), 50),
    partsOfSpeech: searchParams.getAll("part_of_speech"),
    search: searchParams.get("search") || "",
    verified: verifiedParam(searchParams.get("verified")),
  };
}

export function applyDictionaryListParamUpdates(searchParams: URLSearchParams, updates: Partial<DictionaryListSearchParams>): URLSearchParams {
  const next = new URLSearchParams(searchParams);
  if ("page" in updates) setSearchParam(next, "page", updates.page, 1);
  if ("pageSize" in updates) setSearchParam(next, "page_size", updates.pageSize, 50);
  if ("archived" in updates) setSearchParam(next, "archived", updates.archived, false);
  if ("search" in updates) setSearchParam(next, "search", updates.search, "");
  if ("verified" in updates) setSearchParam(next, "verified", updates.verified, "all");
  if ("entryTypes" in updates) {
    next.delete("entry_type");
    updates.entryTypes?.forEach((value) => next.append("entry_type", value));
  }
  if ("partsOfSpeech" in updates) {
    next.delete("part_of_speech");
    updates.partsOfSpeech?.forEach((value) => next.append("part_of_speech", value));
  }
  return next;
}

function verifiedParam(value: string | null): "all" | "verified" | "unverified" {
  if (value === "verified" || value === "unverified") return value;
  return "all";
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
