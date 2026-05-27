import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ArchiveTabs } from "./ArchiveTabs";

describe("ArchiveTabs", () => {
  it("renders MUI tabs and reports the selected archive filter", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(<ArchiveTabs labels={{ all: "Усі", archived: "Архів" }} value="all" onChange={onChange} />);

    expect(screen.getByRole("tab", { name: "Усі" })).toHaveAttribute("aria-selected", "true");

    await user.click(screen.getByRole("tab", { name: "Архів" }));

    expect(onChange).toHaveBeenCalledWith("archived");
  });
});
