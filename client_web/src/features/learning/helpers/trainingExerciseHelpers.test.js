import { describe, expect, it } from "vitest";

import { parseProgressRows, progressSymbolLabel } from "./trainingExerciseHelpers";

describe("trainingExerciseHelpers", () => {
  it("keeps multiline progress bar rows and centered padding slots", () => {
    const rows = parseProgressRows(
      "[✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓]\n[⋯⋯⋯⋯⋯●○○○○○○○○○⋯⋯⋯⋯⋯]",
    );

    expect(rows).toEqual([
      Array.from({ length: 20 }, () => "✓"),
      [
        "⋯",
        "⋯",
        "⋯",
        "⋯",
        "⋯",
        "●",
        "○",
        "○",
        "○",
        "○",
        "○",
        "○",
        "○",
        "○",
        "○",
        "⋯",
        "⋯",
        "⋯",
        "⋯",
        "⋯",
      ],
    ]);
    expect(progressSymbolLabel("⋯")).toBe("\u00A0");
  });
});
