import { beforeEach, describe, expect, it, vi } from "vitest";

import { adminApi } from "../../../api/adminApi";
import {
  createExerciseText,
  confirmExerciseTextParagraphStage,
  exerciseTextsQueryKeys,
  fetchExerciseText,
  fetchExerciseTextGenerationTask,
  fetchExerciseTextReference,
  fetchExerciseTexts,
  fetchGrammarTopics,
  fetchTtsVoices,
  generateExerciseTextStage,
  updateExerciseText,
} from "./exerciseTextsApi";

vi.mock("../../../api/adminApi", () => ({
  adminApi: vi.fn(),
}));

const mockedAdminApi = vi.mocked(adminApi);

describe("exerciseTextsApi", () => {
  beforeEach(() => {
    mockedAdminApi.mockClear();
  });

  it("builds list requests with backend-supported filters", () => {
    fetchExerciseTexts({
      archived: true,
      difficultyBands: ["A1_A2", "B1_B2"],
      hasQuiz: "yes",
      hasTts: "no",
      page: 2,
      pageSize: 100,
      search: "travel",
      sort: "updated_desc",
      statuses: ["draft"],
      textTypes: ["article", "science"],
      topicIds: ["7"],
    });

    expect(mockedAdminApi).toHaveBeenCalledWith(
      "/exercise-texts?page=2&page_size=100&archived=true&search=travel&status=draft&difficulty_band=A1_A2&difficulty_band=B1_B2&text_type=article&text_type=science&topic_id=7&has_quiz=yes&has_tts=no",
    );
  });

  it("omits optional boolean filters when all values are requested", () => {
    fetchExerciseTexts({
      archived: false,
      difficultyBands: [],
      hasQuiz: "all",
      hasTts: "all",
      page: 1,
      pageSize: 50,
      search: "",
      sort: "updated_desc",
      statuses: [],
      textTypes: [],
      topicIds: [],
    });

    expect(mockedAdminApi).toHaveBeenCalledWith("/exercise-texts?page=1&page_size=50&archived=false&search=");
  });

  it("sends non-default sort values", () => {
    fetchExerciseTexts({
      archived: false,
      difficultyBands: [],
      hasQuiz: "all",
      hasTts: "all",
      page: 1,
      pageSize: 50,
      search: "",
      sort: "title_asc",
      statuses: [],
      textTypes: [],
      topicIds: [],
    });

    expect(mockedAdminApi).toHaveBeenCalledWith("/exercise-texts?page=1&page_size=50&archived=false&search=&sort=title_asc");
  });

  it("loads reference endpoints", () => {
    fetchExerciseTextReference();
    fetchGrammarTopics();
    fetchTtsVoices();

    expect(mockedAdminApi).toHaveBeenNthCalledWith(1, "/reference/exercise-text-options");
    expect(mockedAdminApi).toHaveBeenNthCalledWith(2, "/reference/grammar-topics");
    expect(mockedAdminApi).toHaveBeenNthCalledWith(3, "/reference/tts-voices?provider=google_tts");
  });

  it("loads detail and sends save payloads", () => {
    const payload = {
      title: "Travel",
      difficulty_band: "A1_A2",
      text_types: ["article"],
      topic_ids: [7],
      content_jsonb: { schema_version: 1 },
    };

    fetchExerciseText(11);
    createExerciseText(payload);
    updateExerciseText({ exerciseTextId: 11, payload: { ...payload, version: 2 } });

    expect(mockedAdminApi).toHaveBeenCalledWith("/exercise-texts/11");
    expect(mockedAdminApi).toHaveBeenCalledWith("/exercise-texts", { method: "POST", body: JSON.stringify(payload) });
    expect(mockedAdminApi).toHaveBeenCalledWith("/exercise-texts/11", { method: "PUT", body: JSON.stringify({ ...payload, version: 2 }) });
  });

  it("starts generation stages", () => {
    generateExerciseTextStage({ exerciseTextId: 11, stage: "content" });
    generateExerciseTextStage({ exerciseTextId: 11, stage: "translations" });
    generateExerciseTextStage({ exerciseTextId: 11, stage: "quiz" });
    generateExerciseTextStage({ exerciseTextId: 11, stage: "all" });
    generateExerciseTextStage({ exerciseTextId: 11, stage: "tts", voiceCode: "en-US-Neural2-C" });

    expect(mockedAdminApi).toHaveBeenCalledWith("/exercise-texts/11/generate-content", { method: "POST", body: "{}" });
    expect(mockedAdminApi).toHaveBeenCalledWith("/exercise-texts/11/generate-translations", { method: "POST", body: "{}" });
    expect(mockedAdminApi).toHaveBeenCalledWith("/exercise-texts/11/generate-quiz", { method: "POST", body: "{}" });
    expect(mockedAdminApi).toHaveBeenCalledWith("/exercise-texts/11/generate-all", { method: "POST", body: "{}" });
    expect(mockedAdminApi).toHaveBeenCalledWith("/exercise-texts/11/generate-tts", {
      method: "POST",
      body: JSON.stringify({ voice_code: "en-US-Neural2-C" }),
    });
  });

  it("loads generation tasks", () => {
    fetchExerciseTextGenerationTask({ exerciseTextId: 11, taskId: 44 });

    expect(mockedAdminApi).toHaveBeenCalledWith("/exercise-texts/11/generation-tasks/44");
  });

  it("confirms paragraph generation stages", () => {
    confirmExerciseTextParagraphStage({ exerciseTextId: 11, paragraphId: "pg_valid_1", stage: "quiz", version: 3 });

    expect(mockedAdminApi).toHaveBeenCalledWith("/exercise-texts/11/paragraphs/pg_valid_1/confirm-stage", {
      method: "POST",
      body: JSON.stringify({ stage: "quiz", version: 3 }),
    });
  });

  it("creates stable query keys", () => {
    const params = {
      archived: false,
      difficultyBands: [],
      hasQuiz: "all" as const,
      hasTts: "all" as const,
      page: 1,
      pageSize: 50,
      search: "",
      sort: "updated_desc",
      statuses: ["draft"],
      textTypes: [],
      topicIds: [],
    };

    expect(exerciseTextsQueryKeys.reference()).toEqual(["exerciseTexts", "reference"]);
    expect(exerciseTextsQueryKeys.grammarTopics()).toEqual(["exerciseTexts", "grammar-topics"]);
    expect(exerciseTextsQueryKeys.ttsVoices()).toEqual(["exerciseTexts", "tts-voices"]);
    expect(exerciseTextsQueryKeys.detail(11)).toEqual(["exerciseTexts", "detail", 11]);
    expect(exerciseTextsQueryKeys.generationTask(11, 44)).toEqual(["exerciseTexts", "detail", 11, "generation-task", 44]);
    expect(exerciseTextsQueryKeys.list(params)).toEqual(["exerciseTexts", "list", params]);
  });
});
