export type ExerciseTextsListSearchParams = {
  archived: boolean;
  difficultyBands: string[];
  hasQuiz: "all" | "yes" | "no";
  hasTts: "all" | "yes" | "no";
  page: number;
  pageSize: number;
  search: string;
  sort: string;
  statuses: string[];
  textTypes: string[];
  topicIds: string[];
};

export function exerciseTextsParamsFromSearch(searchParams: URLSearchParams): ExerciseTextsListSearchParams {
  return {
    archived: searchParams.get("archived") === "true",
    difficultyBands: searchParams.getAll("difficulty_band"),
    hasQuiz: booleanChoiceParam(searchParams.get("has_quiz")),
    hasTts: booleanChoiceParam(searchParams.get("has_tts")),
    page: positiveIntParam(searchParams.get("page"), 1),
    pageSize: positiveIntParam(searchParams.get("page_size"), 50),
    search: searchParams.get("search") || "",
    sort: searchParams.get("sort") || "updated_desc",
    statuses: searchParams.getAll("status"),
    textTypes: searchParams.getAll("text_type"),
    topicIds: searchParams.getAll("topic_id"),
  };
}

export function applyExerciseTextsParamUpdates(
  searchParams: URLSearchParams,
  updates: Partial<ExerciseTextsListSearchParams>,
): URLSearchParams {
  const next = new URLSearchParams(searchParams);
  if ("page" in updates) setSearchParam(next, "page", updates.page, 1);
  if ("pageSize" in updates) setSearchParam(next, "page_size", updates.pageSize, 50);
  if ("archived" in updates) setSearchParam(next, "archived", updates.archived, false);
  if ("search" in updates) setSearchParam(next, "search", updates.search, "");
  if ("sort" in updates) setSearchParam(next, "sort", updates.sort, "updated_desc");
  if ("hasQuiz" in updates) setSearchParam(next, "has_quiz", updates.hasQuiz, "all");
  if ("hasTts" in updates) setSearchParam(next, "has_tts", updates.hasTts, "all");
  if ("statuses" in updates) setRepeatedSearchParam(next, "status", updates.statuses);
  if ("difficultyBands" in updates) setRepeatedSearchParam(next, "difficulty_band", updates.difficultyBands);
  if ("textTypes" in updates) setRepeatedSearchParam(next, "text_type", updates.textTypes);
  if ("topicIds" in updates) setRepeatedSearchParam(next, "topic_id", updates.topicIds);
  return next;
}

function booleanChoiceParam(value: string | null): "all" | "yes" | "no" {
  if (value === "yes" || value === "no") return value;
  return "all";
}

function positiveIntParam(value: string | null, fallback: number): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function setSearchParam(params: URLSearchParams, key: string, value: unknown, defaultValue: unknown) {
  if (value === defaultValue || value === "" || value === null || value === undefined) {
    params.delete(key);
    return;
  }
  params.set(key, String(value));
}

function setRepeatedSearchParam(params: URLSearchParams, key: string, values: string[] | undefined) {
  params.delete(key);
  values?.forEach((value) => params.append(key, value));
}
