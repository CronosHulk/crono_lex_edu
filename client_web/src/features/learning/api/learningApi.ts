import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { clientApi } from "../../../api/clientApi";

export const learningStateKey = ["learning", "state"] as const;
export const learningWordsKey = ["learning", "words"] as const;
export const learningWordFiltersKey = ["learning", "word-filters"] as const;
export const dictionarySearchKey = ["learning", "dictionary-search"] as const;

type LearningWordsParams = {
  mode: string;
  page: number;
  pageSize: number;
  word?: string;
  topic?: string | string[];
  level?: string;
  enabled?: boolean;
};

type DictionarySearchParams = {
  query: string;
  page: number;
  pageSize: number;
  level?: string;
  enabled?: boolean;
};

export function useLearningState() {
  return useQuery({
    queryKey: learningStateKey,
    queryFn: () => clientApi("/learning/state"),
    refetchInterval: 2500
  });
}

export function useLearningWords(params: LearningWordsParams) {
  return useQuery({
    queryKey: [...learningWordsKey, params],
    queryFn: () => clientApi(`/learning/words?${learningWordsSearchParams(params).toString()}`),
    enabled: params.enabled ?? true
  });
}

export function useLearningWordFilters() {
  return useQuery({
    queryKey: learningWordFiltersKey,
    queryFn: () => clientApi("/learning/word-filters")
  });
}

export function useDictionarySearch(params: DictionarySearchParams) {
  return useQuery({
    queryKey: [...dictionarySearchKey, params],
    queryFn: () => clientApi(`/learning/dictionary-search?${dictionarySearchParams(params).toString()}`),
    enabled: params.enabled ?? true
  });
}

export function useLearnDictionaryWord() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { word_source: "core" | "user"; word_id: number }) =>
      clientApi("/learning/dictionary-search/learn", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dictionarySearchKey });
      queryClient.invalidateQueries({ queryKey: learningWordsKey });
      queryClient.invalidateQueries({ queryKey: learningStateKey });
    }
  });
}

export function usePrioritizeLearningWord() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { word_source: "core" | "user"; word_id: number }) =>
      clientApi("/learning/words/priority", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: learningWordsKey });
      queryClient.invalidateQueries({ queryKey: learningStateKey });
    }
  });
}

export function useStartTraining() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => clientApi("/learning/start", { method: "POST", body: "{}" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: learningStateKey })
  });
}

export function useContinueTraining() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => clientApi("/learning/continue", { method: "POST", body: "{}" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: learningStateKey })
  });
}

export function useFinishTraining() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => clientApi("/learning/finish", { method: "POST", body: "{}" }),
    onSuccess: () => {
      queryClient.setQueryData(learningStateKey, (current: unknown) => ({
        ...(current && typeof current === "object" ? current : {}),
        active_session: null,
      }));
      queryClient.invalidateQueries({ queryKey: learningStateKey });
    }
  });
}

export function useAnswerTraining() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { session_word_id: number; option_index: number }) =>
      clientApi("/learning/answer", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: learningStateKey })
  });
}

export function useCardAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { session_word_id: number; action: string }) =>
      clientApi("/learning/card-action", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: learningStateKey })
  });
}

export function useReadyAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { expected_stage: string; decision: "yes" | "no" }) =>
      clientApi("/learning/ready-action", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: learningStateKey })
  });
}

function dictionarySearchParams(params: DictionarySearchParams): URLSearchParams {
  const searchParams = new URLSearchParams({
    q: params.query,
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.level) searchParams.set("level", params.level);
  return searchParams;
}

function learningWordsSearchParams(params: LearningWordsParams): URLSearchParams {
  const searchParams = new URLSearchParams({
    mode: params.mode,
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.word) searchParams.set("word", params.word);
  if (Array.isArray(params.topic)) {
    params.topic.forEach((topic) => {
      if (topic) searchParams.append("topic", topic);
    });
  } else if (params.topic) {
    searchParams.set("topic", params.topic);
  }
  if (params.level) searchParams.set("level", params.level);
  return searchParams;
}
