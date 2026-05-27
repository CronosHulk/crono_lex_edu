import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LogField } from "./LogField";

describe("LogField", () => {
  it("renders value and empty fallback", () => {
    const { rerender } = render(<LogField label="Status" value="done" />);

    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByText("done")).toBeInTheDocument();

    rerender(<LogField label="Status" value="" />);

    expect(screen.getByText("-")).toBeInTheDocument();

    rerender(<LogField label="Count" value={0} />);

    expect(screen.getByText("0")).toBeInTheDocument();
  });

  it("renders inline label and value for side metadata", () => {
    render(<LogField layout="inline" label="Рівень" value="fatal" />);

    expect(screen.getByText("Рівень:")).toBeInTheDocument();
    expect(screen.getByText("fatal")).toBeInTheDocument();
  });
});
