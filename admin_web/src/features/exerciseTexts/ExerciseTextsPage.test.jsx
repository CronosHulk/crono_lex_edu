import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ExerciseTextsPage } from "./ExerciseTextsPage";
import {
  fetchExerciseTextReference,
  fetchExerciseTexts,
  fetchGrammarTopics,
} from "./api/exerciseTextsApi";

vi.mock("./api/exerciseTextsApi", () => ({
  fetchExerciseTextReference: vi.fn(),
  fetchExerciseTexts: vi.fn(),
  fetchGrammarTopics: vi.fn(),
  exerciseTextsQueryKeys: {
    reference: () => ["exerciseTexts", "reference"],
    grammarTopics: () => ["exerciseTexts", "grammar-topics"],
    list: (params) => ["exerciseTexts", "list", params],
  },
}));

const mockedFetchReference = vi.mocked(fetchExerciseTextReference);
const mockedFetchTexts = vi.mocked(fetchExerciseTexts);
const mockedFetchTopics = vi.mocked(fetchGrammarTopics);

const t = {
  all: "All",
  archived: "Archived",
  date: "Created",
  difficultyBand: "Difficulty",
  emptyExerciseTexts: "No texts",
  exerciseTexts: "Texts for exercises",
  generationState: "Generation",
  grammarTopics: "Grammar topics",
  hasQuiz: "Quiz",
  hasTts: "TTS",
  loading: "Loading",
  loadError: "Load error",
  no: "No",
  search: "Search",
  status: "Status",
  textType: "Text type",
  title: "Title",
  translations: "Translations",
  updated: "Updated",
  yes: "Yes",
};

describe("ExerciseTextsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedFetchReference.mockResolvedValue({
      difficulty_bands: ["A1_A2", "B1_B2"],
      statuses: ["draft", "ready", "published", "archived"],
      text_types: ["reading", "listening"],
    });
    mockedFetchTopics.mockResolvedValue({
      items: [{ id: 7, code: "past_simple", title: "Past Simple" }],
    });
    mockedFetchTexts.mockResolvedValue({
      items: [
        {
          id: 11,
          uuid: "11111111-1111-4111-8111-111111111111",
          title: "Travel story",
          status: "draft",
          difficulty_band: "A1_A2",
          text_types: ["reading"],
          topic_ids: [7],
          content_jsonb: {
            generation_state: { content: "completed" },
            generated: {
              paragraphs: [{ translations: { uk: "Подорож" } }],
              questions: [{ id: "qz_1" }],
              audio: { files: [{ scope: "full" }] },
            },
          },
          created: "2026-05-12 10:00:00",
          updated: "2026-05-12 11:00:00",
        },
      ],
      total: 1,
    });
  });

  it("renders list rows and reads URL params into the query", async () => {
    renderPage("/admin/exercise-texts?page=2&page_size=100&search=travel&status=draft&difficulty_band=A1_A2&text_type=reading&topic_id=7&has_quiz=yes&has_tts=yes");

    expect(await screen.findByText("Travel story")).toBeInTheDocument();
    const row = screen.getByText("Travel story").closest("tr");
    expect(row).not.toBeNull();
    expect(within(row).getByText("Past Simple")).toBeInTheDocument();
    expect(within(row).getAllByText("Yes")).toHaveLength(3);

    await waitFor(() => {
      expect(mockedFetchTexts.mock.calls[0]?.[0]).toMatchObject({
        difficultyBands: ["A1_A2"],
        hasQuiz: "yes",
        hasTts: "yes",
        page: 2,
        pageSize: 100,
        search: "travel",
        statuses: ["draft"],
        textTypes: ["reading"],
        topicIds: ["7"],
      });
    });
  });
});

function renderPage(initialEntry = "/admin/exercise-texts") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <ExerciseTextsPage t={t} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
