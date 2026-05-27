import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { adminApi } from "../../../api/adminApi";
import {
  useAdminProviderSettings,
  useAdminSettings,
  useDeleteAllImportData,
  useMarkAdminPasswordPrompted,
  useSaveAdminProviderSettings,
  useSaveAdminSettings,
  useUpdateBillingMonobankMode,
  useUpdateBillingProviderSettings,
  useUpdateAdminPassword,
} from "./settingsApi";

vi.mock("../../../api/adminApi", () => ({
  adminApi: vi.fn(),
}));

const mockedAdminApi = vi.mocked(adminApi);

describe("settingsApi", () => {
  beforeEach(() => {
    mockedAdminApi.mockReset();
    mockedAdminApi.mockResolvedValue({});
  });

  it("loads admin settings", async () => {
    const { result } = renderHook(() => useAdminSettings(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedAdminApi).toHaveBeenCalledWith("/settings");
  });

  it("saves admin settings", async () => {
    const payload = { interface_locale: "pl", app_version: "0.0.5-beta" };
    const { result } = renderHook(() => useSaveAdminSettings(), { wrapper: createWrapper() });

    act(() => result.current.mutate(payload));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedAdminApi).toHaveBeenCalledWith("/settings", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  });

  it("loads provider settings", async () => {
    const { result } = renderHook(() => useAdminProviderSettings(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedAdminApi).toHaveBeenCalledWith("/settings/providers");
  });

  it("saves provider settings", async () => {
    const payload = { tasks: [{ task_key: "user_import.word_details", provider_key: "openai", is_enabled: true, config: {} }] };
    const { result } = renderHook(() => useSaveAdminProviderSettings(), { wrapper: createWrapper() });

    act(() => result.current.mutate(payload));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedAdminApi).toHaveBeenCalledWith("/settings/providers", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  });

  it("updates admin password", async () => {
    const payload = { current_password: "old", password: "Pass1234", confirm_password: "Pass1234" };
    const { result } = renderHook(() => useUpdateAdminPassword(), { wrapper: createWrapper() });

    act(() => result.current.mutate(payload));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedAdminApi).toHaveBeenCalledWith("/auth/password", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  });

  it("updates billing monobank mode after OTP confirmation", async () => {
    const payload = { monobank_mode: "test", challenge_id: 10, otp: "123456" };
    const { result } = renderHook(() => useUpdateBillingMonobankMode(), { wrapper: createWrapper() });

    act(() => result.current.mutate(payload));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedAdminApi).toHaveBeenCalledWith("/settings/billing/monobank-mode", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  });

  it("updates billing provider settings after OTP confirmation", async () => {
    const payload = { monobank_mode: "test", challenge_id: 10, otp: "123456" };
    const { result } = renderHook(() => useUpdateBillingProviderSettings(), { wrapper: createWrapper() });

    act(() => result.current.mutate(payload));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedAdminApi).toHaveBeenCalledWith("/settings/billing/provider-settings", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  });

  it("updates billing provider without OTP when only provider key changes", async () => {
    const payload = { billing_provider: "instant" };
    const { result } = renderHook(() => useUpdateBillingProviderSettings(), { wrapper: createWrapper() });

    act(() => result.current.mutate(payload));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedAdminApi).toHaveBeenCalledWith("/settings/billing/provider-settings", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  });

  it("marks password prompt as shown", async () => {
    const { result } = renderHook(() => useMarkAdminPasswordPrompted(), { wrapper: createWrapper() });

    act(() => result.current.mutate());
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedAdminApi).toHaveBeenCalledWith("/auth/password-prompted", { method: "POST", body: "{}" });
  });

  it("deletes all import data after OTP confirmation", async () => {
    const payload = { challenge_id: 10, otp: "123456" };
    const { result } = renderHook(() => useDeleteAllImportData(), { wrapper: createWrapper() });

    act(() => result.current.mutate(payload));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedAdminApi).toHaveBeenCalledWith("/settings/import-data", {
      method: "DELETE",
      body: JSON.stringify(payload),
    });
  });
});

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}
