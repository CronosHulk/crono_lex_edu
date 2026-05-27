import { describe, expect, it } from "vitest";

import { canAdminAccess, readCapabilities } from "./adminAcl";

describe("adminAcl", () => {
  it("checks backend-provided capabilities", () => {
    const user = { acl_capabilities: ["dictionary/list_words", "users/view"] };

    expect(canAdminAccess(user, "dictionary/list_words")).toBe(true);
    expect(canAdminAccess(user, "imports/run_now")).toBe(false);
  });

  it("ignores malformed capabilities", () => {
    expect(readCapabilities({ acl_capabilities: ["users/view", 1, null] })).toEqual(["users/view"]);
    expect(readCapabilities({ acl_capabilities: "users/view" })).toEqual([]);
    expect(canAdminAccess(null, "users/view")).toBe(false);
  });
});
