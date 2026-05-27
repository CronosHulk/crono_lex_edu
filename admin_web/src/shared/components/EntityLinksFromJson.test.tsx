import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EntityLinksFromJson } from "./EntityLinksFromJson";

describe("EntityLinksFromJson", () => {
  it("does not render when extractor finds no safe entity links", () => {
    const { container } = render(
      <EntityLinksFromJson
        value={{ user_dictionary_entry_id: "../1", dictionary_entry_id: 0 }}
        user={{ acl_group_title: "super_admin" }}
        onOpenDictionaryEntry={vi.fn()}
      />
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("renders common entity controls and calls provided navigation callbacks", async () => {
    const user = userEvent.setup();
    const onOpenUser = vi.fn();
    const onOpenImportJob = vi.fn();
    const onOpenTaskLog = vi.fn();

    render(
      <EntityLinksFromJson
        value={{ user_id: "11111111-1111-4111-8111-111111111111", import_job_id: 5, task_log_id: 6 }}
        t={{ importJob: "Import" }}
        user={{ acl_group_title: "admin" }}
        onOpenUser={onOpenUser}
        onOpenImportJob={onOpenImportJob}
        onOpenTaskLog={onOpenTaskLog}
      />
    );

    const row = screen.getByText("User #11111111-1111-4111-8111-111111111111").closest(".link-row");
    expect(row).not.toBeNull();
    expect(within(row as HTMLElement).getAllByRole("button")).toHaveLength(3);

    await user.click(screen.getByRole("button", { name: /User #11111111-1111-4111-8111-111111111111/ }));
    await user.click(screen.getByRole("button", { name: /Import #5/ }));
    await user.click(screen.getByRole("button", { name: /Task #6/ }));

    expect(onOpenUser).toHaveBeenCalledWith("11111111-1111-4111-8111-111111111111");
    expect(onOpenImportJob).toHaveBeenCalledWith(5);
    expect(onOpenTaskLog).toHaveBeenCalledWith(6);
  });

  it("keeps user words and dictionary entries read-only for admins", () => {
    render(
      <EntityLinksFromJson
        value={{ user_dictionary_entry_id: 7, dictionary_entry_id: 8 }}
        user={{ acl_group_title: "admin" }}
        onOpenDictionaryEntry={vi.fn()}
      />
    );

    expect(screen.getByText("User word #7").closest(".chip")).not.toBeNull();
    expect(screen.getByText("Word #8").closest(".chip")).not.toBeNull();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("opens dictionary entries for super admins", async () => {
    const user = userEvent.setup();
    const onOpenDictionaryEntry = vi.fn();

    render(
      <EntityLinksFromJson
        value={{ user_dictionary_entry_id: 9, word_id: "10" }}
        user={{ acl_group_title: "super_admin" }}
        onOpenDictionaryEntry={onOpenDictionaryEntry}
      />
    );

    await user.click(screen.getByRole("button", { name: /Word #10/ }));

    expect(screen.getByText("User word #9").closest(".chip")).not.toBeNull();
    expect(onOpenDictionaryEntry).toHaveBeenCalledWith(10);
  });

  it("falls back to read-only chips when callbacks are not provided", () => {
    render(
      <EntityLinksFromJson
        value={{
          user_id: "11111111-1111-4111-8111-111111111111",
          import_job_id: 12,
          user_dictionary_entry_id: 13,
          dictionary_entry_id: 14
        }}
        user={{ acl_group_title: "super_admin" }}
      />
    );

    expect(screen.getByText("User #11111111-1111-4111-8111-111111111111").closest(".chip")).not.toBeNull();
    expect(screen.getByText("Import job #12").closest(".chip")).not.toBeNull();
    expect(screen.getByText("User word #13").closest(".chip")).not.toBeNull();
    expect(screen.getByText("Word #14").closest(".chip")).not.toBeNull();
  });

  it("keeps numeric entity links read-only when the extracted id is not numeric", () => {
    render(
      <EntityLinksFromJson
        value={{ import_job_id: "11111111-1111-4111-8111-111111111111" }}
        t={{ importJob: "Import" }}
        onOpenImportJob={vi.fn()}
      />
    );

    expect(screen.getByText("Import #11111111-1111-4111-8111-111111111111").closest(".chip")).not.toBeNull();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("uses read-only restricted controls when no current user is provided", () => {
    render(
      <EntityLinksFromJson
        value={{ user_dictionary_entry_id: 15, dictionary_entry_id: 16 }}
        onOpenDictionaryEntry={vi.fn()}
      />
    );

    expect(screen.getByText("User word #15").closest(".chip")).not.toBeNull();
    expect(screen.getByText("Word #16").closest(".chip")).not.toBeNull();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
