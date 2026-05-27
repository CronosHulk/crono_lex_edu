import { describe, expect, it, vi } from "vitest";

import { importWordsQueryKeys, useImportItems, useImportJobEvents, useImportJobItems, useSubmitImportWords, useUnbindImportGoogleDoc } from "./importWordsApi";
import { CLIENT_API_BASE, clientApi } from "../../../api/clientApi";
import { learningWordsKey } from "../../learning/api/learningApi";
import { settingsKey } from "../../settings/api/settingsApi";

const invalidateQueries = vi.fn();
const useMutationMock = vi.fn((config) => config);
const useQueryMock = vi.fn((config) => config);

vi.mock("@tanstack/react-query", () => ({
  keepPreviousData: Symbol.for("keepPreviousData"),
  useMutation: (config: unknown) => useMutationMock(config),
  useQuery: (config: unknown) => useQueryMock(config),
  useQueryClient: () => ({ invalidateQueries }),
}));

vi.mock("react", () => ({
  useEffect: (effect: () => void | (() => void)) => {
    const cleanup = effect();
    if (typeof cleanup === "function") cleanup();
  },
}));

vi.mock("../../../api/clientApi", () => ({
  CLIENT_API_BASE: "/api/v1/client-web",
  clientApi: vi.fn(),
}));

describe("importWords api hooks", () => {
  it("submits import payloads and invalidates import and learning caches", () => {
    const mutation = useSubmitImportWords() as unknown as {
      mutationFn: (payload: { text_content: string; file_name: string }) => unknown;
      onSuccess: (data: { job: { id: number } }) => void;
    };

    mutation.mutationFn({ text_content: "carry on", file_name: "words.txt" });
    mutation.onSuccess({ job: { id: 9 } });

    expect(clientApi).toHaveBeenCalledWith("/imports", {
      method: "POST",
      body: JSON.stringify({ text_content: "carry on", file_name: "words.txt" }),
    });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: importWordsQueryKeys.all });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: [...importWordsQueryKeys.all, "job-items", 9] });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: learningWordsKey });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: settingsKey });
  });

  it("unbinds Google Doc and refreshes import/settings state", () => {
    const mutation = useUnbindImportGoogleDoc() as unknown as {
      mutationFn: () => unknown;
      onSuccess: () => void;
    };

    mutation.mutationFn();
    mutation.onSuccess();

    expect(clientApi).toHaveBeenCalledWith("/imports/google-doc-binding", { method: "DELETE" });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: settingsKey });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: importWordsQueryKeys.all });
  });

  it("builds paginated persistent import result queries", () => {
    const query = useImportItems(2, 50, "queued") as unknown as {
      placeholderData: symbol;
      queryFn: () => unknown;
      queryKey: readonly unknown[];
      retry: false;
    };

    expect(query.queryKey).toEqual(importWordsQueryKeys.items(2, 50, "queued"));
    expect(query.placeholderData).toBe(Symbol.for("keepPreviousData"));
    expect(query.retry).toBe(false);
    query.queryFn();
    expect(clientApi).toHaveBeenCalledWith("/imports/items?page=2&page_size=50&status_category=queued");
  });

  it("keeps legacy paginated import job result queries", () => {
    const query = useImportJobItems(9, 2, 50, "queued") as unknown as {
      enabled: boolean;
      placeholderData: symbol;
      queryFn: () => unknown;
      queryKey: readonly unknown[];
      retry: false;
    };

    expect(query.queryKey).toEqual(importWordsQueryKeys.jobItems(9, 2, 50, "queued"));
    expect(query.enabled).toBe(true);
    expect(query.placeholderData).toBe(Symbol.for("keepPreviousData"));
    expect(query.retry).toBe(false);
    query.queryFn();
    expect(clientApi).toHaveBeenCalledWith("/imports/9/items?page=2&page_size=50&status_category=queued");
  });

  it("disables import result queries without a job id", () => {
    const query = useImportJobItems(null, 1, 20, "all") as unknown as {
      enabled: boolean;
      refetchInterval: false;
    };

    expect(query.enabled).toBe(false);
  });

  it("subscribes to import job events and invalidates result caches on push", () => {
    const listeners = new Map<string, EventListener>();
    const close = vi.fn();
    const EventSourceMock = vi.fn(function EventSourceMock(this: { addEventListener: (event: string, listener: EventListener) => void; close: () => void }, url: string) {
      expect(url).toBe(`${CLIENT_API_BASE}/imports/events?job_id=9`);
      this.addEventListener = (event, listener) => listeners.set(event, listener);
      this.close = close;
    });
    vi.stubGlobal("EventSource", EventSourceMock);

    useImportJobEvents(9);

    expect(EventSourceMock).toHaveBeenCalledOnce();
    expect(close).toHaveBeenCalledOnce();
    listeners.get("items_changed")?.(new Event("items_changed"));
    listeners.get("completed")?.(new Event("completed"));

    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: [...importWordsQueryKeys.all, "job-items", 9] });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: learningWordsKey });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: settingsKey });
  });

  it("does not subscribe to import job events without a job id", () => {
    const EventSourceMock = vi.fn();
    vi.stubGlobal("EventSource", EventSourceMock);

    useImportJobEvents(null);

    expect(EventSourceMock).not.toHaveBeenCalled();
  });
});
