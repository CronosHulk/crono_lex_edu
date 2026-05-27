import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LearningWordTable } from "./LearningWordTable";

const priorityMutation = {
  isPending: false,
  mutate: vi.fn(),
};
const apiMocks = vi.hoisted(() => ({
  useLearningWords: vi.fn(),
}));

const learningRows = Array.from({ length: 11 }, (_item, index) => ({
  id: index + 1,
  word_source: "user",
  word_id: 88 + index,
  word: index === 0 ? "storage" : `word-${index + 1}`,
  topic: index === 0 ? "Побут, ІТ" : "Спілкування",
  topic_codes: index === 0 ? ["household", "it"] : ["communication"],
  level: "B1",
  translation: index === 0 ? "зберігання, склад" : `переклад-${index + 1}`,
  status: "В процесі",
}));

vi.mock("../api/learningApi", () => ({
  useLearningWordFilters: vi.fn(() => ({ data: { topics: [] }, isError: false, isLoading: false })),
  useLearningWords: apiMocks.useLearningWords,
  usePrioritizeLearningWord: vi.fn(() => priorityMutation),
}));

function renderTable(ui, initialEntry = "/learning?tab=learning") {
  return render(<MemoryRouter initialEntries={[initialEntry]}>{ui}</MemoryRouter>);
}

describe("LearningWordTable", () => {
  beforeEach(() => {
    apiMocks.useLearningWords.mockReset();
    apiMocks.useLearningWords.mockReturnValue({
    data: {
      items: learningRows,
      total: learningRows.length,
    },
    isLoading: false,
    });
  });

  it("uses current rows as topic filter fallback when the reference option list is empty", () => {
    renderTable(<LearningWordTable mode="learning" />);

    fireEvent.mouseDown(screen.getAllByRole("combobox")[0]);

    const listbox = screen.getByRole("listbox");
    expect(within(listbox).getByText("Побут")).toBeInTheDocument();
    expect(within(listbox).getByText("ІТ")).toBeInTheDocument();
  });

  it("prioritizes the selected learning row", () => {
    priorityMutation.mutate.mockClear();

    renderTable(<LearningWordTable mode="learning" />);

    fireEvent.click(screen.getByRole("button", { name: /Підняти/i }));

    expect(priorityMutation.mutate).toHaveBeenCalledWith({ word_source: "user", word_id: 98 });
  });

  it("hides the prioritize button for the first ten learning rows", () => {
    renderTable(<LearningWordTable mode="learning" />);

    const bodyRows = screen.getAllByRole("row").slice(1);
    bodyRows.slice(0, 10).forEach((row) => {
      expect(within(row).queryByRole("button", { name: /Підняти/i })).not.toBeInTheDocument();
    });
    expect(within(bodyRows[10]).getByRole("button", { name: /Підняти/i })).toBeInTheDocument();
  });

  it("reads table controls from URL search params", () => {
    renderTable(
      <LearningWordTable mode="learning" />,
      "/learning?tab=learning&page=2&page_size=50&word=stor&topic=household&topic=it&level=B1",
    );

    expect(apiMocks.useLearningWords).toHaveBeenLastCalledWith({
      mode: "learning",
      page: 2,
      pageSize: 50,
      word: "stor",
      topic: ["household", "it"],
      level: "B1",
      enabled: true,
    });
  });
});
