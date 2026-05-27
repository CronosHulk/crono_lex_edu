import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useLiveImportRows } from "./useLiveImportRows";

describe("useLiveImportRows", () => {
  it("renders the latest visible rows immediately without staged animation", () => {
    const initialRows = [
      row(1, "first"),
      row(2, "second"),
    ];
    const { result, rerender } = renderHook(
      ({ sourceRows }) =>
        useLiveImportRows({
          sourceRows,
          jobKey: "job:1",
          viewKey: "job:1:1:20:all",
          pageSize: 20,
          isPlaceholderData: false,
        }),
      { initialProps: { sourceRows: initialRows } },
    );

    expect(result.current.rows.map((item) => item.word)).toEqual(["first", "second"]);
    expect(result.current.newRowIds.size).toBe(0);
    expect(result.current.resolvingIds.size).toBe(0);

    rerender({ sourceRows: [...initialRows, row(3, "third")] });

    expect(result.current.rows.map((item) => item.word)).toEqual(["first", "second", "third"]);
    expect(result.current.newRowIds.size).toBe(0);
    expect(result.current.resolvingIds.size).toBe(0);

    rerender({ sourceRows: [...initialRows, row(3, "third"), row(4, "fourth")] });

    expect(result.current.rows.map((item) => item.word)).toEqual(["first", "second", "third", "fourth"]);
    expect(result.current.newRowIds.size).toBe(0);
    expect(result.current.resolvingIds.size).toBe(0);
  });

  it("does not animate the first real rows after a tab or pagination transition", () => {
    const firstPageRows = [row(1, "first"), row(2, "second")];
    const secondPageRows = [row(21, "twenty first"), row(22, "twenty second")];
    const { result, rerender } = renderHook(
      ({ sourceRows, viewKey, isPlaceholderData }) =>
        useLiveImportRows({
          sourceRows,
          jobKey: "job:1",
          viewKey,
          pageSize: 20,
          isPlaceholderData,
        }),
      {
        initialProps: {
          sourceRows: firstPageRows,
          viewKey: "job:1:1:20:all",
          isPlaceholderData: false,
        },
      },
    );

    expect(result.current.rows.map((item) => item.word)).toEqual(["first", "second"]);

    rerender({
      sourceRows: firstPageRows,
      viewKey: "job:1:2:20:all",
      isPlaceholderData: true,
    });

    expect(result.current.rows.map((item) => item.word)).toEqual(["first", "second"]);
    expect(result.current.newRowIds.size).toBe(0);
    expect(result.current.resolvingIds.size).toBe(0);

    rerender({
      sourceRows: secondPageRows,
      viewKey: "job:1:2:20:all",
      isPlaceholderData: false,
    });

    expect(result.current.rows.map((item) => item.word)).toEqual(["twenty first", "twenty second"]);
    expect(result.current.newRowIds.size).toBe(0);
    expect(result.current.resolvingIds.size).toBe(0);
  });

  it("renders later live rows immediately after the real transition baseline is rendered", () => {
    const firstPageRows = [row(1, "first")];
    const secondPageRows = [row(21, "twenty first")];
    const { result, rerender } = renderHook(
      ({ sourceRows, viewKey, isPlaceholderData }) =>
        useLiveImportRows({
          sourceRows,
          jobKey: "job:1",
          viewKey,
          pageSize: 20,
          isPlaceholderData,
        }),
      {
        initialProps: {
          sourceRows: firstPageRows,
          viewKey: "job:1:1:20:all",
          isPlaceholderData: false,
        },
      },
    );

    rerender({
      sourceRows: firstPageRows,
      viewKey: "job:1:2:20:all",
      isPlaceholderData: true,
    });
    rerender({
      sourceRows: secondPageRows,
      viewKey: "job:1:2:20:all",
      isPlaceholderData: false,
    });
    rerender({
      sourceRows: [...secondPageRows, row(23, "twenty third")],
      viewKey: "job:1:2:20:all",
      isPlaceholderData: false,
    });

    expect(result.current.rows.map((item) => item.word)).toEqual(["twenty first", "twenty third"]);
    expect(result.current.newRowIds.size).toBe(0);
    expect(result.current.resolvingIds.size).toBe(0);
  });
});

function row(id, word) {
  return {
    id,
    word,
    status_category: "queued",
    status_label: "Queued",
  };
}
