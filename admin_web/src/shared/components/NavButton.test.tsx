import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { NavButton } from "./NavButton";

describe("NavButton", () => {
  function renderNavButton(element: ReactElement) {
    return render(<MemoryRouter>{element}</MemoryRouter>);
  }

  it("renders active expanded navigation button", async () => {
    const user = userEvent.setup();

    renderNavButton(<NavButton icon={<span data-testid="icon" />} label="Users" active collapsed={false} to="/admin/users" />);

    const link = screen.getByRole("link", { name: "Users" });

    expect(link).toHaveClass("nav", "active");
    expect(link).toHaveAttribute("href", "/admin/users");
    expect(screen.getByTestId("icon")).toBeInTheDocument();

    await user.click(link);

    expect(link).toHaveAttribute("href", "/admin/users");
  });

  it("uses title and hides label when collapsed", () => {
    renderNavButton(<NavButton icon={<span data-testid="icon" />} label="Logs" active={false} collapsed to="/admin/task-logs" />);

    expect(screen.getByTitle("Logs")).toHaveClass("nav");
    expect(screen.queryByText("Logs")).not.toBeInTheDocument();
  });
});
