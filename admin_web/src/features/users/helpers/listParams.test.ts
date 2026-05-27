import { describe, expect, it } from "vitest";

import { applyUsersListParamUpdates, usersListParamsFromSearch } from "./listParams";

describe("usersListParamsFromSearch", () => {
  it("reads list params with defaults", () => {
    expect(usersListParamsFromSearch(new URLSearchParams())).toEqual({
      archived: false,
      page: 1,
      pageSize: 50,
      roles: [],
      search: "",
      userId: "",
      userType: "student",
    });
  });

  it("reads explicit list params and repeated roles", () => {
    const params = new URLSearchParams("archived=true&page=3&page_size=100&search=ada&user_id=111&user_type=teacher&role=admin&role=teacher");

    expect(usersListParamsFromSearch(params)).toEqual({
      archived: true,
      page: 3,
      pageSize: 100,
      roles: ["admin", "teacher"],
      search: "ada",
      userId: "111",
      userType: "teacher",
    });
  });

  it("falls back from invalid positive integer params", () => {
    const params = new URLSearchParams("page=0&page_size=-1&user_type=ghost");

    expect(usersListParamsFromSearch(params)).toMatchObject({ page: 1, pageSize: 50, userType: "student" });
  });
});

describe("applyUsersListParamUpdates", () => {
  it("updates params and removes default values", () => {
    const params = new URLSearchParams("page=2&page_size=100&search=ada&archived=true&role=admin");

    expect(applyUsersListParamUpdates(params, {
      archived: false,
      page: 1,
      pageSize: 50,
      roles: [],
      search: "",
      userId: "",
      userType: "student",
    }).toString()).toBe("");
  });

  it("writes non-default params", () => {
    const result = applyUsersListParamUpdates(new URLSearchParams(), {
      archived: true,
      page: 2,
      pageSize: 100,
      roles: ["admin", "teacher"],
      search: "ada",
      userId: "111",
      userType: "teacher",
    });

    expect(result.toString()).toBe("page=2&page_size=100&archived=true&search=ada&user_id=111&user_type=teacher&role=admin&role=teacher");
  });

  it("updates only provided params and preserves the rest", () => {
    const params = new URLSearchParams("page=2&page_size=100&archived=true&search=ada&role=admin");

    expect(applyUsersListParamUpdates(params, { search: "lin" }).toString()).toBe("page=2&page_size=100&archived=true&search=lin&role=admin");
  });

  it("clears roles when roles update is undefined", () => {
    const params = new URLSearchParams("role=admin&role=teacher");

    expect(applyUsersListParamUpdates(params, { roles: undefined }).toString()).toBe("");
  });
});
