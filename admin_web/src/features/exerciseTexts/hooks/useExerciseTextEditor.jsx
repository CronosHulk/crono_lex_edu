import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createExerciseText,
  confirmExerciseTextParagraphStage,
  exerciseTextsQueryKeys,
  fetchExerciseText,
  fetchExerciseTextGenerationTask,
  fetchExerciseTextReference,
  fetchGrammarTopics,
  fetchTtsVoices,
  generateExerciseTextStage,
  updateExerciseText,
} from "../api/exerciseTextsApi";

export function useExerciseTextEditor(exerciseTextId, taskIds) {
  const queryClient = useQueryClient();
  const isNew = exerciseTextId === null;

  const invalidateExerciseText = async (savedId) => {
    await queryClient.invalidateQueries({ queryKey: exerciseTextsQueryKeys.lists() });
    if (exerciseTextId !== null) {
      await queryClient.invalidateQueries({ queryKey: exerciseTextsQueryKeys.detail(exerciseTextId) });
    }
    if (savedId) {
      await queryClient.invalidateQueries({ queryKey: exerciseTextsQueryKeys.detail(savedId) });
    }
  };

  const detailQuery = useQuery({
    queryKey: exerciseTextsQueryKeys.detail(exerciseTextId || 0),
    queryFn: () => fetchExerciseText(exerciseTextId || 0),
    enabled: !isNew,
  });
  const referenceQuery = useQuery({
    queryKey: exerciseTextsQueryKeys.reference(),
    queryFn: fetchExerciseTextReference,
  });
  const grammarTopicsQuery = useQuery({
    queryKey: exerciseTextsQueryKeys.grammarTopics(),
    queryFn: fetchGrammarTopics,
  });
  const ttsVoicesQuery = useQuery({
    queryKey: exerciseTextsQueryKeys.ttsVoices(),
    queryFn: fetchTtsVoices,
  });
  const saveMutation = useMutation({
    mutationFn: (payload) => (
      isNew ? createExerciseText(payload) : updateExerciseText({ exerciseTextId: exerciseTextId || 0, payload })
    ),
    onSuccess: (data) => {
      const savedId = idFromPayload(data);
      if (savedId) queryClient.setQueryData(exerciseTextsQueryKeys.detail(savedId), data);
      invalidateExerciseText(savedId);
    },
  });
  const generationMutation = useMutation({
    mutationFn: ({ stage, voiceCode }) => (
      generateExerciseTextStage({ exerciseTextId: exerciseTextId || 0, stage, voiceCode })
    ),
    onSuccess: (data) => {
      const saved = exerciseTextFromPayload(data);
      const savedId = idFromPayload(saved);
      if (savedId) queryClient.setQueryData(exerciseTextsQueryKeys.detail(savedId), saved);
      invalidateExerciseText(savedId || exerciseTextId);
    },
  });
  const confirmParagraphStageMutation = useMutation({
    mutationFn: ({ paragraphId, stage, version }) => (
      confirmExerciseTextParagraphStage({ exerciseTextId: exerciseTextId || 0, paragraphId, stage, version })
    ),
    onSuccess: (data) => {
      const savedId = idFromPayload(data);
      if (savedId) queryClient.setQueryData(exerciseTextsQueryKeys.detail(savedId), data);
      invalidateExerciseText(savedId || exerciseTextId);
    },
  });
  const taskQueries = useQueries({
    queries: taskIds.map((taskId) => ({
      queryKey: exerciseTextsQueryKeys.generationTask(exerciseTextId || 0, taskId),
      queryFn: () => fetchExerciseTextGenerationTask({ exerciseTextId: exerciseTextId || 0, taskId }),
      enabled: Boolean(exerciseTextId),
      refetchInterval: (query) => {
        const data = query.state.data;
        updateExerciseTextCache(queryClient, data);
        const status = taskStatusFromPayload(data);
        return status === "processing" || status === "queued" ? 2000 : false;
      },
    })),
  });

  return {
    confirmParagraphStageMutation,
    detailQuery,
    generationMutation,
    grammarTopicsQuery,
    isNew,
    referenceQuery,
    saveMutation,
    taskQueries,
    ttsVoicesQuery,
  };
}

function asRecord(value) {
  return value && typeof value === "object" ? value : null;
}

function idFromPayload(value) {
  const id = asRecord(value)?.id;
  return typeof id === "number" || typeof id === "string" ? id : null;
}

function exerciseTextFromPayload(value) {
  return asRecord(value)?.exercise_text || value;
}

function taskStatusFromPayload(value) {
  const task = asRecord(asRecord(value)?.task);
  return typeof task?.status === "string" ? task.status : null;
}

function updateExerciseTextCache(queryClient, value) {
  const exerciseText = exerciseTextFromPayload(value);
  const savedId = idFromPayload(exerciseText);
  if (savedId) queryClient.setQueryData(exerciseTextsQueryKeys.detail(savedId), exerciseText);
}
