import { adminApi } from "../../../api/adminApi";

export type ExerciseTextsListParams = {
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

export type ExerciseTextPayload = {
  title: string | null;
  difficulty_band: string | null;
  text_types: string[];
  topic_ids: number[];
  content_jsonb: Record<string, unknown>;
  version?: number;
  force_topic_difficulty?: { reason: string };
};

export type ExerciseTextParagraphConfirmPayload = {
  paragraphId: string;
  stage: string;
  version: number;
};

export const exerciseTextsQueryKeys = {
  all: ["exerciseTexts"] as const,
  reference: () => [...exerciseTextsQueryKeys.all, "reference"] as const,
  grammarTopics: () => [...exerciseTextsQueryKeys.all, "grammar-topics"] as const,
  ttsVoices: () => [...exerciseTextsQueryKeys.all, "tts-voices"] as const,
  lists: () => [...exerciseTextsQueryKeys.all, "list"] as const,
  list: (params: ExerciseTextsListParams) => [...exerciseTextsQueryKeys.lists(), params] as const,
  details: () => [...exerciseTextsQueryKeys.all, "detail"] as const,
  detail: (exerciseTextId: number | string) => [...exerciseTextsQueryKeys.details(), Number(exerciseTextId)] as const,
  generationTask: (exerciseTextId: number | string, taskId: number | string) => (
    [...exerciseTextsQueryKeys.detail(exerciseTextId), "generation-task", Number(taskId)] as const
  ),
};

export function fetchExerciseTexts(params: ExerciseTextsListParams) {
  return adminApi(`/exercise-texts?${exerciseTextsSearchParams(params).toString()}`);
}

export function fetchExerciseTextReference() {
  return adminApi("/reference/exercise-text-options");
}

export function fetchGrammarTopics() {
  return adminApi("/reference/grammar-topics");
}

export function fetchTtsVoices() {
  return adminApi("/reference/tts-voices?provider=google_tts");
}

export function fetchExerciseText(exerciseTextId: number | string) {
  return adminApi(`/exercise-texts/${exerciseTextId}`);
}

export function createExerciseText(payload: ExerciseTextPayload) {
  return adminApi("/exercise-texts", { method: "POST", body: JSON.stringify(payload) });
}

export function updateExerciseText({ exerciseTextId, payload }: { exerciseTextId: number | string; payload: ExerciseTextPayload }) {
  return adminApi(`/exercise-texts/${exerciseTextId}`, { method: "PUT", body: JSON.stringify(payload) });
}

export function generateExerciseTextStage({ exerciseTextId, stage, voiceCode }: { exerciseTextId: number | string; stage: string; voiceCode?: string }) {
  const path = stage === "tts" ? "generate-tts" : `generate-${stage}`;
  const body = stage === "tts" && voiceCode ? { voice_code: voiceCode } : {};
  return adminApi(`/exercise-texts/${exerciseTextId}/${path}`, { method: "POST", body: JSON.stringify(body) });
}

export function fetchExerciseTextGenerationTask({ exerciseTextId, taskId }: { exerciseTextId: number | string; taskId: number | string }) {
  return adminApi(`/exercise-texts/${exerciseTextId}/generation-tasks/${taskId}`);
}

export function confirmExerciseTextParagraphStage({
  exerciseTextId,
  paragraphId,
  stage,
  version,
}: { exerciseTextId: number | string } & ExerciseTextParagraphConfirmPayload) {
  return adminApi(`/exercise-texts/${exerciseTextId}/paragraphs/${encodeURIComponent(paragraphId)}/confirm-stage`, {
    method: "POST",
    body: JSON.stringify({ stage, version }),
  });
}

function exerciseTextsSearchParams(params: ExerciseTextsListParams): URLSearchParams {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
    archived: String(params.archived),
    search: params.search,
  });
  if (params.sort !== "updated_desc") query.set("sort", params.sort);
  params.statuses.forEach((value) => query.append("status", value));
  params.difficultyBands.forEach((value) => query.append("difficulty_band", value));
  params.textTypes.forEach((value) => query.append("text_type", value));
  params.topicIds.forEach((value) => query.append("topic_id", value));
  if (params.hasQuiz !== "all") query.set("has_quiz", params.hasQuiz);
  if (params.hasTts !== "all") query.set("has_tts", params.hasTts);
  return query;
}
