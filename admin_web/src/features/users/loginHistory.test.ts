import { describe, expect, it } from "vitest";
import { formatUserTitle, normalizeLoginHistory } from "./loginHistory";

describe("normalizeLoginHistory", () => {
  it("returns array payloads as-is", () => {
    const records = [{ id: 1 }];

    expect(normalizeLoginHistory(records)).toBe(records);
  });

  it("reads items payloads", () => {
    expect(normalizeLoginHistory({ items: [{ id: 2 }] })).toEqual([{ id: 2 }]);
  });

  it("reads records payloads when items are missing", () => {
    expect(normalizeLoginHistory({ records: [{ id: 3 }] })).toEqual([{ id: 3 }]);
  });

  it("reads login_history payloads when earlier keys are missing", () => {
    expect(normalizeLoginHistory({ login_history: [{ id: 4 }] })).toEqual([{ id: 4 }]);
  });

  it("falls back to an empty array for empty payloads", () => {
    expect(normalizeLoginHistory(null)).toEqual([]);
    expect(normalizeLoginHistory(undefined)).toEqual([]);
    expect(normalizeLoginHistory({})).toEqual([]);
  });
});

describe("formatUserTitle", () => {
  it("joins full name, username, and id", () => {
    expect(formatUserTitle({
      first_name: "Ada",
      last_name: "Lovelace",
      username: "ada",
      user_id: "11111111-1111-4111-8111-111111111111",
    })).toBe("Ada Lovelace · @ada · UUID: 11111111-1111-4111-8111-111111111111");
  });

  it("omits missing name parts and username", () => {
    expect(formatUserTitle({
      first_name: "",
      last_name: null,
      username: "",
      user_uuid: "22222222-2222-4222-8222-222222222222",
    })).toBe("UUID: 22222222-2222-4222-8222-222222222222");
  });

  it("keeps a single name part with username and undefined id as before", () => {
    expect(formatUserTitle({
      first_name: "Lin",
      username: "lin",
    })).toBe("Lin · @lin · UUID: ");
  });
});
