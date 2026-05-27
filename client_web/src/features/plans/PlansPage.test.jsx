import { act, fireEvent, render, screen } from "@testing-library/react";
import { useLocation, MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { normalizePlanReturnTo, PlansPage } from "./PlansPage";

const mockState = vi.hoisted(() => ({
  paymentStatusData: null,
  paymentHistoryData: { items: [] },
  checkoutError: null,
  offerText: "Offer text",
}));

const mutate = vi.fn();
const checkoutMutate = vi.fn();
const plansRefetch = vi.fn();
const paymentHistoryRefetch = vi.fn();
const defaultBilling = {
  enabled_period_months: [1, 3, 6, 12],
  plan_prices_uah: { premium: { 1: 10, 3: 30 }, premium_plus: { 1: 20 } },
  frontend_poll_interval_seconds: 10,
  frontend_poll_timeout_seconds: 60,
};
const defaultPlans = [
  { key: "free", title: "Free", is_current: false, feature_keys: [] },
  {
    key: "premium",
    title: "Premium",
    is_current: false,
    feature_keys: ["ai_new_words"],
    order_previews: { 3: { amount_minor: 3000 } },
  },
];
const plansData = {
  current_plan_key: "free",
  billing: structuredClone(defaultBilling),
  plans: structuredClone(defaultPlans),
};

vi.mock("../../shared/i18n/clientI18n", () => ({
  useClientI18n: () => ({
    t: (key, vars = {}) => ({
      updatePlan: "Оновити тариф",
      updatePlanSubtitle: "Оберіть тариф",
      selectPlan: "Обрати",
      currentPlan: "Поточний тариф",
      downgradeAfterCurrentPeriod: "Доступно після завершення поточного періоду",
      freeAfterCurrentPeriod: "На Free можна перейти після завершення платного тарифу",
      fromMonthlyPrice: "від 10 грн/міс.",
      loading: "Завантаження",
      monthlyPrice: "10 грн/міс.",
      notAvailable: "Недоступно",
      billingOfferAccept: "Я погоджуюся",
      billingOfferRead: "прочитати",
      billingPeriod: "Період",
      doubleTimeForProjectSupportText: "Вдячні за підтримку. Подвоєний час підписки.",
      cancel: "Скасувати",
      close: "Закрити",
      pay: "Оплатити",
      paymentActivated: "Вуаля, тариф активовано",
      paymentHistory: "Історія платежів",
      paymentHistoryEmpty: "Платежів ще немає",
      paymentRedirectingMessage: "Не закривайте сторінку. Зараз відкриємо безпечну сторінку оплати.",
      paymentRedirectingTitle: "Переходимо до оплати",
      paymentServiceUnavailable: `Вибачте, сервіс оплати тимчасово недоступний.${vars.detail ? ` ${vars.detail}` : ""}`,
      paymentTerminalMaintenance: "Вибачте, платіжний термінал зараз на технічному обслуговуванні. Оплата недоступна з 23:30 до 00:30. Будь ласка, зайдіть пізніше.",
      paymentStatusCreated: "Очікує оплату",
      paymentStatusExpired: "Час оплати минув",
      paymentStatusFailure: "Не вдалося оплатити",
      paymentStatusInvoiceCreated: "Очікує оплату",
      paymentStatusProcessing: "Оплата обробляється",
      paymentStatusReversed: "Платіж скасовано",
      receipt: "Чек",
      receiptPending: "Чек формується",
      receiptStored: "Чек збережено",
      renewPlan: "Продовжити",
      paymentStatusSuccess: "Успішно",
      paymentStillProcessingMessage: "Платіж все ще обробляється. Ми повідомимо результат у Telegram, щойно дізнаємося його.",
      paymentStillProcessingTitle: "Платіж все ще обробляється",
      subscriptionRemainingDays: "Залишилось: 10 дн.",
      subscriptionValidUntil: "Тариф діє до 5/14/2026.",
      paymentSuccess: "Оплата успішна",
      paymentWaitingForInfo: "Очікуємо інформацію про платіж.",
      paymentWaitingTitle: "Очікуємо інформацію про платіж",
      totalForPeriod: "Разом 30 грн",
      upgradePayment: "Доплата 5 грн",
    })[key] || key,
  }),
}));

vi.mock("./api/plansApi", () => ({
  usePlans: () => ({
    data: plansData,
    isError: false,
    isLoading: false,
    refetch: plansRefetch,
  }),
  useSelectPlan: () => ({
    error: null,
    isError: false,
    isPending: false,
    isSuccess: false,
    mutate,
  }),
  useBillingOffer: () => ({
    data: { offer_text: mockState.offerText, offer_text_hash: "abc123".padEnd(64, "0") },
    isLoading: false,
  }),
  useCreateBillingCheckout: () => ({
    error: mockState.checkoutError,
    isError: Boolean(mockState.checkoutError),
    isPending: false,
    mutate: checkoutMutate,
  }),
  useBillingPaymentStatus: () => ({
    data: mockState.paymentStatusData,
    isError: false,
    isLoading: false,
  }),
  useBillingPaymentHistory: () => ({
    data: mockState.paymentHistoryData,
    isError: false,
    isLoading: false,
    refetch: paymentHistoryRefetch,
  }),
}));

function LocationProbe() {
  const location = useLocation();
  return <span data-testid="location">{`${location.pathname}${location.search}`}</span>;
}

describe("PlansPage", () => {
  beforeEach(() => {
    vi.useRealTimers();
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-05-06T10:00:00.000Z"));
    mutate.mockReset();
    checkoutMutate.mockReset();
    plansRefetch.mockReset();
    paymentHistoryRefetch.mockReset();
    mockState.paymentStatusData = null;
    mockState.paymentHistoryData = { items: [] };
    mockState.checkoutError = null;
    mockState.offerText = "Offer text";
    plansData.billing = structuredClone(defaultBilling);
    plansData.plans = structuredClone(defaultPlans);
    delete plansData.subscription;
    window.sessionStorage.clear();
  });

  it("returns to a safe source page after selecting a free plan", () => {
    render(
      <MemoryRouter initialEntries={["/plans?return_to=%2Fimport-words%3Fjob_id%3D7%26page%3D1"]}>
        <Routes>
          <Route path="/plans" element={<><PlansPage /><LocationProbe /></>} />
          <Route path="/import-words" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getAllByRole("button", { name: "Обрати" })[0]);
    const onSuccess = mutate.mock.calls[0][1].onSuccess;
    act(() => {
      onSuccess();
    });

    expect(mutate).toHaveBeenCalledWith("free", expect.objectContaining({ onSuccess: expect.any(Function) }));
    expect(screen.getByTestId("location")).toHaveTextContent("/import-words?job_id=7&page=1");
  });

  it("opens checkout modal for paid plan with period and amount", () => {
    render(
      <MemoryRouter initialEntries={["/plans?return_to=%2Flearning"]}>
        <Routes>
          <Route path="/plans" element={<PlansPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getAllByRole("button", { name: "Обрати" })[1]);
    fireEvent.mouseDown(screen.getByLabelText("Період"));
    fireEvent.click(screen.getByRole("option", { name: "3 міс." }));
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Оплатити" }));

    expect(screen.getByText("30 грн · 3 міс.")).toBeInTheDocument();
    expect(checkoutMutate).toHaveBeenCalledWith(
      {
        plan_key: "premium",
        period_months: 3,
        offer_accepted: true,
        offer_text_hash: "abc123".padEnd(64, "0"),
        source_path: "/learning",
      },
      expect.objectContaining({ onError: expect.any(Function), onSuccess: expect.any(Function) }),
    );
  });

  it("shows double time support block in checkout only when enabled", () => {
    plansData.billing = {
      ...structuredClone(defaultBilling),
      double_time_for_project_support_enabled: true,
      double_time_for_project_support_text: "Вдячні вам за готовність підтримати проєкт монетою на ранньому етапі тестування. За будь-яку оплату ви отримаєте подвоєний час підписки.",
    };

    render(
      <MemoryRouter initialEntries={["/plans"]}>
        <Routes>
          <Route path="/plans" element={<PlansPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.queryByText(/подвоєний час підписки/)).not.toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Обрати" })[1]);

    expect(screen.getByText(/подвоєний час підписки/)).toBeInTheDocument();
  });

  it("shows granted period in checkout when double time support is enabled", () => {
    plansData.billing = {
      ...structuredClone(defaultBilling),
      double_time_for_project_support_enabled: true,
    };
    plansData.plans = [
      defaultPlans[0],
      {
        ...defaultPlans[1],
        order_previews: { 3: { amount_minor: 3000, granted_period_months: 6 } },
      },
    ];

    render(
      <MemoryRouter initialEntries={["/plans"]}>
        <Routes>
          <Route path="/plans" element={<PlansPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getAllByRole("button", { name: "Обрати" })[1]);
    fireEvent.mouseDown(screen.getByLabelText("Період"));
    fireEvent.click(screen.getByRole("option", { name: "3 міс." }));

    expect(screen.getByText("30 грн · 3 міс. · нараховано 6 міс.")).toBeInTheDocument();
  });

  it("blocks the page with payment overlay until checkout redirects or fails", () => {
    render(
      <MemoryRouter initialEntries={["/plans"]}>
        <Routes>
          <Route path="/plans" element={<PlansPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getAllByRole("button", { name: "Обрати" })[1]);
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Оплатити" }));

    expect(screen.getByText("Переходимо до оплати")).toBeInTheDocument();
    expect(screen.getByText("Не закривайте сторінку. Зараз відкриємо безпечну сторінку оплати.")).toBeInTheDocument();

    act(() => {
      checkoutMutate.mock.calls[0][1].onError();
    });

    expect(screen.queryByText("Переходимо до оплати")).not.toBeInTheDocument();
  });

  it("shows payment terminal maintenance instead of checkout details", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-06T20:45:00.000Z"));
    plansData.billing = {
      ...structuredClone(defaultBilling),
      billing_provider: "monobank",
    };

    render(
      <MemoryRouter initialEntries={["/plans"]}>
        <Routes>
          <Route path="/plans" element={<PlansPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getAllByRole("button", { name: "Обрати" })[1]);

    expect(screen.getByText("Вибачте, платіжний термінал зараз на технічному обслуговуванні. Оплата недоступна з 23:30 до 00:30. Будь ласка, зайдіть пізніше.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Період")).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Оплатити" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Закрити" })).toBeInTheDocument();
  });

  it("does not show payment terminal maintenance state for instant provider", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-06T20:45:00.000Z"));
    plansData.billing = {
      ...structuredClone(defaultBilling),
      billing_provider: "instant",
      monobank_mode: "disabled",
    };

    render(
      <MemoryRouter initialEntries={["/plans"]}>
        <Routes>
          <Route path="/plans" element={<PlansPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getAllByRole("button", { name: "Обрати" })[1]);

    expect(screen.queryByText(/платіжний термінал зараз на технічному обслуговуванні/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Період")).toBeInTheDocument();
    expect(screen.getByRole("checkbox")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Оплатити" })).toBeInTheDocument();
  });

  it("keeps the period total out of plan cards", () => {
    render(
      <MemoryRouter initialEntries={["/plans"]}>
        <Routes>
          <Route path="/plans" element={<PlansPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.queryByText("Разом 30 грн")).not.toBeInTheDocument();
    expect(screen.getByText("від 10 грн/міс.")).toBeInTheDocument();
  });

  it("shows checkout service errors inside the payment dialog", () => {
    mockState.checkoutError = new Error("Monobank checkout is disabled");

    render(
      <MemoryRouter initialEntries={["/plans"]}>
        <Routes>
          <Route path="/plans" element={<PlansPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getAllByRole("button", { name: "Обрати" })[1]);

    expect(screen.getByText(/Вибачте, сервіс оплати тимчасово недоступний\./i)).toBeInTheDocument();
    expect(screen.queryByText(/Monobank/i)).not.toBeInTheDocument();
  });

  it("does not rewrite arbitrary monobank-like identifiers in checkout errors", () => {
    mockState.checkoutError = new Error("MONOBANK_TOKEN_TEST is missing");

    render(
      <MemoryRouter initialEntries={["/plans"]}>
        <Routes>
          <Route path="/plans" element={<PlansPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getAllByRole("button", { name: "Обрати" })[1]);

    expect(screen.getByText("Вибачте, сервіс оплати тимчасово недоступний. MONOBANK_TOKEN_TEST is missing")).toBeInTheDocument();
    expect(screen.queryByText(/payment provider checkout is disabled/i)).not.toBeInTheDocument();
  });

  it("renders billing offer text as markdown", () => {
    mockState.offerText = "## Публічна оферта\n\n- **Оплата** підтверджує згоду";

    render(
      <MemoryRouter initialEntries={["/plans"]}>
        <Routes>
          <Route path="/plans" element={<PlansPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getAllByRole("button", { name: "Обрати" })[1]);
    fireEvent.click(screen.getByRole("button", { name: "прочитати" }));

    expect(screen.getByRole("heading", { level: 2, name: "Публічна оферта" })).toBeInTheDocument();
    expect(screen.getByRole("listitem")).toHaveTextContent("Оплата підтверджує згоду");
  });

  it("rejects external or protocol-relative return targets", () => {
    expect(normalizePlanReturnTo("https://example.com/import-words")).toBe("");
    expect(normalizePlanReturnTo("//example.com/import-words")).toBe("");
    expect(normalizePlanReturnTo("/import-words?page=1")).toBe("/import-words?page=1");
  });

  it("closes check-payment overlay after terminal failure", async () => {
    vi.useFakeTimers();
    mockState.paymentStatusData = {
      payment: { id: 7, source_path: "/learning" },
      status: { is_terminal: true, is_success: false, is_failure: true, message: "Declined" },
    };

    render(
      <MemoryRouter initialEntries={["/plans?payment_id=7&check_payment=true"]}>
        <Routes>
          <Route path="/plans" element={<><PlansPage /><LocationProbe /></>} />
        </Routes>
      </MemoryRouter>,
    );

    await act(async () => {});
    expect(screen.getAllByText("Declined").length).toBeGreaterThan(0);
    await act(async () => {
      vi.advanceTimersByTime(2100);
    });
    expect(screen.getByTestId("location")).toHaveTextContent("/plans");
  });

  it("refetches plans and returns after successful check-payment activation", async () => {
    vi.useFakeTimers();
    mockState.paymentStatusData = {
      payment: { id: 7, source_path: "/learning" },
      status: { is_terminal: true, is_success: true, is_failure: false },
    };

    render(
      <MemoryRouter initialEntries={["/plans?payment_id=7&check_payment=true&return_to=%2Fimport-words"]}>
        <Routes>
          <Route path="/plans" element={<><PlansPage /><LocationProbe /></>} />
          <Route path="/learning" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    );

    await act(async () => {});
    expect(screen.getByText("Оплата успішна")).toBeInTheDocument();
    expect(screen.getAllByText("Вуаля, тариф активовано").length).toBeGreaterThan(0);
    await act(async () => {
      vi.advanceTimersByTime(2100);
    });
    expect(plansRefetch).toHaveBeenCalled();
    expect(paymentHistoryRefetch).toHaveBeenCalled();
    expect(screen.getByTestId("location")).toHaveTextContent("/learning");
  });

  it("keeps users on plans after check-payment timeout", async () => {
    vi.useFakeTimers();

    render(
      <MemoryRouter initialEntries={["/plans?payment_id=7&check_payment=true"]}>
        <Routes>
          <Route path="/plans" element={<><PlansPage /><LocationProbe /></>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Очікуємо інформацію про платіж")).toBeInTheDocument();
    await act(async () => {
      vi.advanceTimersByTime(60_000);
    });
    expect(screen.getByText("Платіж все ще обробляється")).toBeInTheDocument();
    await act(async () => {
      vi.advanceTimersByTime(2100);
    });
    expect(screen.getByTestId("location")).toHaveTextContent("/plans");
  });

  it("renders human payment history statuses", () => {
    mockState.paymentHistoryData = {
      items: [
        {
          id: 1,
          plan_key: "premium",
          amount_uah: 10,
          period_months: 1,
          status: "invoice_created",
          created: "2026-05-06T10:00:00Z",
          receipts: [],
        },
        {
          id: 2,
          plan_key: "premium",
          amount_uah: 10,
          period_months: 1,
          granted_period_months: 2,
          status: "success",
          created: "2026-05-06T10:00:00Z",
          promotion_label: "Двойное время за поддержку проекта",
          receipts: [],
        },
      ],
    };

    render(
      <MemoryRouter initialEntries={["/plans"]}>
        <Routes>
          <Route path="/plans" element={<PlansPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Очікує оплату")).toBeInTheDocument();
    expect(screen.getByText("Успішно")).toBeInTheDocument();
    expect(screen.getByText("premium · 10 грн · 1 міс. · нараховано 2 міс.")).toBeInTheDocument();
    expect(screen.getByText("Двойное время за поддержку проекта")).toBeInTheDocument();
    expect(screen.getAllByText(/06\.05\.2026/)).toHaveLength(2);
    expect(screen.queryByText("paymentStatusInvoiceCreated")).not.toBeInTheDocument();
  });

  it("shows stored receipt only for done file receipts", () => {
    mockState.paymentHistoryData = {
      items: [
        {
          id: 1,
          plan_key: "premium",
          amount_uah: 10,
          period_months: 1,
          status: "success",
          created: "2026-05-06T10:00:00Z",
          receipts: [{ id: 11, status: "unavailable", has_file: true, tax_url: null }],
        },
        {
          id: 2,
          plan_key: "premium",
          amount_uah: 10,
          period_months: 1,
          status: "success",
          created: "2026-05-06T10:00:00Z",
          receipts: [{ id: 12, status: "done", has_file: true, tax_url: null }],
        },
      ],
    };

    render(
      <MemoryRouter initialEntries={["/plans"]}>
        <Routes>
          <Route path="/plans" element={<PlansPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getAllByText("Чек збережено")).toHaveLength(1);
  });

  it("shows checkbox receipt link even while fiscal check is pending", () => {
    mockState.paymentHistoryData = {
      items: [
        {
          id: 1,
          plan_key: "premium",
          amount_uah: 10,
          period_months: 1,
          status: "success",
          created: "2026-05-06T10:00:00Z",
          receipts: [
            {
              id: 11,
              status: "new",
              has_file: false,
              tax_url: "https://check.checkbox.ua/55a1d9f7-7475-4088-86d2-2132c2261e71",
            },
            {
              id: 12,
              status: "done",
              has_file: false,
              tax_url: "https://check.checkbox.ua/55a1d9f7-7475-4088-86d2-2132c2261e71",
            },
          ],
        },
      ],
    };

    render(
      <MemoryRouter initialEntries={["/plans"]}>
        <Routes>
          <Route path="/plans" element={<PlansPage />} />
        </Routes>
      </MemoryRouter>,
    );

    const receiptLinks = screen.getAllByRole("link", { name: "Чек" });
    expect(receiptLinks).toHaveLength(1);
    const receiptLink = receiptLinks[0];
    expect(receiptLink).toHaveAttribute(
      "href",
      "https://check.checkbox.ua/55a1d9f7-7475-4088-86d2-2132c2261e71",
    );
    expect(receiptLink).toHaveAttribute("target", "_blank");
  });

  it("shows pending receipt state instead of tax cabinet links", () => {
    mockState.paymentHistoryData = {
      items: [
        {
          id: 1,
          plan_key: "premium",
          amount_uah: 10,
          period_months: 1,
          status: "success",
          created: "2026-05-06T10:00:00Z",
          receipts: [
            {
              id: 11,
              receipt_type: "fiscal_check",
              status: "done",
              has_file: false,
              tax_url: "https://cabinet.tax.gov.ua/cashregs/check?id=long",
            },
          ],
        },
      ],
    };

    render(
      <MemoryRouter initialEntries={["/plans"]}>
        <Routes>
          <Route path="/plans" element={<PlansPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.queryByRole("link", { name: "Чек" })).not.toBeInTheDocument();
    expect(screen.getByText("Чек формується")).toBeInTheDocument();
  });

  it("shows subscription remainder and disables paid downgrade until the period ends", () => {
    plansData.subscription = {
      plan_key: "premium_plus",
      end: "2026-05-14T12:00:00Z",
      remaining_seconds: 864000,
      remaining_days: 10,
    };
    plansData.plans = [
      { key: "free", title: "Free", is_current: false, feature_keys: [] },
      {
        key: "premium",
        title: "Premium",
        is_current: false,
        feature_keys: [],
        availability: { can_checkout: false, reason: "downgrade_after_current_period" },
      },
      { key: "premium_plus", title: "Premium +", is_current: true, feature_keys: [] },
    ];

    render(
      <MemoryRouter initialEntries={["/plans"]}>
        <Routes>
          <Route path="/plans" element={<PlansPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText(/Тариф діє до/)).toBeInTheDocument();
    expect(screen.getByText("Доступно після завершення поточного періоду")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Недоступно" })).toHaveLength(2);
  });

  it("disables free downgrade while a paid subscription is active", () => {
    plansData.subscription = {
      plan_key: "premium",
      end: "2027-05-06T12:00:00Z",
      remaining_seconds: 31536000,
      remaining_days: 365,
    };
    plansData.plans = [
      { key: "free", title: "Free", is_current: false, feature_keys: [] },
      { key: "premium", title: "Premium", is_current: true, feature_keys: [] },
    ];

    render(
      <MemoryRouter initialEntries={["/plans"]}>
        <Routes>
          <Route path="/plans" element={<PlansPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("На Free можна перейти після завершення платного тарифу")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Недоступно" })).toBeDisabled();
  });

  it("allows renewing the current paid plan", () => {
    plansData.subscription = {
      plan_key: "premium",
      end: "2027-05-06T12:00:00Z",
      remaining_seconds: 31536000,
      remaining_days: 365,
    };
    plansData.billing = {
      ...structuredClone(defaultBilling),
      enabled_period_months: [1],
      plan_prices_uah: { premium: { 1: 10 } },
    };
    plansData.plans = [
      { key: "free", title: "Free", is_current: false, feature_keys: [] },
      {
        key: "premium",
        title: "Premium",
        is_current: true,
        feature_keys: [],
        order_previews: { 1: { kind: "renewal", amount_minor: 1000 } },
      },
    ];

    render(
      <MemoryRouter initialEntries={["/plans"]}>
        <Routes>
          <Route path="/plans" element={<PlansPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Продовжити" }));
    fireEvent.click(screen.getByRole("checkbox"));
    expect(screen.getByText("10 грн · 1 міс.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Оплатити" }));

    expect(checkoutMutate).toHaveBeenCalledWith(
      {
        plan_key: "premium",
        period_months: 1,
        offer_accepted: true,
        offer_text_hash: "abc123".padEnd(64, "0"),
        source_path: null,
      },
      expect.objectContaining({ onError: expect.any(Function), onSuccess: expect.any(Function) }),
    );
  });
});
