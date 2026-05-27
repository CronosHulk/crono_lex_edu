import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Pager } from "./Pager";

describe("Pager", () => {
  it("reports page changes through MUI table pagination", async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    const onPageSizeChange = vi.fn();

    render(<Pager page={1} pageSize={50} total={120} onPageChange={onPageChange} onPageSizeChange={onPageSizeChange} />);

    expect(screen.getByText("1-50 / 120")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /next page/i }));

    expect(onPageChange).toHaveBeenCalledWith(2);
    expect(onPageSizeChange).not.toHaveBeenCalled();
  });

  it("reports rows per page changes", async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    const onPageSizeChange = vi.fn();

    render(<Pager page={1} pageSize={50} total={120} onPageChange={onPageChange} onPageSizeChange={onPageSizeChange} />);

    await user.click(screen.getByRole("combobox", { name: /на сторінці/i }));
    await user.click(screen.getByRole("option", { name: "100" }));

    expect(onPageSizeChange).toHaveBeenCalledWith(100);
    expect(onPageChange).not.toHaveBeenCalled();
  });
});
