import { describe, expect, it } from "vitest";

import { applyExerciseTextsParamUpdates, exerciseTextsParamsFromSearch } from "./listParams";

describe("exerciseTextsParamsFromSearch", () => {
  it("reads defaults", () => {
    expect(exerciseTextsParamsFromSearch(new URLSearchParams())).toEqual({
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
  });

  it("reads explicit params", () => {
    const params = new URLSearchParams(
      "archived=true&page=2&page_size=100&search=travel&sort=updated_asc&has_quiz=yes&has_tts=no&status=draft&difficulty_band=A1_A2&text_type=reading&topic_id=7",
    );

    expect(exerciseTextsParamsFromSearch(params)).toEqual({
      archived: true,
      difficultyBands: ["A1_A2"],
      hasQuiz: "yes",
      hasTts: "no",
      page: 2,
      pageSize: 100,
      search: "travel",
      sort: "updated_asc",
      statuses: ["draft"],
      textTypes: ["reading"],
      topicIds: ["7"],
    });
  });
});

describe("applyExerciseTextsParamUpdates", () => {
  it("removes default values", () => {
    const params = new URLSearchParams(
      "archived=true&page=2&page_size=100&search=travel&sort=updated_asc&has_quiz=yes&has_tts=no&status=draft&difficulty_band=A1_A2&text_type=reading&topic_id=7",
    );

    expect(applyExerciseTextsParamUpdates(params, {
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
    }).toString()).toBe("");
  });

  it("writes non-default values", () => {
    const result = applyExerciseTextsParamUpdates(new URLSearchParams(), {
      archived: true,
      difficultyBands: ["A1_A2"],
      hasQuiz: "yes",
      hasTts: "no",
      page: 2,
      pageSize: 100,
      search: "travel",
      sort: "updated_asc",
      statuses: ["draft", "ready"],
      textTypes: ["reading"],
      topicIds: ["7", "8"],
    });

    expect(result.toString()).toBe(
      "page=2&page_size=100&archived=true&search=travel&sort=updated_asc&has_quiz=yes&has_tts=no&status=draft&status=ready&difficulty_band=A1_A2&text_type=reading&topic_id=7&topic_id=8",
    );
  });

  it("updates only provided params and preserves the rest", () => {
    const params = new URLSearchParams("search=travel&status=draft&topic_id=7");

    expect(applyExerciseTextsParamUpdates(params, { search: "museum" }).toString()).toBe("search=museum&status=draft&topic_id=7");
  });

  it("clears repeated filters when update value is undefined", () => {
    const params = new URLSearchParams("status=draft&difficulty_band=A1_A2&text_type=reading&topic_id=7");

    expect(applyExerciseTextsParamUpdates(params, {
      difficultyBands: undefined,
      statuses: undefined,
      textTypes: undefined,
      topicIds: undefined,
    }).toString()).toBe("");
  });
});
