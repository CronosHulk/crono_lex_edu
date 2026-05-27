import { beforeEach, describe, expect, it, vi } from "vitest";

import { adminApi } from "../../../api/adminApi";
import {
  archiveDictionaryEntry,
  deleteDictionaryEntry,
  dictionaryQueryKeys,
  fetchDictionaryEntries,
  fetchDictionaryEntry,
  fetchDictionaryFilterMetadata,
  updateDictionaryEntry,
  verifyDictionaryEntries,
} from "./dictionaryApi";

vi.mock("../../../api/adminApi", () => ({
  adminApi: vi.fn(),
}));

const mockedAdminApi = vi.mocked(adminApi);

describe("dictionaryApi", () => {
  beforeEach(() => {
    mockedAdminApi.mockClear();
  });

  it("builds list requests with pagination and repeated part of speech filters", () => {
    fetchDictionaryEntries({
      archived: true,
      page: 2,
      pageSize: 100,
      entryTypes: ["word", "phrasal_verb"],
      partsOfSpeech: ["noun", "verb"],
      search: "run",
      verified: "unverified",
    });

    expect(mockedAdminApi).toHaveBeenCalledWith("/dictionary/entries?page=2&page_size=100&archived=true&search=run&verified=unverified&entry_type=word&entry_type=phrasal_verb&part_of_speech=noun&part_of_speech=verb");
  });

  it("omits the verified filter when all entries are requested", () => {
    fetchDictionaryEntries({
      archived: false,
      page: 1,
      pageSize: 50,
      entryTypes: [],
      partsOfSpeech: [],
      search: "",
      verified: "all",
    });

    expect(mockedAdminApi).toHaveBeenCalledWith("/dictionary/entries?page=1&page_size=50&archived=false&search=");
  });

  it("calls metadata and entry detail endpoints", () => {
    fetchDictionaryFilterMetadata();
    fetchDictionaryEntry(42);

    expect(mockedAdminApi).toHaveBeenNthCalledWith(1, "/dictionary/filter-metadata");
    expect(mockedAdminApi).toHaveBeenNthCalledWith(2, "/dictionary/entries/42");
  });

  it("calls mutation endpoints", () => {
    archiveDictionaryEntry(42);
    deleteDictionaryEntry(42);
    updateDictionaryEntry({ entryId: 42, payload: { word: "run" } });
    verifyDictionaryEntries({ entryIds: [42, "43"] });

    expect(mockedAdminApi).toHaveBeenNthCalledWith(1, "/dictionary/42/archive", { method: "POST", body: "{}" });
    expect(mockedAdminApi).toHaveBeenNthCalledWith(2, "/dictionary/42", { method: "DELETE" });
    expect(mockedAdminApi).toHaveBeenNthCalledWith(3, "/dictionary/entries/42", {
      method: "PATCH",
      body: JSON.stringify({ word: "run" }),
    });
    expect(mockedAdminApi).toHaveBeenNthCalledWith(4, "/dictionary/entries/verify", {
      method: "POST",
      body: JSON.stringify({ entry_ids: [42, 43] }),
    });
  });

  it("creates stable query keys", () => {
    const params = { archived: false, page: 1, pageSize: 50, entryTypes: ["word"], partsOfSpeech: ["noun"], search: "", verified: "all" as const };

    expect(dictionaryQueryKeys.filterMetadata()).toEqual(["dictionary", "filter-metadata"]);
    expect(dictionaryQueryKeys.list(params)).toEqual(["dictionary", "entries", params]);
    expect(dictionaryQueryKeys.detail(42)).toEqual(["dictionary", "entry", "42"]);
    expect(dictionaryQueryKeys.detail(null)).toEqual(["dictionary", "entry", ""]);
  });
});
