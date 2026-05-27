import { describe, expect, it } from "vitest";

import { DEFAULT_IMPORT_SETTINGS, weekdaysForPreset, weekdayPresetValue } from "./ImportSettingsSection";

describe("ImportSettingsSection weekday presets", () => {
  it("preserves legacy interval fallback when weekdays are not set", () => {
    expect(weekdayPresetValue(null)).toBe("legacy_interval");
    expect(weekdaysForPreset("legacy_interval")).toBeNull();
  });

  it("maps supported weekday presets without changing order", () => {
    expect(weekdayPresetValue([0, 2, 4])).toBe("mon_wed_fri");
    expect(weekdaysForPreset("every_day")).toEqual([0, 1, 2, 3, 4, 5, 6]);
  });

  it("defaults scheduler and details weekdays for persisted import settings", () => {
    expect(DEFAULT_IMPORT_SETTINGS.attribute_build_weekdays).toBeNull();
    expect(DEFAULT_IMPORT_SETTINGS.audio_build_hour).toBe(2);
    expect(DEFAULT_IMPORT_SETTINGS.audio_build_weekdays).toBeNull();
    expect(DEFAULT_IMPORT_SETTINGS.google_doc_sync_hour).toBe(0);
    expect(DEFAULT_IMPORT_SETTINGS.scheduler_tick_minutes).toBe(10);
  });
});
