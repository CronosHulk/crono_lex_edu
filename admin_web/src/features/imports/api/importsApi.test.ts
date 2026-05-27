import { beforeEach, describe, expect, it, vi } from "vitest";

import { adminApi } from "../../../api/adminApi";
import {
  fetchImportItemFilters,
  fetchImportItems,
  fetchImportJobDetail,
  fetchImportJobFilters,
  fetchImportJobItems,
  fetchImportJobs,
  importsQueryKeys,
} from "./importsApi";

vi.mock("../../../api/adminApi", () => ({
  adminApi: vi.fn(),
}));

const mockedAdminApi = vi.mocked(adminApi);

describe("importsApi", () => {
  beforeEach(() => {
    mockedAdminApi.mockClear();
  });

  it("builds import job list requests with repeated filters", () => {
    fetchImportJobs({ page: 2, pageSize: 100, search: "doc", sourceTypes: ["google_doc"], statuses: ["completed", "failed"] });

    expect(mockedAdminApi).toHaveBeenCalledWith("/import-jobs?page=2&page_size=100&search=doc&status=completed&status=failed&source_type=google_doc");
  });

  it("builds import item list requests with optional numeric filters", () => {
    fetchImportItems({ importJobId: "42", page: 2, pageSize: 100, search: "word", statuses: ["pending"], userId: "99" });
    fetchImportItems({ importJobId: "", page: 1, pageSize: 50, search: "", statuses: [], userId: "" });

    expect(mockedAdminApi).toHaveBeenNthCalledWith(1, "/import-items?page=2&page_size=100&search=word&status=pending&import_job_id=42&user_id=99");
    expect(mockedAdminApi).toHaveBeenNthCalledWith(2, "/import-items?page=1&page_size=50&search=");
  });

  it("calls metadata, detail, and nested item endpoints", () => {
    fetchImportJobFilters();
    fetchImportItemFilters();
    fetchImportJobDetail(42);
    fetchImportJobItems({ importJobId: 42, page: 3, pageSize: 50, statuses: ["imported"] });

    expect(mockedAdminApi).toHaveBeenNthCalledWith(1, "/import_jobs/filter-metadata");
    expect(mockedAdminApi).toHaveBeenNthCalledWith(2, "/import_items/filter-metadata");
    expect(mockedAdminApi).toHaveBeenNthCalledWith(3, "/import-jobs/42");
    expect(mockedAdminApi).toHaveBeenNthCalledWith(4, "/import-items?page=3&page_size=50&import_job_id=42&status=imported");
  });

  it("creates stable query keys", () => {
    const jobParams = { page: 1, pageSize: 50, search: "", sourceTypes: [], statuses: [] };
    const itemParams = { importJobId: "", page: 1, pageSize: 50, search: "", statuses: [], userId: "" };
    const jobItemsParams = { importJobId: 42, page: 1, pageSize: 50, statuses: ["imported"] };

    expect(importsQueryKeys.jobFilters()).toEqual(["imports", "jobs", "filter-metadata"]);
    expect(importsQueryKeys.jobList(jobParams)).toEqual(["imports", "jobs", "list", jobParams]);
    expect(importsQueryKeys.jobDetail(42)).toEqual(["imports", "jobs", "detail", "42"]);
    expect(importsQueryKeys.jobDetail(null)).toEqual(["imports", "jobs", "detail", ""]);
    expect(importsQueryKeys.jobItems(jobItemsParams)).toEqual(["imports", "jobs", "items", jobItemsParams]);
    expect(importsQueryKeys.itemFilters()).toEqual(["imports", "items", "filter-metadata"]);
    expect(importsQueryKeys.itemList(itemParams)).toEqual(["imports", "items", "list", itemParams]);
  });
});
