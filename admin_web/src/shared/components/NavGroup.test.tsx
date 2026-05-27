import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { NavGroup } from "./NavGroup";

describe("NavGroup", () => {
  function renderNavGroup(element: ReactElement) {
    return render(<MemoryRouter>{element}</MemoryRouter>);
  }

  it("renders children when expanded", () => {
    renderNavGroup(
      <NavGroup icon={<span />} label="Logs" collapsed={false} to="/admin/task-logs">
        <button>Task Logs</button>
      </NavGroup>
    );

    expect(screen.getByRole("link", { name: "Logs" })).toHaveAttribute("href", "/admin/task-logs");
    expect(screen.getByRole("button", { name: "Task Logs" })).toBeInTheDocument();
  });

  it("hides children and keeps title when collapsed", () => {
    renderNavGroup(
      <NavGroup icon={<span />} label="Logs" collapsed to="/admin/task-logs">
        <button>Task Logs</button>
      </NavGroup>
    );

    expect(screen.getByTitle("Logs")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Task Logs" })).not.toBeInTheDocument();
  });
});
