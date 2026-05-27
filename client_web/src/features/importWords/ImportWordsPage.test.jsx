import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ImportWordsPage } from "./ImportWordsPage";

const submitImport = {
  error: null,
  isPending: false,
  mutate: vi.fn(),
  reset: vi.fn(),
};

const unbindGoogleDoc = {
  error: null,
  isPending: false,
  mutate: vi.fn(),
};
const emptyImportResults = { items: [], total: 0, summary: null };
let importItemsResult = emptyImportResults;
let jobItemsResult = null;
let jobItemsError = null;
let jobItemsIsFetching = false;
let jobItemsIsPending = false;
let jobItemsIsPlaceholderData = false;
const importItemsEnabledCalls = [];
const importResultTable = vi.fn(() => <div data-testid="import-results" />);
let settingsResult = { profile: {} };

vi.mock("./api/importWordsApi", () => ({
  useImportItems: (_page, _pageSize, _statusCategory, enabled) => {
    importItemsEnabledCalls.push(enabled);
    return { data: importItemsResult, error: null, isFetching: false, isPending: false, isPlaceholderData: false };
  },
  useImportJobEvents: vi.fn(),
  useImportJobItems: () => ({
    data: jobItemsResult,
    error: jobItemsError,
    isFetching: jobItemsIsFetching,
    isPending: jobItemsIsPending,
    isPlaceholderData: jobItemsIsPlaceholderData,
  }),
  useSubmitImportWords: () => submitImport,
  useUnbindImportGoogleDoc: () => unbindGoogleDoc,
}));

vi.mock("../settings/api/settingsApi", () => ({
  useSettings: () => ({ data: settingsResult }),
}));

vi.mock("./components/ImportResultTable", () => ({
  ImportResultTable: (props) => importResultTable(props),
}));

describe("ImportWordsPage", () => {
  beforeEach(() => {
    submitImport.error = null;
    submitImport.isPending = false;
    submitImport.mutate.mockReset();
    submitImport.reset.mockReset();
    unbindGoogleDoc.error = null;
    unbindGoogleDoc.isPending = false;
    unbindGoogleDoc.mutate.mockReset();
    importItemsResult = emptyImportResults;
    jobItemsResult = null;
    jobItemsError = null;
    jobItemsIsFetching = false;
    jobItemsIsPending = false;
    jobItemsIsPlaceholderData = false;
    importItemsEnabledCalls.length = 0;
    importResultTable.mockClear();
    settingsResult = { profile: {} };
  });

  it("shows lookup-only import notice for restricted import mode", () => {
    settingsResult = {
      profile: {},
      subscription: { import_mode: "lookup_only" },
      google_doc_rescan_schedule: { hour: 9, weekdays: [0, 2, 4], interval_days: 3 },
    };

    render(
      <MemoryRouter initialEntries={["/import-words?job_id=7&page=1"]}>
        <ImportWordsPage />
      </MemoryRouter>,
    );

    expect(
      screen.getByText(
        /Нові слова з Google Doc синхронізуються за графіком: Понеділок \/ Середа \/ Пʼятниця о 09:00\. Для глибшого AI-аналізу можна/,
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "оновити тариф" })).toHaveAttribute(
      "href",
      "/plans?return_to=%2Fimport-words%3Fjob_id%3D7%26page%3D1",
    );
  });

  it("hides lookup-only import notice when smart import is available", () => {
    settingsResult = {
      profile: {},
      subscription: { import_mode: "ai_new_words" },
    };

    render(
      <MemoryRouter>
        <ImportWordsPage />
      </MemoryRouter>,
    );

    expect(screen.queryByText(/Розумний імпорт зараз недоступний/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Google Doc синхронізується протягом години/)).not.toBeInTheDocument();
  });

  it("shows Google Doc binding instructions and sharing help before the URL field", () => {
    settingsResult = {
      profile: {},
      google_doc_rescan_schedule: { hour: 9, weekdays: [0, 2, 4], interval_days: 3 },
    };

    render(
      <MemoryRouter>
        <ImportWordsPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("Як привʼязати Google Doc")).toBeInTheDocument();
    expect(screen.getByText("1. Створіть Google Doc зі словами для навчання.")).toBeInTheDocument();
    expect(screen.getByText(/Після привʼязки документ синхронізуватиметься за графіком: Понеділок \/ Середа \/ Пʼятниця о 09:00\./)).toBeInTheDocument();
    expect(screen.getByText("Формат записів:")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: "як відкрити доступ" }));

    const dialog = screen.getByRole("dialog", { name: "Як відкрити доступ до Google Doc за посиланням" });
    const shareHelpItems = within(dialog).getAllByRole("listitem");
    expect(shareHelpItems[0]).toHaveTextContent('1. Натисніть "Поділитися" у правому верхньому куті документа.');
    expect(shareHelpItems[1]).toHaveTextContent('2. У блоці загального доступу виберіть "Усі, хто має посилання".');
    expect(shareHelpItems[2]).toHaveTextContent('3. Залиште роль "Читач".');
    expect(within(dialog).getByText('"Поділитися"').tagName).toBe("STRONG");
    expect(within(dialog).getByText('"Усі, хто має посилання"').tagName).toBe("STRONG");
    expect(within(dialog).getByText('"Читач"').tagName).toBe("STRONG");
    expect(within(dialog).getByText("4. Скопіюйте посилання й поверніться в CronoLex.")).toBeInTheDocument();
  });

  it("shows supported Google Doc entry formats in a help dialog", () => {
    render(
      <MemoryRouter>
        <ImportWordsPage />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("link", { name: "приклади" }));

    const dialog = screen.getByRole("dialog", { name: "Підтримувані формати записів" });
    expect(within(dialog).getByText(/CronoLex читає окремі слова, phrasal verbs і короткі навчальні вирази/)).toBeInTheDocument();
    expect(within(dialog).getByText("1. Окремі рядки")).toBeInTheDocument();
    expect(within(dialog).getByText("2. Кілька записів через кому")).toBeInTheDocument();
    expect(within(dialog).getByText("3. Запис із перекладом")).toBeInTheDocument();
    expect(within(dialog).getByText("4. Нумерований список")).toBeInTheDocument();
    expect(within(dialog).getByText(/word, take over, scenic view/)).toBeInTheDocument();
    expect(within(dialog).getByText(/1\. word - переклад/)).toBeInTheDocument();
    expect(within(dialog).getByText(/Переклад після дефіса використовується тільки як підказка/)).toBeInTheDocument();
  });

  it("shows paid post-upgrade rescan notice only while rescan is queued", () => {
    settingsResult = {
      profile: {},
      subscription: { import_mode: "ai_new_words" },
      google_doc_post_upgrade_rescan_pending: true,
    };

    render(
      <MemoryRouter>
        <ImportWordsPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("Після оплати тарифу Google Doc синхронізується протягом години.")).toBeInTheDocument();
  });

  it("shows the bound Google Doc panel immediately after import submit", async () => {
    render(
      <MemoryRouter>
        <ImportWordsPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Посилання на Google Doc"), {
      target: {
        value: "https://docs.google.com/document/d/1hjfnAc6_IRoasNmtjiPp-8ZKk878HN39-RDHkn4KG7U/edit?tab=t.0",
      },
    });
    fireEvent.click(screen.getByRole("button", { name: /Імпорт/ }));

    expect(screen.getByText("Google Doc прив'язано")).toBeInTheDocument();
    expect(screen.getByText("https://docs.google.com/document/d/1hjf...KG7U/...")).toBeInTheDocument();
    expect(screen.queryByLabelText("Посилання на Google Doc")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Імпорт/ })).toBeDisabled();
    expect(submitImport.mutate).toHaveBeenCalledWith(
      {
        source_url: "https://docs.google.com/document/d/1hjfnAc6_IRoasNmtjiPp-8ZKk878HN39-RDHkn4KG7U/edit?tab=t.0",
        text_content: null,
        file_name: null,
      },
      expect.objectContaining({
        onError: expect.any(Function),
        onSuccess: expect.any(Function),
      }),
    );
  });

  it("keeps Google Doc binding instructions visible when a document is already bound", () => {
    settingsResult = {
      profile: {
        import_google_doc_id: "1hjfnAc6_IRoasNmtjiPp-8ZKk878HN39-RDHkn4KG7U",
      },
      google_doc_rescan_schedule: { hour: 9, weekdays: [0, 2, 4], interval_days: 3 },
    };

    render(
      <MemoryRouter>
        <ImportWordsPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("Як привʼязати Google Doc")).toBeInTheDocument();
    expect(screen.getByText(/Після привʼязки документ синхронізуватиметься за графіком/)).toBeInTheDocument();
    expect(screen.getByText("Google Doc прив'язано")).toBeInTheDocument();
    expect(screen.queryByLabelText("Посилання на Google Doc")).not.toBeInTheDocument();
  });

  it("requires confirmation before unbinding the bound Google Doc", async () => {
    settingsResult = {
      profile: {
        import_google_doc_id: "1hjfnAc6_IRoasNmtjiPp-8ZKk878HN39-RDHkn4KG7U",
      },
    };

    render(
      <MemoryRouter>
        <ImportWordsPage />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Відв'язати" }));

    expect(unbindGoogleDoc.mutate).not.toHaveBeenCalled();
    let dialog = screen.getByRole("dialog", { name: "Відв'язати Google Doc?" });
    expect(dialog).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole("button", { name: "Скасувати" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(unbindGoogleDoc.mutate).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Відв'язати" }));
    dialog = screen.getByRole("dialog", { name: "Відв'язати Google Doc?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Відв'язати" }));

    expect(unbindGoogleDoc.mutate).toHaveBeenCalledTimes(1);
  });

  it("shows the Google Doc sync schedule only in the guide", () => {
    settingsResult = {
      profile: {
        import_google_doc_id: "1hjfnAc6_IRoasNmtjiPp-8ZKk878HN39-RDHkn4KG7U",
      },
      google_doc_rescan_schedule: { hour: 9, weekdays: [0, 2, 4], interval_days: 3 },
    };

    render(
      <MemoryRouter>
        <ImportWordsPage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/Після привʼязки документ синхронізуватиметься за графіком: Понеділок \/ Середа \/ Пʼятниця о 09:00\./)).toBeInTheDocument();
    expect(screen.queryByText(/нові слова додаватимуться автоматично/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Раз на 3 дні/)).not.toBeInTheDocument();
  });

  it("keeps summary counters from the API while live rows animate", () => {
    jobItemsResult = {
      items: [
        { id: 1, status_category: "added" },
        { id: 2, status_category: "added" },
      ],
      total: 161,
      summary: { added: 57, queued: 95, rejected: 9, processing: 0 },
    };

    render(
      <MemoryRouter initialEntries={["/import-words?job_id=7&page=1&page_size=20&status_category=all"]}>
        <ImportWordsPage />
      </MemoryRouter>,
    );

    const latestProps = importResultTable.mock.calls.at(-1)?.[0];

    expect(latestProps.summary).toEqual({ added: 57, queued: 95, rejected: 9, processing: 0 });
    expect(latestProps.total).toBe(161);
  });

  it("does not show table loading for background polling when current data is present", () => {
    jobItemsResult = {
      items: [{ id: 1, status_category: "added" }],
      total: 1,
      summary: { added: 1, queued: 0, rejected: 0, processing: 0 },
    };
    jobItemsIsFetching = true;

    render(
      <MemoryRouter initialEntries={["/import-words?job_id=7&page=1&page_size=20&status_category=all"]}>
        <ImportWordsPage />
      </MemoryRouter>,
    );

    expect(importResultTable.mock.calls.at(-1)?.[0].loading).toBe(false);
  });

  it("shows table loading while rendering placeholder data for a page transition", () => {
    jobItemsResult = {
      items: [{ id: 1, status_category: "added" }],
      total: 50,
      summary: { added: 50, queued: 0, rejected: 0, processing: 0 },
    };
    jobItemsIsFetching = true;
    jobItemsIsPlaceholderData = true;

    render(
      <MemoryRouter initialEntries={["/import-words?job_id=7&page=2&page_size=20&status_category=all"]}>
        <ImportWordsPage />
      </MemoryRouter>,
    );

    expect(importResultTable.mock.calls.at(-1)?.[0].loading).toBe(true);
    expect(importResultTable.mock.calls.at(-1)?.[0].rows).toEqual([{ id: 1, status_category: "added" }]);
  });

  it("drops stale import job ids after the backend reports a missing job", async () => {
    jobItemsError = new Error("Import job not found");

    render(
      <MemoryRouter initialEntries={["/import-words?job_id=777&page=1&page_size=20&status_category=all"]}>
        <ImportWordsPage />
      </MemoryRouter>,
    );

    expect(await screen.findByTestId("import-results")).toBeInTheDocument();
    await waitFor(() => expect(importItemsEnabledCalls).toContain(true));
    expect(screen.queryByText("Import job not found")).not.toBeInTheDocument();
  });
});
