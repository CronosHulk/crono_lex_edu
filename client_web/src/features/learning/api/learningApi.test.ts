import { describe, expect, it, vi } from "vitest";

import {
  dictionarySearchKey,
  learningStateKey,
  learningWordFiltersKey,
  learningWordsKey,
  useDictionarySearch,
  useAnswerTraining,
  useCardAction,
  useContinueTraining,
  useFinishTraining,
  useLearnDictionaryWord,
  useLearningWordFilters,
  useLearningState,
  useLearningWords,
  usePrioritizeLearningWord,
  useReadyAction,
  useStartTraining,
} from "./learningApi";
import { clientApi } from "../../../api/clientApi";

const invalidateQueries = vi.fn();
const setQueryData = vi.fn();
const useMutationMock = vi.fn((config) => config);
const useQueryMock = vi.fn((config) => config);

vi.mock("@tanstack/react-query", () => ({
  useMutation: (config: unknown) => useMutationMock(config),
  useQuery: (config: unknown) => useQueryMock(config),
  useQueryClient: () => ({ invalidateQueries, setQueryData }),
}));

vi.mock("../../../api/clientApi", () => ({
  clientApi: vi.fn(),
}));

describe("learning api hooks", () => {
  it("builds the state query", () => {
    const query = useLearningState() as unknown as { queryFn: () => unknown; queryKey: readonly string[]; refetchInterval: number };

    expect(query).toMatchObject({ queryKey: learningStateKey, refetchInterval: 2500 });
    query.queryFn();
    expect(clientApi).toHaveBeenCalledWith("/learning/state");
  });

  it("builds the learning words query", () => {
    const query = useLearningWords({
      mode: "learning",
      page: 2,
      pageSize: 50,
      word: "passion",
      topic: ["emotion", "", "planning"],
      level: "A1",
    }) as unknown as { queryFn: () => unknown; queryKey: readonly unknown[] };

    expect(query.queryKey[0]).toBe("learning");
    query.queryFn();
    expect(clientApi).toHaveBeenCalledWith(
      "/learning/words?mode=learning&page=2&page_size=50&word=passion&topic=emotion&topic=planning&level=A1",
    );
  });

  it("builds the learning word filters query", () => {
    const query = useLearningWordFilters() as unknown as { queryFn: () => unknown; queryKey: readonly string[] };

    expect(query).toMatchObject({ queryKey: learningWordFiltersKey });
    query.queryFn();
    expect(clientApi).toHaveBeenCalledWith("/learning/word-filters");
  });

  it("builds the dictionary search query", () => {
    const query = useDictionarySearch({
      query: "stor",
      page: 2,
      pageSize: 50,
      level: "A2",
    }) as unknown as { queryFn: () => unknown; queryKey: readonly unknown[] };

    expect(query.queryKey[0]).toBe("learning");
    expect(query.queryKey[1]).toBe("dictionary-search");
    query.queryFn();
    expect(clientApi).toHaveBeenCalledWith("/learning/dictionary-search?q=stor&page=2&page_size=50&level=A2");
  });

  it("builds the dictionary search query without optional level", () => {
    const query = useDictionarySearch({
      query: "stor",
      page: 1,
      pageSize: 20,
    }) as unknown as { queryFn: () => unknown };

    query.queryFn();
    expect(clientApi).toHaveBeenCalledWith("/learning/dictionary-search?q=stor&page=1&page_size=20");
  });

  it("builds the learning words query without optional filters", () => {
    const query = useLearningWords({
      mode: "learned",
      page: 1,
      pageSize: 20,
      enabled: false,
    }) as unknown as { enabled: boolean; queryFn: () => unknown };

    expect(query.enabled).toBe(false);
    query.queryFn();
    expect(clientApi).toHaveBeenCalledWith("/learning/words?mode=learned&page=1&page_size=20");
  });

  it("keeps backward-compatible single topic query values", () => {
    const query = useLearningWords({
      mode: "learning",
      page: 1,
      pageSize: 20,
      topic: "business",
    }) as unknown as { queryFn: () => unknown };

    query.queryFn();
    expect(clientApi).toHaveBeenCalledWith("/learning/words?mode=learning&page=1&page_size=20&topic=business");
  });

  it("builds training mutations and invalidates learning state", () => {
    const start = useStartTraining() as unknown as { mutationFn: () => unknown; onSuccess: () => void };
    const resume = useContinueTraining() as unknown as { mutationFn: () => unknown; onSuccess: () => void };
    const finish = useFinishTraining() as unknown as { mutationFn: () => unknown; onSuccess: () => void };
    const answer = useAnswerTraining() as unknown as {
      mutationFn: (payload: { session_word_id: number; option_index: number }) => unknown;
      onSuccess: () => void;
    };
    const card = useCardAction() as unknown as {
      mutationFn: (payload: { session_word_id: number; action: string }) => unknown;
      onSuccess: () => void;
    };
    const ready = useReadyAction() as unknown as {
      mutationFn: (payload: { expected_stage: string; decision: "yes" | "no" }) => unknown;
      onSuccess: () => void;
    };
    const priority = usePrioritizeLearningWord() as unknown as {
      mutationFn: (payload: { word_source: "core" | "user"; word_id: number }) => unknown;
      onSuccess: () => void;
    };
    const learnDictionaryWord = useLearnDictionaryWord() as unknown as {
      mutationFn: (payload: { word_source: "core" | "user"; word_id: number }) => unknown;
      onSuccess: () => void;
    };

    start.mutationFn();
    resume.mutationFn();
    finish.mutationFn();
    answer.mutationFn({ session_word_id: 7, option_index: 2 });
    card.mutationFn({ session_word_id: 8, action: "know" });
    ready.mutationFn({ expected_stage: "ready_en_uk", decision: "yes" });
    priority.mutationFn({ word_source: "user", word_id: 88 });
    learnDictionaryWord.mutationFn({ word_source: "core", word_id: 42 });
    start.onSuccess();
    resume.onSuccess();
    finish.onSuccess();
    answer.onSuccess();
    card.onSuccess();
    ready.onSuccess();
    priority.onSuccess();
    learnDictionaryWord.onSuccess();

    expect(clientApi).toHaveBeenCalledWith("/learning/start", { method: "POST", body: "{}" });
    expect(clientApi).toHaveBeenCalledWith("/learning/continue", { method: "POST", body: "{}" });
    expect(clientApi).toHaveBeenCalledWith("/learning/finish", { method: "POST", body: "{}" });
    expect(clientApi).toHaveBeenCalledWith("/learning/answer", {
      method: "POST",
      body: JSON.stringify({ session_word_id: 7, option_index: 2 }),
    });
    expect(clientApi).toHaveBeenCalledWith("/learning/card-action", {
      method: "POST",
      body: JSON.stringify({ session_word_id: 8, action: "know" }),
    });
    expect(clientApi).toHaveBeenCalledWith("/learning/ready-action", {
      method: "POST",
      body: JSON.stringify({ expected_stage: "ready_en_uk", decision: "yes" }),
    });
    expect(clientApi).toHaveBeenCalledWith("/learning/words/priority", {
      method: "POST",
      body: JSON.stringify({ word_source: "user", word_id: 88 }),
    });
    expect(clientApi).toHaveBeenCalledWith("/learning/dictionary-search/learn", {
      method: "POST",
      body: JSON.stringify({ word_source: "core", word_id: 42 }),
    });
    expect(invalidateQueries).toHaveBeenCalledTimes(11);
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: learningStateKey });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: learningWordsKey });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: dictionarySearchKey });
    expect(setQueryData).toHaveBeenCalledWith(learningStateKey, expect.any(Function));
    const finishUpdater = setQueryData.mock.calls[0][1] as (current: unknown) => unknown;
    expect(finishUpdater({ active_session: { id: 7 }, has_teacher_link: true })).toEqual({
      active_session: null,
      has_teacher_link: true,
    });
    expect(finishUpdater(null)).toEqual({ active_session: null });
  });
});
