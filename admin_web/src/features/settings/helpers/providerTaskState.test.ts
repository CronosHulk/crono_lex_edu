import { describe, expect, it } from "vitest";

import {
  isProviderTaskEnabled,
  providerTaskConfigFields,
  providerTaskConfigOptions,
  providerTaskEnabledLabel,
} from "./providerTaskState";

describe("providerTaskState", () => {
  it("uses the effective provider enabled state for labels", () => {
    const labels = { providerEnabled: "Увімкнено", providerDisabled: "Вимкнено" };

    expect(providerTaskEnabledLabel({ provider_key: "openai", is_enabled: true }, labels)).toBe("Увімкнено");
    expect(providerTaskEnabledLabel({ provider_key: "openai", is_enabled: false }, labels)).toBe("Вимкнено");
    expect(providerTaskEnabledLabel({ provider_key: "disabled", is_enabled: true }, labels)).toBe("Вимкнено");
  });

  it("treats disabled provider keys as disabled even if legacy data says enabled", () => {
    expect(isProviderTaskEnabled({ provider_key: "disabled", is_enabled: true })).toBe(false);
  });

  it("falls back to English labels when translations are missing", () => {
    expect(providerTaskEnabledLabel({ provider_key: "openai", is_enabled: true }, {})).toBe("Enabled");
    expect(providerTaskEnabledLabel({ provider_key: "openai", is_enabled: false }, {})).toBe("Disabled");
  });

  it("builds config fields from provider options and current config", () => {
    const task = {
      provider_key: "openai",
      config: { api_url: "https://api.example.test/responses" },
      config_options_by_provider: { openai: { model: ["gpt-5.4-mini"] } },
    };

    expect(providerTaskConfigFields(task)).toEqual(["model", "api_url"]);
    expect(providerTaskConfigOptions(task, "model")).toEqual(["gpt-5.4-mini"]);
  });

  it("hides config fields for disabled providers", () => {
    expect(providerTaskConfigFields({ provider_key: "disabled", config: { model: "gpt-5.4-mini" } })).toEqual([]);
    expect(providerTaskConfigFields({ config: { model: "gpt-5.4-mini" } })).toEqual([]);
  });

  it("uses legacy config_options when provider-specific options are unavailable", () => {
    const task = {
      provider_key: "openai",
      config_options: { model: ["gpt-5.4"] },
    };

    expect(providerTaskConfigFields(task)).toEqual(["model"]);
    expect(providerTaskConfigOptions(task, "model")).toEqual(["gpt-5.4"]);
    expect(providerTaskConfigOptions({ provider_key: "openai" }, "model")).toEqual([]);
    expect(providerTaskConfigOptions({}, "model")).toEqual([]);
    expect(providerTaskConfigFields({ provider_key: "openai" })).toEqual([]);
  });
});
