import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { LogToolbar } from "./LogToolbar";

describe("LogToolbar", () => {
  it("reports search changes", () => {
    const onSearch = vi.fn();

    render(<LogToolbar t={{ search: "Search" }} search="" onSearch={onSearch} />);

    fireEvent.change(screen.getByRole("textbox", { name: "Search" }), { target: { value: "error" } });

    expect(onSearch).toHaveBeenLastCalledWith("error");
  });

  it("renders search input without an icon adornment", () => {
    const { container } = render(<LogToolbar t={{ search: "Search" }} search="" onSearch={vi.fn()} />);

    expect(container.querySelector("svg")).toBeNull();
    expect(container.querySelector(".MuiInputAdornment-root")).toBeNull();
  });
});
