import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Placeholder } from "./Placeholder";

describe("Placeholder", () => {
  it("renders the requested title", () => {
    render(<Placeholder title="Settings" description="Ready for the next admin slice." />);

    expect(screen.getByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByText("Ready for the next admin slice.")).toBeInTheDocument();
  });
});
