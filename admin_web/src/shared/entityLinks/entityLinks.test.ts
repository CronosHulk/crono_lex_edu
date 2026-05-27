import { describe, expect, it } from "vitest";
import { extractEntityLinks, normalizeEntityId } from "./entityLinks";

describe("normalizeEntityId", () => {
  it("accepts safe positive integer numbers and digit strings", () => {
    expect(normalizeEntityId(1)).toBe(1);
    expect(normalizeEntityId("42")).toBe(42);
    expect(normalizeEntityId(" 7 ")).toBe(7);
  });

  it("rejects invalid ids", () => {
    expect(normalizeEntityId(0)).toBeNull();
    expect(normalizeEntityId(-1)).toBeNull();
    expect(normalizeEntityId(1.5)).toBeNull();
    expect(normalizeEntityId(Number.MAX_SAFE_INTEGER + 1)).toBeNull();
    expect(normalizeEntityId("0")).toBeNull();
    expect(normalizeEntityId("-1")).toBeNull();
    expect(normalizeEntityId("1.5")).toBeNull();
    expect(normalizeEntityId("abc")).toBeNull();
    expect(normalizeEntityId("9007199254740992")).toBeNull();
    expect(normalizeEntityId(null)).toBeNull();
    expect(normalizeEntityId({ id: 1 })).toBeNull();
  });
});

describe("extractEntityLinks", () => {
  it("extracts allowlisted singular entity ids", () => {
    const userId = "11111111-1111-4111-8111-111111111111";
    const actorUserId = "22222222-2222-4222-8222-222222222222";
    expect(extractEntityLinks({
      user_id: userId,
      actor_user_id: actorUserId,
      import_job_id: 5,
      created_import_job_id: 6,
      task_log_id: 7,
      dictionary_entry_id: 9,
      existing_word_id: 10,
      word_id: 11,
      user_dictionary_entry_id: 12
    })).toEqual([
      { type: "user", id: userId },
      { type: "user", id: actorUserId },
      { type: "import_job", id: 5 },
      { type: "import_job", id: 6 },
      { type: "task_log", id: 7 },
      { type: "dictionary_entry", id: 9 },
      { type: "dictionary_entry", id: 10 },
      { type: "dictionary_entry", id: 11 },
      { type: "user_dictionary_entry", id: 12 }
    ]);
  });

  it("extracts allowlisted plural entity ids and ignores invalid array items", () => {
    const firstUserId = "11111111-1111-4111-8111-111111111111";
    const secondUserId = "22222222-2222-4222-8222-222222222222";
    expect(extractEntityLinks({
      user_ids: [firstUserId, "not-a-uuid"],
      user_uuids: [secondUserId],
      import_job_ids: [4],
      task_log_ids: [5],
      dictionary_entry_ids: [7],
      existing_word_ids: [8],
      word_ids: [9],
      user_dictionary_entry_ids: [10]
    })).toEqual([
      { type: "user", id: firstUserId },
      { type: "user", id: secondUserId },
      { type: "import_job", id: 4 },
      { type: "task_log", id: 5 },
      { type: "dictionary_entry", id: 7 },
      { type: "dictionary_entry", id: 8 },
      { type: "dictionary_entry", id: 9 },
      { type: "user_dictionary_entry", id: 10 }
    ]);
  });

  it("walks nested objects and arrays within the max depth", () => {
    const payload = {
      wrapper: [
        {
          nested: {
            items: [
              {
                import_job_id: "12"
              }
            ]
          }
        }
      ]
    };

    expect(extractEntityLinks(payload)).toEqual([{ type: "import_job", id: 12 }]);
  });

  it("stops walking after the max depth", () => {
    const tooDeep = {
      one: {
        two: {
          three: {
            four: {
              five: {
                six: {
                  task_log_id: 99
                }
              }
            }
          }
        }
      }
    };

    expect(extractEntityLinks(tooDeep)).toEqual([]);
  });

  it("deduplicates links by type and id", () => {
    const userId = "11111111-1111-4111-8111-111111111111";
    expect(extractEntityLinks({
      user_id: userId,
      user_uuid: userId,
      import_job_id: 1
    })).toEqual([
      { type: "user", id: userId },
      { type: "import_job", id: 1 }
    ]);
  });

  it("caps links at twenty", () => {
    const ids = Array.from({ length: 25 }, (_, index) => index + 1);
    const links = extractEntityLinks({ user_ids: ids });

    expect(links).toHaveLength(20);
    expect(links.at(0)).toEqual({ type: "user", id: 1 });
    expect(links.at(-1)).toEqual({ type: "user", id: 20 });
  });

  it("ignores arbitrary url-like keys and unsupported id labels", () => {
    expect(extractEntityLinks({
      url: "https://example.com/admin/users/1",
      href: "/admin/import-jobs/2",
      label: "User #1",
      custom_user_reference: 3,
      task_log_id: "not-a-number"
    })).toEqual([]);
  });

  it("returns no links for empty, primitive, or array-only payloads", () => {
    expect(extractEntityLinks(null)).toEqual([]);
    expect(extractEntityLinks("task_log_id=1")).toEqual([]);
    expect(extractEntityLinks([1, 2, 3])).toEqual([]);
  });
});
