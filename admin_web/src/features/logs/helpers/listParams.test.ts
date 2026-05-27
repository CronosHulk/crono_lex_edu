import { describe, expect, it } from "vitest";

import {
  applyErrorLogsParamUpdates,
  applyTaskLogsParamUpdates,
  errorLogsParamsFromSearch,
  taskLogsParamsFromSearch,
} from "./listParams";

describe("taskLogsParamsFromSearch", () => {
  it("reads defaults and explicit task log params", () => {
    expect(taskLogsParamsFromSearch(new URLSearchParams())).toEqual({
      page: 1,
      pageSize: 50,
      search: "",
      statuses: [],
      taskTypes: [],
    });

    expect(taskLogsParamsFromSearch(new URLSearchParams("page=2&page_size=100&search=sync&status=done&task_type=import"))).toEqual({
      page: 2,
      pageSize: 100,
      search: "sync",
      statuses: ["done"],
      taskTypes: ["import"],
    });
  });
});

describe("errorLogsParamsFromSearch", () => {
  it("reads defaults and explicit error log params", () => {
    expect(errorLogsParamsFromSearch(new URLSearchParams())).toEqual({
      levels: [],
      page: 1,
      pageSize: 50,
      search: "",
    });

    expect(errorLogsParamsFromSearch(new URLSearchParams("page=2&page_size=100&search=boom&level=warn&level=fatal"))).toEqual({
      levels: ["warn", "fatal"],
      page: 2,
      pageSize: 100,
      search: "boom",
    });
  });
});

describe("applyTaskLogsParamUpdates", () => {
  it("writes, preserves, and clears task log params", () => {
    const written = applyTaskLogsParamUpdates(new URLSearchParams(), {
      page: 2,
      pageSize: 100,
      search: "sync",
      statuses: ["done"],
      taskTypes: ["import"],
    });
    expect(written.toString()).toBe("page=2&page_size=100&search=sync&status=done&task_type=import");

    expect(applyTaskLogsParamUpdates(written, { search: "audio" }).toString()).toBe("page=2&page_size=100&search=audio&status=done&task_type=import");
    expect(applyTaskLogsParamUpdates(written, { statuses: ["failed"] }).toString()).toBe("page=2&page_size=100&search=sync&task_type=import&status=failed");
    expect(applyTaskLogsParamUpdates(written, { page: 1, pageSize: 50, search: "", statuses: undefined, taskTypes: [] }).toString()).toBe("");
  });
});

describe("applyErrorLogsParamUpdates", () => {
  it("writes, preserves, and clears error log params", () => {
    const written = applyErrorLogsParamUpdates(new URLSearchParams(), {
      levels: ["warn", "fatal"],
      page: 2,
      pageSize: 100,
      search: "boom",
    });
    expect(written.toString()).toBe("page=2&page_size=100&search=boom&level=warn&level=fatal");

    expect(applyErrorLogsParamUpdates(written, { search: "other" }).toString()).toBe("page=2&page_size=100&search=other&level=warn&level=fatal");
    expect(applyErrorLogsParamUpdates(written, { levels: ["debug"] }).toString()).toBe("page=2&page_size=100&search=boom&level=debug");
    expect(applyErrorLogsParamUpdates(written, { levels: undefined, page: 1, pageSize: 50, search: "" }).toString()).toBe("");
  });
});
