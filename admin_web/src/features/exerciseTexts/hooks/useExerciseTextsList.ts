import { useQuery } from "@tanstack/react-query";

import {
  exerciseTextsQueryKeys,
  fetchExerciseTextReference,
  fetchExerciseTexts,
  fetchGrammarTopics,
  type ExerciseTextsListParams,
} from "../api/exerciseTextsApi";

export function useExerciseTextsList(params: ExerciseTextsListParams) {
  const referenceQuery = useQuery({
    queryKey: exerciseTextsQueryKeys.reference(),
    queryFn: fetchExerciseTextReference,
  });
  const grammarTopicsQuery = useQuery({
    queryKey: exerciseTextsQueryKeys.grammarTopics(),
    queryFn: fetchGrammarTopics,
  });
  const listQuery = useQuery({
    queryKey: exerciseTextsQueryKeys.list(params),
    queryFn: () => fetchExerciseTexts(params),
  });

  return {
    grammarTopicsQuery,
    listQuery,
    referenceQuery,
  };
}
