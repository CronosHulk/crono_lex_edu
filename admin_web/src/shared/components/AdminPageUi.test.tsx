import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import {
  ActionRow,
  ChipRow,
  CrudEditPage,
  CrudFormSurface,
  CrudPage,
  CrudTableSurface,
  DetailGrid,
  InlineDetailBlock,
  InlineDetailGrid,
  DetailPanel,
  EmptyState,
  LinkButton,
  ListCard,
  LoadingLine,
  PreLine,
  SideMeta,
  TitleRow,
} from ".";

describe("AdminPageUi", () => {
  it("renders shared page layout primitives", () => {
    render(
      <>
        <ListCard>
          <TitleRow label="ID-1" title="Import item" trailing="draft" />
          <SideMeta>
            <ChipRow>
              <span>one</span>
            </ChipRow>
          </SideMeta>
        </ListCard>
        <DetailGrid>
          <DetailPanel title="Details">
            <ActionRow>
              <span>Approve</span>
            </ActionRow>
          </DetailPanel>
        </DetailGrid>
        <InlineDetailGrid>
          <InlineDetailBlock title="Context">
            <span>Task #1</span>
          </InlineDetailBlock>
        </InlineDetailGrid>
        <PreLine>{"line 1\nline 2"}</PreLine>
        <EmptyState text="No rows" />
        <LoadingLine text="Loading rows" />
      </>
    );

    expect(screen.getByText("ID-1")).toBeInTheDocument();
    expect(screen.getByText("Import item")).toBeInTheDocument();
    expect(screen.getByText("draft")).toBeInTheDocument();
    expect(screen.getByText("Details")).toBeInTheDocument();
    expect(screen.getByText("Approve")).toBeInTheDocument();
    expect(screen.getByText("Context")).toBeInTheDocument();
    expect(screen.getByText("Task #1")).toBeInTheDocument();
    expect(screen.getByText(/line 1/)).toHaveTextContent("line 1 line 2");
    expect(screen.getByText("No rows")).toBeInTheDocument();
    expect(screen.getByText("Loading rows")).toBeInTheDocument();
  });

  it("renders CRUD page primitives without stretching content height", () => {
    render(
      <MemoryRouter>
        <CrudPage
          title="Dictionary"
          breadcrumbs={[
            { title: "Admin", path: "/admin" },
            { title: "Dictionary" },
          ]}
          actions={<button type="button">Create</button>}
        >
          <CrudTableSurface>
            <table>
              <tbody>
                <tr>
                  <td>run</td>
                </tr>
              </tbody>
            </table>
          </CrudTableSurface>
          <CrudFormSurface sx={[{ maxWidth: 480 }]}>
            <label htmlFor="word">Word</label>
            <input id="word" />
          </CrudFormSurface>
          <CrudFormSurface sx={{ maxWidth: 360 }}>
            <span>compact form</span>
          </CrudFormSurface>
          <CrudTableSurface sx={[{ maxWidth: 640 }]}>
            <span>extra table</span>
          </CrudTableSurface>
        </CrudPage>
        <CrudEditPage
          title="Edit word"
          breadcrumbs={[
            { title: "Dictionary", path: "/admin" },
            { title: "run" },
          ]}
          actions={<button type="button">Back</button>}
        >
          <CrudFormSurface>
            <span>Edit form</span>
          </CrudFormSurface>
        </CrudEditPage>
      </MemoryRouter>
    );

    expect(screen.getByRole("heading", { name: "Dictionary" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Edit word" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Admin" })).toHaveAttribute("href", "/admin");
    expect(screen.getByRole("link", { name: "Dictionary" })).toHaveAttribute("href", "/admin");
    expect(screen.getByRole("button", { name: "Create" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Back" })).toBeInTheDocument();
    expect(screen.getAllByText("run")).toHaveLength(2);
    expect(screen.getByText("Edit form")).toBeInTheDocument();
    expect(screen.getByText("extra table")).toBeInTheDocument();
    expect(screen.getByText("compact form")).toBeInTheDocument();
    expect(screen.getByLabelText("Word")).toBeInTheDocument();
  });

  it("renders fallbacks for optional display values", () => {
    render(
      <>
        <TitleRow />
        <PreLine>{null}</PreLine>
      </>
    );

    expect(screen.getAllByText("-")).toHaveLength(3);
  });

  it("reports link navigation actions", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();

    render(
      <LinkButton onClick={onOpen}>Open entity</LinkButton>
    );

    await user.click(screen.getByRole("button", { name: /Open entity/ }));

    expect(onOpen).toHaveBeenCalledTimes(1);
  });
});
