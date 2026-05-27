import { beforeEach, describe, expect, it, vi } from "vitest";

import { adminApi } from "../../../api/adminApi";
import {
  bulkActionUserDictionaryEntries,
  fetchUserDictionaryEntryDetail,
  fetchUserDictionaryEntries,
  fetchUserDictionaryFilterMetadata,
  promoteUserDictionaryEntries,
  promoteUserDictionaryEntry,
  userDictionaryQueryKeys,
} from "./userDictionaryApi";

vi.mock("../../../api/adminApi", () => ({
  adminApi: vi.fn(),
}));

const mockedAdminApi = vi.mocked(adminApi);

describe("userDictionaryApi", () => {
  beforeEach(() => {
    mockedAdminApi.mockClear();
  });

  it("builds list requests with repeated filters", () => {
    const params = {
      levelIds: ["2"],
      page: 2,
      pageSize: 100,
      partsOfSpeech: ["noun"],
      search: "cord",
      statuses: ["ready_for_rotation"],
    };

    fetchUserDictionaryEntries(params);

    expect(mockedAdminApi).toHaveBeenCalledWith(
      "/user-dictionary/entries?page=2&page_size=100&search=cord&status=ready_for_rotation&part_of_speech=noun&level_id=2",
    );
  });

  it("calls metadata endpoint and creates stable query keys", () => {
    const params = { levelIds: [], page: 1, pageSize: 50, partsOfSpeech: [], search: "", statuses: [] };

    fetchUserDictionaryFilterMetadata();

    expect(mockedAdminApi).toHaveBeenCalledWith("/user_dictionary/filter-metadata");
    expect(userDictionaryQueryKeys.filterMetadata()).toEqual(["userDictionary", "filter-metadata"]);
    expect(userDictionaryQueryKeys.list(params)).toEqual(["userDictionary", "list", params]);
    expect(userDictionaryQueryKeys.detail(7)).toEqual(["userDictionary", "detail", "7"]);
    expect(userDictionaryQueryKeys.detail(null)).toEqual(["userDictionary", "detail", ""]);
  });

  it("loads user dictionary entry details", () => {
    fetchUserDictionaryEntryDetail(7);

    expect(mockedAdminApi).toHaveBeenCalledWith("/user-dictionary/entries/7");
  });

  it("promotes user dictionary entries", () => {
    promoteUserDictionaryEntry(7);
    promoteUserDictionaryEntries({ entryIds: [7, "8"] });

    expect(mockedAdminApi).toHaveBeenNthCalledWith(1, "/user-dictionary/entries/7/promote", {
      method: "POST",
      body: "{}",
    });
    expect(mockedAdminApi).toHaveBeenNthCalledWith(2, "/user-dictionary/entries/promote", {
      method: "POST",
      body: JSON.stringify({ entry_ids: [7, 8] }),
    });
  });

  it("executes user dictionary bulk actions", () => {
    bulkActionUserDictionaryEntries({ action: "rebuild_embedding", entryIds: [7, "8"] });

    expect(mockedAdminApi).toHaveBeenCalledWith("/user-dictionary/entries/bulk-action", {
      method: "POST",
      body: JSON.stringify({ action: "rebuild_embedding", entry_ids: [7, 8] }),
    });
  });
});
