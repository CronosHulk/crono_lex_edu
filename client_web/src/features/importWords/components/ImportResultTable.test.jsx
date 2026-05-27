import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { createTranslator } from "@cronolex/shared/i18n/projectI18n";

import { ImportResultTable } from "./ImportResultTable";

const defaultProps = {
  t: createTranslator("client", "uk"),
  rows: [
    {
      id: 1,
      word: "leisure",
      raw_value: "leisure [лижеp:]",
      validated_word: "leisure",
      validated_part_of_speech: "noun",
      validated_translation_uk: "дозвілля",
      status_category: "added",
      status_label: "Успішно додано",
    },
  ],
  total: 1,
  page: 1,
  pageSize: 50,
  loading: false,
  summary: { added: 1, queued: 0, rejected: 0, processing: 0 },
  statusCategory: "all",
  showSummary: true,
  resolvingIds: new Set(),
  newRowIds: new Set(),
  onPageChange: vi.fn(),
  onPageSizeChange: vi.fn(),
  onStatusCategoryChange: vi.fn(),
};

describe("ImportResultTable", () => {
  it("renders the client translation for part of speech", () => {
    render(<ImportResultTable {...defaultProps} />);

    expect(screen.getByRole("columnheader", { name: "Частина мови" })).toBeInTheDocument();
    expect(screen.queryByText("partOfSpeech")).not.toBeInTheDocument();
  });

  it("truncates rejected word text and shows the escaped full text on hover", async () => {
    const user = userEvent.setup();
    const rejectedText = "Знак оклику - як exclamation mark <script>alert(1)</script>";
    const { container } = render(
      <ImportResultTable
        {...defaultProps}
        rows={[
          {
            id: 2,
            word: rejectedText,
            validated_word: "",
            validated_part_of_speech: "",
            validated_translation_uk: "",
            status_category: "rejected",
            status_label: "Відхилено",
          },
        ]}
        summary={{ added: 0, queued: 0, rejected: 1, processing: 0 }}
      />,
    );

    const preview = screen.getByText("Знак оклику - як exclamation m...");
    expect(screen.queryByText(rejectedText)).not.toBeInTheDocument();
    expect(container.querySelector("script")).toBeNull();

    await user.hover(preview);

    expect(await screen.findByRole("tooltip")).toHaveTextContent(rejectedText);
    expect(container.querySelector("script")).toBeNull();
  });
});
