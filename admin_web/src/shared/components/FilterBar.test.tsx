import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FilterBar } from "./FilterBar";

describe("FilterBar", () => {
  it("renders filter controls in one bar", () => {
    render(
      <FilterBar>
        <button type="button">Control</button>
      </FilterBar>
    );

    expect(screen.getByRole("button", { name: "Control" })).toBeInTheDocument();
  });
});
