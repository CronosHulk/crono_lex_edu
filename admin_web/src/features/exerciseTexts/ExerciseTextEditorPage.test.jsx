import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ExerciseTextEditorPage } from "./ExerciseTextEditorPage";
import {
  confirmExerciseTextParagraphStage,
  createExerciseText,
  fetchExerciseText,
  fetchExerciseTextGenerationTask,
  fetchExerciseTextReference,
  fetchGrammarTopics,
  fetchTtsVoices,
  generateExerciseTextStage,
} from "./api/exerciseTextsApi";

vi.mock("./api/exerciseTextsApi", () => ({
  confirmExerciseTextParagraphStage: vi.fn(),
  createExerciseText: vi.fn(),
  exerciseTextsQueryKeys: {
    all: ["exerciseTexts"],
    reference: () => ["exerciseTexts", "reference"],
    grammarTopics: () => ["exerciseTexts", "grammar-topics"],
    ttsVoices: () => ["exerciseTexts", "tts-voices"],
    lists: () => ["exerciseTexts", "list"],
    detail: (id) => ["exerciseTexts", "detail", Number(id)],
    generationTask: (id, taskId) => ["exerciseTexts", "detail", Number(id), "generation-task", Number(taskId)],
  },
  fetchExerciseText: vi.fn(),
  fetchExerciseTextGenerationTask: vi.fn(),
  fetchExerciseTextReference: vi.fn(),
  fetchGrammarTopics: vi.fn(),
  fetchTtsVoices: vi.fn(),
  generateExerciseTextStage: vi.fn(),
  updateExerciseText: vi.fn(),
}));

const mockedConfirmParagraphStage = vi.mocked(confirmExerciseTextParagraphStage);
const mockedCreate = vi.mocked(createExerciseText);
const mockedFetchDetail = vi.mocked(fetchExerciseText);
const mockedFetchGenerationTask = vi.mocked(fetchExerciseTextGenerationTask);
const mockedFetchReference = vi.mocked(fetchExerciseTextReference);
const mockedFetchTopics = vi.mocked(fetchGrammarTopics);
const mockedFetchVoices = vi.mocked(fetchTtsVoices);
const mockedGenerate = vi.mocked(generateExerciseTextStage);

const t = {
  actionError: "Action error",
  close: "Close",
  create: "Create",
  difficultyBand: "Difficulty",
  empty: "Empty",
  exerciseTexts: "Texts for exercises",
  generationState: "Generation",
  grammarTopics: "Grammar topics",
  hasQuiz: "Quiz",
  loading: "Loading",
  save: "Save",
  saveError: "Save error",
  saving: "Saving",
  source: "Source",
  textType: "Text type",
  title: "Title",
  voice: "Voice",
};

describe("ExerciseTextEditorPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedFetchReference.mockResolvedValue({
      difficulty_bands: ["A1_A2", "B1_B2"],
      text_types: ["article", "science"],
    });
    mockedFetchTopics.mockResolvedValue({ items: [{ id: 7, code: "past_simple", title: "Past Simple" }] });
    mockedFetchVoices.mockResolvedValue({ items: [{ code: "en-US-Neural2-C", display_name: "US C" }] });
    mockedFetchGenerationTask.mockResolvedValue({ task: { id: 44, status: "success" }, exercise_text: existingExerciseText() });
    mockedConfirmParagraphStage.mockResolvedValue(existingExerciseText());
  });

  it("saves a new draft with source constraints", async () => {
    const user = userEvent.setup();
    mockedCreate.mockResolvedValue({ id: 12, version: 1, content_jsonb: { schema_version: 1 } });

    renderPage(<ExerciseTextEditorPage t={t} exerciseTextId={null} />);

    await user.type(await screen.findByLabelText("Title"), "Travel draft");
    await user.type(screen.getByLabelText("Source"), "A short source text.");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(mockedCreate).toHaveBeenCalledWith(expect.objectContaining({
        title: "Travel draft",
        content_jsonb: expect.objectContaining({
          schema_version: 1,
          source: expect.objectContaining({ english_text: "A short source text." }),
        }),
      }));
    });
    const payload = mockedCreate.mock.calls[0][0];
    expect(payload.content_jsonb.source.generation_constraints).not.toHaveProperty("text_types");
  });

  it("renders generation controls for existing drafts", async () => {
    const user = userEvent.setup();
    mockedFetchDetail.mockResolvedValue(existingExerciseText());
    mockedGenerate.mockResolvedValue({
      task: { id: 44, status: "success" },
      exercise_text: existingExerciseText(),
    });

    renderPage(<ExerciseTextEditorPage t={t} exerciseTextId={11} />);

    expect(await screen.findByRole("heading", { name: "Travel story" })).toBeInTheDocument();
    expect(screen.getByText("pg_valid_1")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Generate Content" }));

    await waitFor(() => {
      expect(mockedGenerate).toHaveBeenCalledWith({ exerciseTextId: 11, stage: "content", voiceCode: undefined });
    });
  });

  it("blocks generation while the form has unsaved edits", async () => {
    const user = userEvent.setup();
    mockedFetchDetail.mockResolvedValue(existingExerciseText());

    renderPage(<ExerciseTextEditorPage t={{ ...t, saveBeforeGenerate: "Save first" }} exerciseTextId={11} />);

    await screen.findByRole("heading", { name: "Travel story" });
    await user.type(screen.getByLabelText("Source"), " changed");
    await user.click(screen.getByRole("button", { name: "Generate Content" }));

    expect(await screen.findByText("Save first")).toBeInTheDocument();
    expect(mockedGenerate).not.toHaveBeenCalled();
  });

  it("requires save before generation when source constraints are not stored", async () => {
    const user = userEvent.setup();
    mockedFetchDetail.mockResolvedValue(existingExerciseText({ includeSourceConstraints: false }));

    renderPage(<ExerciseTextEditorPage t={{ ...t, saveBeforeGenerate: "Save first" }} exerciseTextId={11} />);

    await screen.findByRole("heading", { name: "Travel story" });
    await user.click(screen.getByRole("button", { name: "Generate Content" }));

    expect(await screen.findByText("Save first")).toBeInTheDocument();
    expect(mockedGenerate).not.toHaveBeenCalled();
  });

  it("highlights quiz evidence and confirms stale paragraph stages", async () => {
    const user = userEvent.setup();
    mockedFetchDetail.mockResolvedValue(existingExerciseText({ staleStage: "quiz" }));

    renderPage(<ExerciseTextEditorPage t={{ ...t, confirmStage: "Confirm" }} exerciseTextId={11} />);

    await screen.findByRole("heading", { name: "Travel story" });
    expect(screen.getByText("evidence ok")).toBeInTheDocument();

    await user.hover(screen.getByText("Correct"));
    expect(screen.getByText("One small robot opens the museum door.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Confirm quiz" }));
    expect(mockedConfirmParagraphStage).toHaveBeenCalledWith({ exerciseTextId: 11, paragraphId: "pg_valid_1", stage: "quiz", version: 3 });
  });
});

function renderPage(component) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/admin/exercise-texts/11"]}>
        {component}
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function existingExerciseText({ includeSourceConstraints = true, staleStage = null } = {}) {
  return {
    id: 11,
    title: "Travel story",
    version: 3,
    difficulty_band: "A1_A2",
    text_types: ["article"],
    topic_ids: [7],
    content_jsonb: {
      schema_version: 1,
      source: {
        english_text: "",
        ...(includeSourceConstraints
          ? { generation_constraints: { difficulty_band: "A1_A2", text_types: ["article"], topic_ids: [7] } }
          : {}),
      },
      generation_state: { content: "completed" },
      generated: {
        title: "Travel story",
        text_types: ["article"],
        paragraphs: [
          {
            id: "pg_valid_1",
            status: { content: "completed", ...(staleStage ? { [staleStage]: "stale" } : {}) },
            text: {
              source: { lang: "en", content: "One small robot opens the museum door. It greets every child. The children smile." },
              translations: [{ lang: "uk", content: "uk text" }],
            },
          },
        ],
        questions: [
          {
            id: "qz_valid_1",
            paragraph_ids: ["pg_valid_1"],
            question: { source: { lang: "en", content: "What happens?" }, translations: [] },
            options: [
              {
                id: "op_valid_1",
                text: { source: { lang: "en", content: "Correct" }, translations: [] },
                is_correct: true,
                evidence_quote: "One small robot opens the museum door.",
                evidence_span: { paragraph_id: "pg_valid_1", start_char: 0, end_char: 38 },
              },
            ],
          },
        ],
      },
    },
  };
}
