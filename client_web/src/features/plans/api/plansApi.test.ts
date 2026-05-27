import { describe, expect, it, vi } from "vitest";

import { clientApi } from "../../../api/clientApi";
import { settingsKey } from "../../settings/api/settingsApi";
import {
  plansKey,
  useBillingOffer,
  useBillingPaymentHistory,
  useBillingPaymentStatus,
  useCreateBillingCheckout,
  usePlans,
  useSelectPlan,
} from "./plansApi";

const invalidateQueries = vi.fn();
const useMutationMock = vi.fn((config) => config);
const useQueryMock = vi.fn((config) => config);

vi.mock("@tanstack/react-query", () => ({
  useMutation: (config: unknown) => useMutationMock(config),
  useQuery: (config: unknown) => useQueryMock(config),
  useQueryClient: () => ({ invalidateQueries }),
}));

vi.mock("../../../api/clientApi", () => ({
  clientApi: vi.fn(),
}));

describe("plans api hooks", () => {
  it("builds the plans query", () => {
    const query = usePlans() as unknown as { queryFn: () => unknown; queryKey: readonly string[] };

    expect(query.queryKey).toEqual(plansKey);
    query.queryFn();

    expect(clientApi).toHaveBeenCalledWith("/plans");
  });

  it("selects a plan and refreshes plan/settings state", () => {
    const mutation = useSelectPlan() as unknown as { mutationFn: (planKey: string) => unknown; onSuccess: () => void };

    mutation.mutationFn("premium_plus");
    mutation.onSuccess();

    expect(clientApi).toHaveBeenCalledWith("/plans/select", {
      method: "POST",
      body: JSON.stringify({ plan_key: "premium_plus" }),
    });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: plansKey });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: settingsKey });
  });

  it("loads offer text", () => {
    const query = useBillingOffer() as unknown as { queryFn: () => unknown; queryKey: readonly string[] };

    query.queryFn();

    expect(query.queryKey).toEqual(["billing", "offer"]);
    expect(clientApi).toHaveBeenCalledWith("/billing/offer");
  });

  it("creates billing checkout", () => {
    const mutation = useCreateBillingCheckout() as unknown as {
      mutationFn: (payload: { plan_key: string; period_months: number; offer_accepted: boolean; offer_text_hash: string }) => unknown;
    };

    mutation.mutationFn({ plan_key: "premium", period_months: 3, offer_accepted: true, offer_text_hash: "hash" });

    expect(clientApi).toHaveBeenCalledWith("/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ plan_key: "premium", period_months: 3, offer_accepted: true, offer_text_hash: "hash" }),
    });
  });

  it("polls payment status until terminal state", () => {
    const query = useBillingPaymentStatus(7, 10) as unknown as {
      queryFn: () => unknown;
      queryKey: readonly unknown[];
      refetchInterval: (query: { state: { data: unknown } }) => false | number;
    };

    query.queryFn();

    expect(query.queryKey).toEqual(["billing", "payment-status", 7]);
    expect(clientApi).toHaveBeenCalledWith("/billing/payments/7/status");
    expect(query.refetchInterval({ state: { data: { status: { is_terminal: false } } } })).toBe(10000);
    expect(query.refetchInterval({ state: { data: { status: { is_terminal: false, should_stop_polling: true } } } })).toBe(false);
    expect(query.refetchInterval({ state: { data: { status: { is_terminal: true } } } })).toBe(false);
  });

  it("can ignore backend stop flag for check-payment overlay polling", () => {
    const query = useBillingPaymentStatus(7, 10, true, false) as unknown as {
      refetchInterval: (query: { state: { data: unknown } }) => false | number;
    };

    expect(query.refetchInterval({ state: { data: { status: { is_terminal: false, should_stop_polling: true } } } })).toBe(10000);
  });

  it("loads payment history", () => {
    const query = useBillingPaymentHistory() as unknown as { queryFn: () => unknown; queryKey: readonly unknown[] };

    query.queryFn();

    expect(query.queryKey).toEqual(["billing", "payments"]);
    expect(clientApi).toHaveBeenCalledWith("/billing/payments?page=1&page_size=20");
  });
});
