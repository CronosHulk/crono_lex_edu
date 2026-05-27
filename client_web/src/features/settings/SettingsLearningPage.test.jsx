import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SettingsLearningPage } from "./SettingsLearningPage";

const saveMutate = vi.fn();
let settingsResult;
let saveResult;

vi.mock("./api/settingsApi", () => ({
  useSettings: () => settingsResult,
  useSaveSettings: () => saveResult,
}));

describe("SettingsLearningPage", () => {
  beforeEach(() => {
    saveMutate.mockReset();
    settingsResult = {
      data: {
        profile: { language_level_title: "A2", words_per_session: 15 },
        levels: ["A1", "A2", "B1"],
        words_per_session_options: [5, 10, 15, 20],
      },
      isPending: false,
      isError: false,
    };
    saveResult = {
      mutate: saveMutate,
      isPending: false,
      isSuccess: false,
      isError: false,
    };
  });

  it("renders learning settings and saves current selection", () => {
    render(<SettingsLearningPage />);

    expect(screen.getByRole("heading", { name: "Налаштування навчання" })).toBeInTheDocument();
    expect(screen.getByLabelText("Рівень слів")).toHaveTextContent("A2");
    expect(screen.getByLabelText("Слів у тренуванні")).toHaveTextContent("15");

    fireEvent.click(screen.getByRole("button", { name: "Зберегти зміни" }));

    expect(saveMutate).toHaveBeenCalledWith({
      language_level: "A2",
      words_per_session: 15,
    });
  });
});
