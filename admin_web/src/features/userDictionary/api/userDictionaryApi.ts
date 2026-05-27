import { adminApi } from "../../../api/adminApi";

export type UserDictionaryListParams = {
  levelIds: string[];
  page: number;
  pageSize: number;
  partsOfSpeech: string[];
  search: string;
  statuses: string[];
};

export type UserDictionaryPromotePayload = {
  entryIds: Array<string | number>;
};

export type UserDictionaryBulkActionPayload = {
  action: string;
  entryIds: Array<string | number>;
};

export const userDictionaryQueryKeys = {
  all: ["userDictionary"] as const,
  filterMetadata: () => [...userDictionaryQueryKeys.all, "filter-metadata"] as const,
  list: (params: UserDictionaryListParams) => [...userDictionaryQueryKeys.all, "list", params] as const,
  detail: (entryId: string | number | null | undefined) => [...userDictionaryQueryKeys.all, "detail", String(entryId || "")] as const,
};

export function fetchUserDictionaryEntries(params: UserDictionaryListParams) {
  return adminApi(`/user-dictionary/entries?${userDictionarySearchParams(params).toString()}`);
}

export function fetchUserDictionaryEntryDetail(entryId: string | number) {
  return adminApi(`/user-dictionary/entries/${encodeURIComponent(String(entryId))}`);
}

export function fetchUserDictionaryFilterMetadata() {
  return adminApi("/user_dictionary/filter-metadata");
}

export function promoteUserDictionaryEntry(entryId: string | number) {
  return adminApi(`/user-dictionary/entries/${encodeURIComponent(String(entryId))}/promote`, {
    method: "POST",
    body: "{}",
  });
}

export function promoteUserDictionaryEntries({ entryIds }: UserDictionaryPromotePayload) {
  return adminApi("/user-dictionary/entries/promote", {
    method: "POST",
    body: JSON.stringify({ entry_ids: entryIds.map((entryId) => Number(entryId)) }),
  });
}

export function bulkActionUserDictionaryEntries({ action, entryIds }: UserDictionaryBulkActionPayload) {
  return adminApi("/user-dictionary/entries/bulk-action", {
    method: "POST",
    body: JSON.stringify({
      action,
      entry_ids: entryIds.map((entryId) => Number(entryId)),
    }),
  });
}

function userDictionarySearchParams(params: UserDictionaryListParams): URLSearchParams {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
    search: params.search,
  });
  params.statuses.forEach((value) => query.append("status", value));
  params.partsOfSpeech.forEach((value) => query.append("part_of_speech", value));
  params.levelIds.forEach((value) => query.append("level_id", value));
  return query;
}
