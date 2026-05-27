import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BillingSettingsPanel } from "./BillingSettingsPanel";
import { requestAdminActionOtp } from "../../auth/api/actionOtpApi";
import { useAdminSettings, useSaveAdminSettings, useUpdateBillingProviderSettings } from "../../settings/api/settingsApi";

vi.mock("../../settings/api/settingsApi", () => ({
  useAdminSettings: vi.fn(),
  useSaveAdminSettings: vi.fn(),
  useUpdateBillingProviderSettings: vi.fn(),
}));

vi.mock("../../auth/api/actionOtpApi", () => ({
  requestAdminActionOtp: vi.fn(),
}));

const mockedUseAdminSettings = vi.mocked(useAdminSettings);
const mockedUseSaveAdminSettings = vi.mocked(useSaveAdminSettings);
const mockedUseUpdateBillingProviderSettings = vi.mocked(useUpdateBillingProviderSettings);
const mockedRequestAdminActionOtp = vi.mocked(requestAdminActionOtp);
const saveSettings = vi.fn();
const updateBillingProviderSettings = vi.fn();
const t = {
  otp: "OTP",
  verify: "Verify",
  save: "Save",
  saving: "Saving",
  settingsSaved: "Saved",
};

describe("BillingSettingsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedUseAdminSettings.mockReturnValue({
      data: {
        settings: {
          billing_settings: {
            monobank_mode: "test",
            double_time_for_project_support_enabled: true,
            premium_plus_checkout_enabled: false,
            enabled_period_months: [1, 3],
            plan_prices_uah: {
              premium: { 1: 10, 3: 30, 6: 60, 12: 120 },
              premium_plus: { 1: 20, 3: 60, 6: 120, 12: 240 },
            },
            invoice_validity_seconds: 3600,
            webhook_wait_seconds: 20,
            frontend_poll_interval_seconds: 10,
            frontend_poll_timeout_seconds: 60,
            long_processing_seconds: 60,
            reconciliation_interval_seconds: 3600,
            subscription_recovery_interval_seconds: 600,
            receipt_retry_interval_seconds: 3600,
            receipt_retry_delay_seconds: 3600,
            receipt_retry_max_attempts: 3,
            success_recheck_interval_days: 7,
            success_recheck_hour: 6,
            success_recheck_window_days: 7,
            subscription_expiration_hour: 0,
            offer_text: "CronoLex paid subscription offer text for tests.",
          },
        },
      },
      isError: false,
      isLoading: false,
    });
    mockedUseSaveAdminSettings.mockReturnValue({
      error: null,
      isError: false,
      isPending: false,
      isSuccess: false,
      mutate: saveSettings,
    });
    mockedUseUpdateBillingProviderSettings.mockReturnValue({
      error: null,
      isError: false,
      isPending: false,
      isSuccess: false,
      mutate: updateBillingProviderSettings,
    });
    mockedRequestAdminActionOtp.mockResolvedValue({ challenge_id: 77, dev_otp_hint: "111111" });
  });

  it("saves weekly success recheck and hourly worker settings", async () => {
    renderPanel();

    await screen.findByDisplayValue("CronoLex paid subscription offer text for tests.");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(saveSettings).toHaveBeenCalled();
    });
    const payload = saveSettings.mock.calls[0]?.[0] || {};

    expect(screen.getAllByText("Двойное время за поддержку проекта").length).toBeGreaterThan(0);
    expect(payload.billing_settings.billing_provider).toBeUndefined();
    expect(payload.billing_settings.double_time_for_project_support_enabled).toBe(true);
    expect(payload.billing_settings.premium_plus_checkout_enabled).toBe(false);
    expect(payload.billing_settings.reconciliation_interval_seconds).toBe(3600);
    expect(payload.billing_settings.frontend_poll_interval_seconds).toBe(10);
    expect(payload.billing_settings.receipt_retry_interval_seconds).toBe(3600);
    expect(payload.billing_settings.receipt_retry_delay_seconds).toBe(3600);
    expect(payload.billing_settings.success_recheck_interval_days).toBe(7);
    expect(payload.billing_settings.success_recheck_hour).toBe(6);
    expect(payload.billing_settings.success_recheck_window_days).toBe(7);
  });

  it("updates billing provider through OTP-protected provider-settings mutation", async () => {
    renderPanel();

    fireEvent.mouseDown(screen.getByLabelText("Billing provider"));
    fireEvent.click(screen.getByRole("option", { name: "Monobank" }));

    await waitFor(() => {
      expect(mockedRequestAdminActionOtp).toHaveBeenCalledWith({ action_key: "billing_provider_settings" });
    });
    expect(updateBillingProviderSettings).not.toHaveBeenCalled();
    expect(saveSettings).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("OTP"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));

    await waitFor(() => {
      expect(updateBillingProviderSettings).toHaveBeenCalledWith(
        { billing_provider: "monobank", challenge_id: 77, otp: "123456" },
        expect.any(Object),
      );
    });
    expect(saveSettings).not.toHaveBeenCalled();
  });

  it("shows Monobank mode only for monobank provider", async () => {
    mockedUseAdminSettings.mockReturnValue({
      data: {
        settings: {
          billing_settings: {
            billing_provider: "monobank",
            monobank_mode: "test",
          },
        },
      },
      isError: false,
      isLoading: false,
    });
    renderPanel();

    expect(screen.getByLabelText("Monobank mode")).toBeInTheDocument();
  });

  it("requests OTP with provider settings action key when changing Monobank mode", async () => {
    mockedUseAdminSettings.mockReturnValue({
      data: {
        settings: {
          billing_settings: {
            billing_provider: "monobank",
            monobank_mode: "test",
          },
        },
      },
      isError: false,
      isLoading: false,
    });
    renderPanel();

    fireEvent.mouseDown(screen.getByLabelText("Monobank mode"));
    fireEvent.click(screen.getByRole("option", { name: "production" }));

    await waitFor(() => {
      expect(mockedRequestAdminActionOtp).toHaveBeenCalledWith({ action_key: "billing_provider_settings" });
    });
  });
});

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BillingSettingsPanel t={t} user={{ acl_capabilities: ["acl/manage"] }} />
    </QueryClientProvider>,
  );
}
