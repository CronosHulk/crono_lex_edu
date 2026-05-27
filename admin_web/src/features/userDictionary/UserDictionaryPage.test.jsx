import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { UserDictionaryPage } from "./UserDictionaryPage";
import {
  bulkActionUserDictionaryEntries,
  fetchUserDictionaryEntries,
  fetchUserDictionaryFilterMetadata,
} from "./api/userDictionaryApi";

vi.mock("./api/userDictionaryApi", () => ({
  bulkActionUserDictionaryEntries: vi.fn(),
  fetchUserDictionaryEntries: vi.fn(),
  fetchUserDictionaryFilterMetadata: vi.fn(),
  userDictionaryQueryKeys: {
    all: ["userDictionary"],
    filterMetadata: () => ["userDictionary", "filter-metadata"],
    list: (params) => ["userDictionary", "list", params],
  },
}));

const mockedFetchEntries = vi.mocked(fetchUserDictionaryEntries);
const mockedFetchFilters = vi.mocked(fetchUserDictionaryFilterMetadata);
const mockedBulkAction = vi.mocked(bulkActionUserDictionaryEntries);

const t = {
  assignments: "Assignments",
  audio: "Audio",
  created: "Created",
  dictionary: "Dictionary",
  emptyLogs: "No rows",
  examples: "Examples",
  level: "Level",
  loading: "Loading",
  loadError: "Load error",
  missingAudio: "Missing audio",
  partOfSpeech: "Part of speech",
  promoteToBase: "Promote to base",
  rejectUserWords: "Reject",
  bulkAction: "Bulk action",
  execute: "Execute",
  rebuildDetails: "Rebuild details",
  rebuildEmbedding: "Rebuild embedding",
  search: "Search",
  status: "Status",
  translations: "Translations",
  userDictionary: "User words",
  word: "Word",
  showDetails: "Details",
};

describe("UserDictionaryPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedFetchFilters.mockResolvedValue({ filters: [] });
    mockedFetchEntries.mockResolvedValue({
      items: [
        {
          id: 5,
          word: "cord",
          status: "ready_for_rotation",
          part_of_speech: "noun",
          level_title: "A1",
          translation_uk: "шнур",
          examples_json: ["Pull the cord."],
          assignment_count: 3,
          audio_url: "/audio/cord.mp3",
        },
        {
          id: 6,
          word: "spark",
          status: "details_failed",
          part_of_speech: "noun",
          failure_reason: "details provider bad response/schema error: lookup_word: gap builder could not blank usage form",
          assignment_count: 1,
        },
        {
          id: 7,
          word: "glow",
          status: "embedding_failed",
          part_of_speech: "noun",
          translation_uk: "сяйво",
          examples_json: ["The glow faded."],
          is_embedding_ready: false,
          assignment_count: 1,
        },
      ],
      total: 3,
    });
    mockedBulkAction.mockResolvedValue({ updated_count: 1 });
  });

  it("renders a selectable table and executes selected bulk action", async () => {
    renderPage();

    expect(await screen.findByText("Assignments")).toBeInTheDocument();
    const readyRow = (await screen.findByText("cord")).closest("tr");
    expect(readyRow).not.toBeNull();
    expect(within(readyRow).getByText("3")).toBeInTheDocument();
    const executeButton = screen.getByText("Execute").closest("button");
    expect(executeButton).toBeDisabled();

    const readyCheckbox = readyRow.querySelector('input[type="checkbox"]');
    const failedRow = screen.getByText("spark").closest("tr");
    const disabledCheckbox = failedRow.querySelector('input[type="checkbox"]');
    fireEvent.click(readyCheckbox);
    expect(disabledCheckbox).toBeDisabled();
    fireEvent.click(screen.getByText("Execute (1)").closest("button"));

    await waitFor(() => {
      expect(mockedBulkAction.mock.calls[0]?.[0]).toEqual({ action: "promote_to_base", entryIds: [5] });
    });
  });

  it("switches selectable rows by selected rebuild action", async () => {
    const user = userEvent.setup();

    renderPage();

    await screen.findByText("cord");
    await user.click(screen.getByRole("combobox", { name: "Bulk action" }));
    await user.click(screen.getByRole("option", { name: "Rebuild details" }));
    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes[1]).toBeDisabled();
    expect(checkboxes[2]).not.toBeDisabled();
    await user.click(checkboxes[2]);
    await user.click(screen.getByRole("button", { name: /Execute \(1\)/ }));

    await waitFor(() => {
      expect(mockedBulkAction.mock.calls[0]?.[0]).toEqual({ action: "rebuild_details", entryIds: [6] });
    });
  });

  it("executes reject bulk action for non-promoted user words", async () => {
    const user = userEvent.setup();

    renderPage();

    await screen.findByText("cord");
    await user.click(screen.getByRole("combobox", { name: "Bulk action" }));
    await user.click(screen.getByRole("option", { name: "Reject" }));
    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes[1]).not.toBeDisabled();
    expect(checkboxes[2]).not.toBeDisabled();
    await user.click(checkboxes[2]);
    await user.click(screen.getByRole("button", { name: /Execute \(1\)/ }));

    await waitFor(() => {
      expect(mockedBulkAction.mock.calls[0]?.[0]).toEqual({ action: "reject", entryIds: [6] });
    });
  });

  it("opens entry details from an icon-only trailing action", async () => {
    const user = userEvent.setup();
    const onOpenEntry = vi.fn();

    renderPage({ onOpenEntry });

    const readyRow = (await screen.findByText("cord")).closest("tr");
    expect(readyRow).not.toBeNull();
    expect(within(readyRow).queryByText("Details")).not.toBeInTheDocument();

    await user.click(within(readyRow).getByRole("button", { name: "Details" }));

    expect(onOpenEntry).toHaveBeenCalledWith(5);
  });

  it("renders long failure reasons as compact row summaries", async () => {
    renderPage();

    const failedRow = (await screen.findByText("spark")).closest("tr");
    expect(failedRow).not.toBeNull();
    expect(within(failedRow).getByText("details provider bad response")).toBeInTheDocument();
    expect(within(failedRow).queryByText(/lookup_word: gap builder/)).not.toBeInTheDocument();
  });
});

function renderPage(props = {}) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <UserDictionaryPage t={t} {...props} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
