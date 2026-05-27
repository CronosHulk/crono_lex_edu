import { describe, expect, it } from "vitest";

import { applyDictionaryListParamUpdates, dictionaryListParamsFromSearch } from "./listParams";

describe("dictionaryListParamsFromSearch", () => {
  it("reads defaults", () => {
    expect(dictionaryListParamsFromSearch(new URLSearchParams())).toEqual({
      archived: false,
      entryTypes: [],
      page: 1,
      pageSize: 50,
      partsOfSpeech: [],
      search: "",
      verified: "all",
    });
  });

  it("reads explicit params", () => {
    const params = new URLSearchParams("archived=true&page=2&page_size=100&search=run&verified=verified&entry_type=word&entry_type=idiom&part_of_speech=noun&part_of_speech=verb");

    expect(dictionaryListParamsFromSearch(params)).toEqual({
      archived: true,
      entryTypes: ["word", "idiom"],
      page: 2,
      pageSize: 100,
      partsOfSpeech: ["noun", "verb"],
      search: "run",
      verified: "verified",
    });
  });
});

describe("applyDictionaryListParamUpdates", () => {
  it("removes default values", () => {
    const params = new URLSearchParams("page=2&page_size=100&archived=true&search=run&entry_type=word&part_of_speech=noun");

    expect(applyDictionaryListParamUpdates(params, {
      archived: false,
      entryTypes: [],
      page: 1,
      pageSize: 50,
      partsOfSpeech: [],
      search: "",
      verified: "all",
    }).toString()).toBe("");
  });

  it("writes non-default values", () => {
    const result = applyDictionaryListParamUpdates(new URLSearchParams(), {
      archived: true,
      page: 2,
      pageSize: 100,
      entryTypes: ["word", "idiom"],
      partsOfSpeech: ["noun", "verb"],
      search: "run",
      verified: "unverified",
    });

    expect(result.toString()).toBe("page=2&page_size=100&archived=true&search=run&verified=unverified&entry_type=word&entry_type=idiom&part_of_speech=noun&part_of_speech=verb");
  });

  it("updates only provided params and preserves the rest", () => {
    const params = new URLSearchParams("page=2&page_size=100&archived=true&search=run&entry_type=word&part_of_speech=noun");

    expect(applyDictionaryListParamUpdates(params, { search: "walk" }).toString()).toBe("page=2&page_size=100&archived=true&search=walk&entry_type=word&part_of_speech=noun");
  });

  it("clears entry type values when update is undefined", () => {
    const params = new URLSearchParams("entry_type=word&entry_type=idiom");

    expect(applyDictionaryListParamUpdates(params, { entryTypes: undefined }).toString()).toBe("");
  });

  it("clears part of speech values when update is undefined", () => {
    const params = new URLSearchParams("part_of_speech=noun&part_of_speech=verb");

    expect(applyDictionaryListParamUpdates(params, { partsOfSpeech: undefined }).toString()).toBe("");
  });
});
