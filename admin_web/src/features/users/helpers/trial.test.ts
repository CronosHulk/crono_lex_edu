import { describe, expect, it } from "vitest";

import { isTrialActive } from "./trial";

describe("trial helpers", () => {
  const now = new Date("2026-05-05T12:00:00.000Z");

  it("treats future trial end as active", () => {
    expect(isTrialActive({ trial_end: "2026-05-06T12:00:00.000Z" }, now)).toBe(true);
  });

  it("treats expired or missing trial end as inactive", () => {
    expect(isTrialActive({ trial_end: "2026-05-04T12:00:00.000Z" }, now)).toBe(false);
    expect(isTrialActive({ trial_end: null }, now)).toBe(false);
    expect(isTrialActive({}, now)).toBe(false);
    expect(isTrialActive({ trial_end: "not-a-date" }, now)).toBe(false);
  });
});
