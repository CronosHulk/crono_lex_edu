import { within, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MultiSelect, normalizeMultiSelectValue } from "./MultiSelect";

describe("normalizeMultiSelectValue", () => {
  it("keeps array values and splits string fallback values", () => {
    expect(normalizeMultiSelectValue(["noun", "verb"])).toEqual(["noun", "verb"]);
    expect(normalizeMultiSelectValue("noun,verb")).toEqual(["noun", "verb"]);
  });
});

describe("MultiSelect", () => {
  it("renders selected options and reports selected values", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(
      <MultiSelect
        label="Part of speech"
        options={[
          { value: "noun", label: "Noun" },
          { value: "verb", label: "Verb" }
        ]}
        value={["noun"]}
        onChange={onChange}
      />
    );

    const combobox = screen.getByRole("combobox");
    expect(within(combobox).getByText("Noun")).toBeInTheDocument();

    await user.click(combobox);
    await user.click(screen.getByRole("option", { name: "Verb" }));

    expect(onChange).toHaveBeenCalledWith(["noun", "verb"]);
  });

  it("renders empty and unknown selected values", () => {
    const { rerender } = render(
      <MultiSelect
        label="Part of speech"
        options={[{ value: "noun", label: "Noun" }]}
        value={[]}
        onChange={vi.fn()}
      />
    );

    expect(screen.getByRole("combobox", { name: "Part of speech" }).textContent?.replace(/\u200b/g, "")).toBe("");

    rerender(
      <MultiSelect
        label="Part of speech"
        options={[{ value: "noun", label: "Noun" }]}
        value={["custom"]}
        onChange={vi.fn()}
      />
    );

    expect(screen.getByRole("combobox")).toHaveTextContent("custom");
  });
});
