import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LearningPage } from "./LearningPage";

const startMutate = vi.fn();
const resumeMutate = vi.fn();
const finishMutate = vi.fn();
const answerMutate = vi.fn();
const cardActionMutate = vi.fn();
const readyActionMutate = vi.fn();

let learningStateResult;

vi.mock("./api/learningApi", () => ({
  useLearningState: () => learningStateResult,
  useStartTraining: () => ({ mutate: startMutate, isPending: false }),
  useContinueTraining: () => ({ mutate: resumeMutate, isPending: false }),
  useFinishTraining: () => ({ mutate: finishMutate, isPending: false }),
  useAnswerTraining: () => ({ mutate: answerMutate, isPending: false }),
  useCardAction: () => ({ mutate: cardActionMutate }),
  useReadyAction: () => ({ mutate: readyActionMutate, isPending: false }),
}));

vi.mock("./components/LearningWordTable", () => ({
  LearningWordTable: () => <div data-testid="learning-word-table" />,
}));

vi.mock("../../shared/i18n/clientI18n", () => ({
  useClientI18n: () => ({
    t: (key) => ({
      navWordLearning: "Вивчення слів",
      tabTraining: "Тренування",
      tabLearning: "Вчу",
      tabLearned: "Вивчено",
      startTraining: "Почати тренування",
      resumeLesson: "Продовжити поточне заняття",
      telegramClaimed: "Готові почати або продовжити заняття?",
      cardIntro: "Знайомство зі словами",
      listenPronunciation: "Прослухати",
      listenWordPronunciation: "Прослухати слово",
      back: "Назад",
      forward: "Вперед",
      toExercises: "До вправ",
      alreadyKnow: "Вже знаю",
    }[key] || key),
  }),
}));

describe("LearningPage", () => {
  beforeEach(() => {
    startMutate.mockReset();
    resumeMutate.mockReset();
    finishMutate.mockReset();
    answerMutate.mockReset();
    cardActionMutate.mockReset();
    readyActionMutate.mockReset();
    learningStateResult = {
      data: {
        active_session: buildActiveSession(),
      },
      isPending: false,
      isError: false,
    };
  });

  it("asks to start or continue instead of opening the active exercise on page entry", () => {
    renderLearningPage();

    expect(screen.getByRole("button", { name: "Почати тренування" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Продовжити поточне заняття" })).toBeInTheDocument();
    expect(screen.queryByText("focus")).not.toBeInTheDocument();
  });

  it("opens the current exercise only after explicit continue", () => {
    resumeMutate.mockImplementation((_payload, options) => {
      options?.onSuccess?.({ active_session: buildActiveSession() });
    });

    renderLearningPage();
    fireEvent.click(screen.getByRole("button", { name: "Продовжити поточне заняття" }));

    expect(resumeMutate).toHaveBeenCalledTimes(1);
    expect(screen.getByText("focus")).toBeInTheDocument();
  });

  it("asks to start or continue when Telegram owns the active session", () => {
    learningStateResult = {
      data: {
        active_session: buildActiveSession({ isOwnedByWeb: false }),
      },
      isPending: false,
      isError: false,
    };

    renderLearningPage();

    expect(screen.getByText("Готові почати або продовжити заняття?")).toBeInTheDocument();
    expect(screen.queryByText("Заняття перехоплено в Telegram.")).not.toBeInTheDocument();
  });
});

function renderLearningPage() {
  return render(
    <MemoryRouter initialEntries={["/learning?tab=training"]}>
      <LearningPage />
    </MemoryRouter>,
  );
}

function buildActiveSession({ isOwnedByWeb = true } = {}) {
  return {
    id: 77,
    status: "active",
    current_stage: "card",
    stage_position: 0,
    active_interface: "client_web",
    is_owned_by_web: isOwnedByWeb,
    exercise: {
      type: "card",
      session_word_id: 501,
      word: "focus",
      translation: "фокус",
      translation_uk: "фокус",
      transcription: "/focus/",
      examples: [],
      categories: [],
      position: 1,
      total: 10,
      progress_bar: "●○○",
      can_go_back: false,
      can_go_forward: true,
      next_action: "next",
    },
  };
}
