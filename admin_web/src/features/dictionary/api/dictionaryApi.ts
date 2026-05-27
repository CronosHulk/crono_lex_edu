import { adminApi } from "../../../api/adminApi";

export type DictionaryListParams = {
  archived: boolean;
  page: number;
  pageSize: number;
  entryTypes: string[];
  partsOfSpeech: string[];
  search: string;
  verified: "all" | "verified" | "unverified";
};

export type DictionaryEntryUpdate = {
  entryId: string | number;
  payload: unknown;
};

export type DictionaryVerifyPayload = {
  entryIds: Array<string | number>;
};

export const dictionaryQueryKeys = {
  all: ["dictionary"] as const,
  filterMetadata: () => [...dictionaryQueryKeys.all, "filter-metadata"] as const,
  lists: () => [...dictionaryQueryKeys.all, "entries"] as const,
  list: (params: DictionaryListParams) => [...dictionaryQueryKeys.lists(), params] as const,
  details: () => [...dictionaryQueryKeys.all, "entry"] as const,
  detail: (entryId: string | number | null | undefined) => [...dictionaryQueryKeys.details(), String(entryId || "")] as const,
};

export function fetchDictionaryEntries(params: DictionaryListParams) {
  return adminApi(`/dictionary/entries?${dictionaryListSearchParams(params).toString()}`);
}

export function fetchDictionaryFilterMetadata() {
  return adminApi("/dictionary/filter-metadata");
}

export function archiveDictionaryEntry(entryId: string | number) {
  return adminApi(`/dictionary/${encodeURIComponent(String(entryId))}/archive`, { method: "POST", body: "{}" });
}

export function deleteDictionaryEntry(entryId: string | number) {
  return adminApi(`/dictionary/${encodeURIComponent(String(entryId))}`, { method: "DELETE" });
}

export function fetchDictionaryEntry(entryId: string | number) {
  return adminApi(`/dictionary/entries/${encodeURIComponent(String(entryId))}`);
}

export function updateDictionaryEntry({ entryId, payload }: DictionaryEntryUpdate) {
  return adminApi(`/dictionary/entries/${encodeURIComponent(String(entryId))}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function verifyDictionaryEntries({ entryIds }: DictionaryVerifyPayload) {
  return adminApi("/dictionary/entries/verify", {
    method: "POST",
    body: JSON.stringify({ entry_ids: entryIds.map((entryId) => Number(entryId)) }),
  });
}

function dictionaryListSearchParams(params: DictionaryListParams): URLSearchParams {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
    archived: String(params.archived),
    search: params.search,
  });
  if (params.verified !== "all") query.set("verified", params.verified);
  params.entryTypes.forEach((value) => query.append("entry_type", value));
  params.partsOfSpeech.forEach((value) => query.append("part_of_speech", value));
  return query;
}
