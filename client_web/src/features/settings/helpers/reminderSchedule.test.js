import { describe, expect, it } from "vitest";

import {
  exceedsWeekdayLimit,
  hasDuplicateReminderTime,
  hasRemainingWeekdayCapacity,
  rowsToRules,
  rulesToRows,
} from "./reminderSchedule";

const t = (key, params) => {
  if (key === "reminderMorningTitle") return "Morning";
  if (key === "reminderDayTitle") return "Day";
  if (key === "reminderEveningTitle") return "Evening";
  return params ? `${key}:${JSON.stringify(params)}` : key;
};

describe("reminder schedule helpers", () => {
  it("preserves half-hour time and title between rows and rules", () => {
    const rules = rowsToRules([
      { title: "Evening", weekday: 1, hour: 20, minute: 30, status: "enabled" },
      { title: "Evening", weekday: 3, hour: 20, minute: 30, status: "enabled" },
    ], t);

    expect(rules).toEqual([
      { id: "enabled:20:30:Evening", title: "Evening", weekdays: [1, 3], hour: 20, minute: 30, status: "enabled" },
    ]);
    expect(rulesToRows(rules)).toEqual([
      { title: "Evening", weekday: 1, hour: 20, minute: 30, status: "enabled" },
      { title: "Evening", weekday: 3, hour: 20, minute: 30, status: "enabled" },
    ]);
  });

  it("rejects duplicate weekday and time before sending the payload", () => {
    const rules = [{ title: "Morning", weekdays: [0], hour: 9, minute: 0, status: "enabled" }];

    expect(hasDuplicateReminderTime(rules, { weekdays: [0], hour: 9, minute: 0 })).toBe(true);
    expect(hasDuplicateReminderTime(rules, { weekdays: [0], hour: 9, minute: 30 })).toBe(false);
  });

  it("enforces the enabled reminder limit per weekday", () => {
    const rules = [{ title: "Morning", weekdays: [0], hour: 9, minute: 0, status: "enabled" }];

    expect(exceedsWeekdayLimit(rules, { weekdays: [0], hour: 20, minute: 30, status: "enabled" }, 1)).toBe(true);
    expect(exceedsWeekdayLimit(rules, { weekdays: [0], hour: 20, minute: 30, status: "disabled" }, 1)).toBe(false);
  });

  it("detects whether any weekday can still receive an active reminder", () => {
    const fullRules = [
      { title: "Morning", weekdays: [0, 1, 2, 3, 4, 5, 6], hour: 9, minute: 0, status: "enabled" },
    ];

    expect(hasRemainingWeekdayCapacity(fullRules, 1)).toBe(false);
    expect(hasRemainingWeekdayCapacity(fullRules, 2)).toBe(true);
    expect(hasRemainingWeekdayCapacity([{ ...fullRules[0], status: "disabled" }], 1)).toBe(true);
  });
});
