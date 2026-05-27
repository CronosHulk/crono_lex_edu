import { describe, expect, it } from "vitest";

import {
  applyImportItemsParamUpdates,
  applyImportJobItemsParamUpdates,
  applyImportJobsParamUpdates,
  importItemsParamsFromSearch,
  importJobItemsParamsFromSearch,
  importJobsParamsFromSearch,
} from "./listParams";

describe("importJobsParamsFromSearch", () => {
  it("reads defaults and explicit import job params", () => {
    expect(importJobsParamsFromSearch(new URLSearchParams())).toEqual({
      page: 1,
      pageSize: 50,
      search: "",
      sourceTypes: [],
      statuses: [],
    });

    expect(importJobsParamsFromSearch(new URLSearchParams("page=2&page_size=100&search=doc&status=completed&source_type=google_doc"))).toEqual({
      page: 2,
      pageSize: 100,
      search: "doc",
      sourceTypes: ["google_doc"],
      statuses: ["completed"],
    });
  });
});

describe("importItemsParamsFromSearch", () => {
  it("reads defaults and explicit import item params", () => {
    expect(importItemsParamsFromSearch(new URLSearchParams())).toEqual({
      importJobId: "",
      page: 1,
      pageSize: 50,
      search: "",
      statuses: [],
      userId: "",
    });

    expect(importItemsParamsFromSearch(new URLSearchParams("page=2&page_size=100&search=word&status=failed&import_job_id=42&user_id=99"))).toEqual({
      importJobId: "42",
      page: 2,
      pageSize: 100,
      search: "word",
      statuses: ["failed"],
      userId: "99",
    });
  });
});

describe("importJobItemsParamsFromSearch", () => {
  it("reads defaults and explicit nested import item params", () => {
    expect(importJobItemsParamsFromSearch(new URLSearchParams())).toEqual({
      itemStatuses: [],
      itemsPage: 1,
      itemsPageSize: 50,
    });

    expect(importJobItemsParamsFromSearch(new URLSearchParams("items_page=3&items_page_size=100&items_status=imported"))).toEqual({
      itemStatuses: ["imported"],
      itemsPage: 3,
      itemsPageSize: 100,
    });
  });
});

describe("applyImportJobsParamUpdates", () => {
  it("writes, preserves, and clears import job params", () => {
    const written = applyImportJobsParamUpdates(new URLSearchParams(), {
      page: 2,
      pageSize: 100,
      search: "doc",
      sourceTypes: ["google_doc"],
      statuses: ["completed"],
    });
    expect(written.toString()).toBe("page=2&page_size=100&search=doc&status=completed&source_type=google_doc");

    expect(applyImportJobsParamUpdates(written, { statuses: ["failed"] }).toString()).toBe("page=2&page_size=100&search=doc&source_type=google_doc&status=failed");
    expect(applyImportJobsParamUpdates(written, { sourceTypes: ["manual"] }).toString()).toBe("page=2&page_size=100&search=doc&status=completed&source_type=manual");
    expect(applyImportJobsParamUpdates(written, { page: 1, pageSize: 50, search: "", sourceTypes: undefined, statuses: [] }).toString()).toBe("");
  });
});

describe("applyImportItemsParamUpdates", () => {
  it("writes, preserves, and clears import item params", () => {
    const written = applyImportItemsParamUpdates(new URLSearchParams(), {
      importJobId: "42",
      page: 2,
      pageSize: 100,
      search: "word",
      statuses: ["pending"],
      userId: "99",
    });
    expect(written.toString()).toBe("page=2&page_size=100&search=word&status=pending&import_job_id=42&user_id=99");

    expect(applyImportItemsParamUpdates(written, { userId: "100" }).toString()).toBe("page=2&page_size=100&search=word&status=pending&import_job_id=42&user_id=100");
    expect(applyImportItemsParamUpdates(written, { importJobId: "84" }).toString()).toBe("page=2&page_size=100&search=word&status=pending&import_job_id=84&user_id=99");
    expect(applyImportItemsParamUpdates(written, { importJobId: "", page: 1, pageSize: 50, search: "", statuses: undefined, userId: "" }).toString()).toBe("");
  });
});

describe("applyImportJobItemsParamUpdates", () => {
  it("writes, preserves, and clears nested import item params", () => {
    const written = applyImportJobItemsParamUpdates(new URLSearchParams(), {
      itemsPage: 3,
      itemsPageSize: 100,
      itemStatuses: ["imported"],
    });
    expect(written.toString()).toBe("items_page=3&items_page_size=100&items_status=imported");

    expect(applyImportJobItemsParamUpdates(written, { itemsPage: 4 }).toString()).toBe("items_page=4&items_page_size=100&items_status=imported");
    expect(applyImportJobItemsParamUpdates(written, { itemsPageSize: 25 }).toString()).toBe("items_page=3&items_page_size=25&items_status=imported");
    expect(applyImportJobItemsParamUpdates(written, { itemsPage: 1, itemsPageSize: 50, itemStatuses: [] }).toString()).toBe("");
  });
});
