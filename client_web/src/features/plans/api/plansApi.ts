import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { clientApi } from "../../../api/clientApi";
import { settingsKey } from "../../settings/api/settingsApi";

export const plansKey = ["plans"] as const;

type BillingPaymentStatusResponse = {
  status?: {
    is_terminal?: boolean;
    is_success?: boolean;
    should_stop_polling?: boolean;
  };
};

export function usePlans() {
  return useQuery({ queryKey: plansKey, queryFn: () => clientApi("/plans") });
}

export function useSelectPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (planKey: string) => clientApi("/plans/select", { method: "POST", body: JSON.stringify({ plan_key: planKey }) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: plansKey });
      queryClient.invalidateQueries({ queryKey: settingsKey });
    },
  });
}

export function useBillingOffer(enabled = true) {
  return useQuery({ queryKey: ["billing", "offer"], queryFn: () => clientApi("/billing/offer"), enabled });
}

export function useCreateBillingCheckout() {
  return useMutation({
    mutationFn: (payload: { plan_key: string; period_months: number; offer_accepted: boolean; offer_text_hash: string; source_path?: string | null }) => (
      clientApi("/billing/checkout", { method: "POST", body: JSON.stringify(payload) })
    ),
  });
}

export function useBillingPaymentStatus(
  paymentId: number | null,
  intervalSeconds: number,
  enabled = true,
  stopOnServerTimeout = true,
) {
  return useQuery({
    queryKey: ["billing", "payment-status", paymentId],
    queryFn: () => clientApi<BillingPaymentStatusResponse>(`/billing/payments/${paymentId}/status`),
    enabled: Boolean(paymentId) && enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (stopOnServerTimeout && status?.should_stop_polling) return false;
      return status?.is_terminal ? false : Math.max(intervalSeconds, 1) * 1000;
    },
  });
}

export function useBillingPaymentHistory() {
  return useQuery({
    queryKey: ["billing", "payments"],
    queryFn: () => clientApi("/billing/payments?page=1&page_size=20"),
  });
}
