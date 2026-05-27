import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { adminApi } from "../../../api/adminApi";

export const adminSettingsKey = ["admin-settings"] as const;
export const adminProviderSettingsKey = ["admin-provider-settings"] as const;

export function useAdminSettings() {
  return useQuery({ queryKey: adminSettingsKey, queryFn: () => adminApi("/settings") });
}

export function useSaveAdminSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: unknown) => adminApi("/settings", { method: "PATCH", body: JSON.stringify(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: adminSettingsKey }),
  });
}

export function useUpdateBillingMonobankMode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: unknown) =>
      adminApi("/settings/billing/monobank-mode", { method: "PATCH", body: JSON.stringify(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: adminSettingsKey }),
  });
}

export function useUpdateBillingProviderSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: unknown) =>
      adminApi("/settings/billing/provider-settings", { method: "PATCH", body: JSON.stringify(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: adminSettingsKey }),
  });
}

export function useAdminProviderSettings() {
  return useQuery({ queryKey: adminProviderSettingsKey, queryFn: () => adminApi("/settings/providers") });
}

export function useSaveAdminProviderSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: unknown) => adminApi("/settings/providers", { method: "PATCH", body: JSON.stringify(payload) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminProviderSettingsKey });
      queryClient.invalidateQueries({ queryKey: adminSettingsKey });
    },
  });
}

export function useUpdateAdminPassword() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: unknown) => adminApi("/auth/password", { method: "PATCH", body: JSON.stringify(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: adminSettingsKey }),
  });
}

export function useMarkAdminPasswordPrompted() {
  return useMutation({
    mutationFn: () => adminApi("/auth/password-prompted", { method: "POST", body: "{}" }),
  });
}

export function useDeleteAllImportData() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: unknown) =>
      adminApi("/settings/import-data", { method: "DELETE", body: JSON.stringify(payload) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminSettingsKey });
      queryClient.invalidateQueries();
    },
  });
}
