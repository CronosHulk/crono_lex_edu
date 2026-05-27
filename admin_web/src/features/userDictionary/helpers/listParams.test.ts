import { describe, expect, it } from "vitest";
import {
  applyUserDictionaryParamUpdates,
  userDictionaryParamsFromSearch,
} from "./listParams";

describe("userDictionaryParamsFromSearch", () => {
  it("reads pagination and filters", () => {
    const params = userDictionaryParamsFromSearch(
      new URLSearchParams("page=2&page_size=100&search=cord&status=ready_for_rotation&part_of_speech=noun&level_id=3"),
    );

    expect(params).toEqual({
      levelIds: ["3"],
      page: 2,
      pageSize: 100,
      partsOfSpeech: ["noun"],
      search: "cord",
      statuses: ["ready_for_rotation"],
    });
  });

  it("falls back to safe pagination", () => {
    const params = userDictionaryParamsFromSearch(new URLSearchParams("page=-1&page_size=nope"));

    expect(params.page).toBe(1);
    expect(params.pageSize).toBe(50);
  });
});

describe("applyUserDictionaryParamUpdates", () => {
  it("writes and clears URL params", () => {
    const next = applyUserDictionaryParamUpdates(new URLSearchParams("page=3&search=old"), {
      levelIds: ["1", "2"],
      page: 1,
      partsOfSpeech: ["verb"],
      search: "",
      statuses: ["queued_for_details"],
    });

    expect(next.toString()).toBe("status=queued_for_details&part_of_speech=verb&level_id=1&level_id=2");
  });

  it("keeps non-default pagination and search params", () => {
    const next = applyUserDictionaryParamUpdates(new URLSearchParams(), {
      page: 3,
      pageSize: 100,
      search: "cord",
    });

    expect(next.toString()).toBe("page=3&page_size=100&search=cord");
  });

  it("updates repeated filters without touching existing pagination", () => {
    const next = applyUserDictionaryParamUpdates(new URLSearchParams("page=4&search=cord"), {
      statuses: ["ready_for_rotation"],
    });

    expect(next.toString()).toBe("page=4&search=cord&status=ready_for_rotation");
  });
});
