import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { clientApi } from "../../../api/clientApi";

export const settingsKey = ["settings"] as const;

export function useSettings() {
  return useQuery({ queryKey: settingsKey, queryFn: () => clientApi("/settings") });
}

export function useSaveSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: unknown) => clientApi("/settings", { method: "PATCH", body: JSON.stringify(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: settingsKey })
  });
}

export function useUpdatePassword() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: unknown) => clientApi("/auth/password", { method: "PATCH", body: JSON.stringify(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: settingsKey })
  });
}

export function useMarkPasswordPrompted() {
  return useMutation({
    mutationFn: () => clientApi("/auth/password-prompted", { method: "POST", body: "{}" })
  });
}
