import { useMutation } from "@tanstack/react-query";
import { Alert, Box, Button, Checkbox, Divider, FormControlLabel, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useState } from "react";

import { requestAdminActionOtp } from "../../auth/api/actionOtpApi";
import { useAdminSettings, useSaveAdminSettings, useUpdateBillingProviderSettings } from "../../settings/api/settingsApi";
import { canAdminAccess } from "../../../shared/acl/adminAcl";
import { DangerousActionOtpDialog } from "../../../shared/components";

const PERIOD_OPTIONS = [1, 3, 6, 12];
const PAID_PLAN_KEYS = ["premium", "premium_plus"];
const PLAN_LABELS = { premium: "Premium", premium_plus: "Premium +" };
const BILLING_PROVIDER_OPTIONS = [
  { value: "instant", label: "instant" },
  { value: "monobank", label: "Monobank" },
];
const MONOBANK_MODE_OPTIONS = [
  { value: "disabled", label: "disabled" },
  { value: "test", label: "test" },
  { value: "production", label: "production" },
];
const DEFAULT_BILLING_SETTINGS = {
  billing_provider: "instant",
  monobank_mode: "disabled",
  double_time_for_project_support_enabled: false,
  premium_plus_checkout_enabled: true,
  enabled_period_months: [1, 3, 6, 12],
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
  offer_text: "",
};

export function BillingSettingsPanel({ t, user, onSettingsUpdate }) {
  const settingsQuery = useAdminSettings();
  const saveSettings = useSaveAdminSettings();
  const updateBillingProviderSettings = useUpdateBillingProviderSettings();
  const canManageBilling = canAdminAccess(user, "acl/manage");
  const [billingSettings, setBillingSettings] = useState(DEFAULT_BILLING_SETTINGS);
  const [dangerActionType, setDangerActionType] = useState(null);
  const [dangerActionValue, setDangerActionValue] = useState("");
  const [dangerActionOtp, setDangerActionOtp] = useState("");
  const [dangerActionChallenge, setDangerActionChallenge] = useState(null);
  const [dangerDialogOpen, setDangerDialogOpen] = useState(false);
  const requestDangerActionOtp = useMutation({
    mutationFn: () => requestAdminActionOtp({ action_key: "billing_provider_settings" }),
    onSuccess: (data) => {
      setDangerActionChallenge(data);
      setDangerActionOtp("");
      setDangerDialogOpen(true);
    },
  });

  useEffect(() => {
    setBillingSettings(normalizeBillingSettings(settingsQuery.data?.settings?.billing_settings));
  }, [settingsQuery.data?.settings?.billing_settings]);

  function updateField(field, value) {
    setBillingSettings((current) => ({ ...current, [field]: value }));
  }

  function updatePeriod(period, checked) {
    setBillingSettings((current) => {
      const values = new Set(current.enabled_period_months || []);
      if (checked) values.add(period);
      else values.delete(period);
      return { ...current, enabled_period_months: PERIOD_OPTIONS.filter((item) => values.has(item)) };
    });
  }

  function updatePrice(planKey, period, value) {
    setBillingSettings((current) => ({
      ...current,
      plan_prices_uah: {
        ...(current.plan_prices_uah || {}),
        [planKey]: {
          ...(current.plan_prices_uah?.[planKey] || {}),
          [period]: value,
        },
      },
    }));
  }

  function saveBillingSettings(event) {
    event.preventDefault();
    saveSettings.mutate(
      {
        billing_settings: {
          double_time_for_project_support_enabled: Boolean(billingSettings.double_time_for_project_support_enabled),
          premium_plus_checkout_enabled: Boolean(billingSettings.premium_plus_checkout_enabled),
          enabled_period_months: billingSettings.enabled_period_months.map(Number),
          plan_prices_uah: PAID_PLAN_KEYS.reduce((payload, planKey) => {
            payload[planKey] = PERIOD_OPTIONS.reduce((prices, period) => {
              prices[String(period)] = Number(billingSettings.plan_prices_uah?.[planKey]?.[period]);
              return prices;
            }, {});
            return payload;
          }, {}),
          invoice_validity_seconds: Number(billingSettings.invoice_validity_seconds),
          webhook_wait_seconds: Number(billingSettings.webhook_wait_seconds),
          frontend_poll_interval_seconds: Number(billingSettings.frontend_poll_interval_seconds),
          frontend_poll_timeout_seconds: Number(billingSettings.frontend_poll_timeout_seconds),
          long_processing_seconds: Number(billingSettings.long_processing_seconds),
          reconciliation_interval_seconds: Number(billingSettings.reconciliation_interval_seconds),
          subscription_recovery_interval_seconds: Number(billingSettings.subscription_recovery_interval_seconds),
          receipt_retry_interval_seconds: Number(billingSettings.receipt_retry_interval_seconds),
          receipt_retry_delay_seconds: Number(billingSettings.receipt_retry_delay_seconds),
          receipt_retry_max_attempts: Number(billingSettings.receipt_retry_max_attempts),
          success_recheck_interval_days: Number(billingSettings.success_recheck_interval_days),
          success_recheck_hour: Number(billingSettings.success_recheck_hour),
          success_recheck_window_days: Number(billingSettings.success_recheck_window_days),
          subscription_expiration_hour: Number(billingSettings.subscription_expiration_hour),
          offer_text: billingSettings.offer_text,
        },
      },
      { onSuccess: onSettingsUpdate },
    );
  }

  function requestBillingProviderChange(nextProvider) {
    if (
      nextProvider === billingSettings.billing_provider ||
      requestDangerActionOtp.isPending ||
      updateBillingProviderSettings.isPending
    ) {
      return;
    }
    setDangerActionType("billing_provider");
    setDangerActionValue(nextProvider);
    requestDangerActionOtp.mutate();
  }

  function requestModeChange(nextMode) {
    if (
      nextMode === billingSettings.monobank_mode ||
      requestDangerActionOtp.isPending ||
      updateBillingProviderSettings.isPending
    ) {
      return;
    }
    setDangerActionType("monobank_mode");
    setDangerActionValue(nextMode);
    requestDangerActionOtp.mutate();
  }

  function confirmDangerAction() {
    if (!dangerActionChallenge?.challenge_id || !dangerActionType || !dangerActionValue) return;
    const payload = dangerActionType === "monobank_mode"
      ? {
          monobank_mode: dangerActionValue,
          challenge_id: dangerActionChallenge.challenge_id,
          otp: dangerActionOtp,
        }
      : {
          billing_provider: dangerActionValue,
          challenge_id: dangerActionChallenge.challenge_id,
          otp: dangerActionOtp,
        };
    updateBillingProviderSettings.mutate(payload, {
      onSuccess: (data) => {
        closeDangerDialog();
        onSettingsUpdate?.(data);
      },
    });
  }

  function closeDangerDialog() {
    setDangerDialogOpen(false);
    setDangerActionType(null);
    setDangerActionOtp("");
    setDangerActionChallenge(null);
    setDangerActionValue("");
  }

  const dangerActionTitle = dangerActionType === "monobank_mode"
    ? (t.monobankModeConfirmTitle || "Change Monobank mode?")
    : dangerActionType === "billing_provider"
      ? (t.billingProviderConfirmTitle || "Change billing provider?")
      : (t.billingSettingsUpdate || "Change billing setting?");

  const dangerActionText = dangerActionType === "monobank_mode"
    ? (t.monobankModeConfirmText || "Enter Telegram OTP to switch Monobank mode to {mode}.").replace("{mode}", dangerActionValue)
    : dangerActionType === "billing_provider"
      ? (t.billingProviderConfirmText || "Enter Telegram OTP to switch billing provider to {provider}.").replace("{provider}", dangerActionValue)
      : "";

  return (
    <Stack component="form" spacing={2} onSubmit={saveBillingSettings}>
      {settingsQuery.isError && <Alert severity="error">{settingsQuery.error.message || t.loadError}</Alert>}
      {saveSettings.isSuccess && <Alert severity="success">{t.settingsSaved}</Alert>}
      {saveSettings.isError && <Alert severity="error">{saveSettings.error.message || t.saveError}</Alert>}
      {requestDangerActionOtp.isError && <Alert severity="error">{requestDangerActionOtp.error.message || t.actionError}</Alert>}
      {updateBillingProviderSettings.isSuccess && (
        <Alert severity="success">{t.billingProviderUpdated || t.billingModeUpdated || "Billing provider settings updated."}</Alert>
      )}
      {updateBillingProviderSettings.isError && <Alert severity="error">{updateBillingProviderSettings.error.message || t.saveError}</Alert>}
      {!canManageBilling && <Alert severity="info">{t.billingSettingsReadOnly || "Billing settings are read-only for this account."}</Alert>}

      <Stack spacing={0.5}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{t.billingProvider || "Billing provider"}</Typography>
        <Typography variant="body2" color="text.secondary">
          {t.billingProviderHint || "Choose how billing is processed for paid subscriptions."}
        </Typography>
      </Stack>
      <TextField
        select
        label={t.billingProvider || "Billing provider"}
        value={billingSettings.billing_provider}
        disabled={!canManageBilling || settingsQuery.isLoading || saveSettings.isPending || requestDangerActionOtp.isPending || updateBillingProviderSettings.isPending || dangerDialogOpen}
        onChange={(event) => requestBillingProviderChange(event.target.value)}
        fullWidth
      >
        {BILLING_PROVIDER_OPTIONS.map((option) => (
          <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
        ))}
      </TextField>

      {billingSettings.billing_provider === "monobank" ? (
        <>
          <Divider />
          <Stack spacing={0.5}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{t.monobankMode || "Monobank mode"}</Typography>
            <Typography variant="body2" color="text.secondary">
              {t.monobankModeHint || "Changing test/production/disabled mode requires Telegram OTP. Tokens are read from env and are not stored in DB."}
            </Typography>
          </Stack>
          <TextField
            select
            label={t.monobankMode || "Monobank mode"}
            value={billingSettings.monobank_mode}
            disabled={!canManageBilling || settingsQuery.isLoading || requestDangerActionOtp.isPending || updateBillingProviderSettings.isPending || dangerDialogOpen}
            onChange={(event) => requestModeChange(event.target.value)}
            fullWidth
          >
            {MONOBANK_MODE_OPTIONS.map((option) => (
              <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
            ))}
          </TextField>
        </>
      ) : null}
      <Divider />
      <Stack spacing={0.5}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Двойное время за поддержку проекта</Typography>
        <Typography variant="body2" color="text.secondary">
          {t.doubleTimeForProjectSupportHint || "Когда включено, любая успешная оплата начисляет в два раза больше времени подписки."}
        </Typography>
        <FormControlLabel
          control={
            <Checkbox
              checked={Boolean(billingSettings.double_time_for_project_support_enabled)}
              onChange={(event) => updateField("double_time_for_project_support_enabled", event.target.checked)}
              disabled={!canManageBilling}
            />
          }
          label="Двойное время за поддержку проекта"
        />
      </Stack>

      <Divider />
      <Stack spacing={0.5}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{t.premiumPlusPurchase || "Premium+ purchase"}</Typography>
        <Typography variant="body2" color="text.secondary">
          {t.premiumPlusPurchaseHint || "When disabled, Premium+ is hidden from the client plans page and direct Premium+ checkout is rejected."}
        </Typography>
        <FormControlLabel
          control={
            <Checkbox
              checked={Boolean(billingSettings.premium_plus_checkout_enabled)}
              onChange={(event) => updateField("premium_plus_checkout_enabled", event.target.checked)}
              disabled={!canManageBilling}
            />
          }
          label={t.premiumPlusPurchaseEnabled || "Premium+ purchase enabled"}
        />
      </Stack>

      <Divider />
      <Stack spacing={0.5}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{t.billingPricing || "Pricing"}</Typography>
        <Typography variant="body2" color="text.secondary">
          {t.billingPricingHint || "Prices are UAH amounts shown to users on the plan page."}
        </Typography>
      </Stack>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "repeat(4, minmax(0, 1fr))" }, gap: 1 }}>
        {PERIOD_OPTIONS.map((period) => (
          <FormControlLabel
            key={period}
            control={
              <Checkbox
                checked={(billingSettings.enabled_period_months || []).includes(period)}
                onChange={(event) => updatePeriod(period, event.target.checked)}
                disabled={!canManageBilling}
              />
            }
            label={`${period} ${t.monthsShort || "мес."}`}
          />
        ))}
      </Box>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "repeat(2, minmax(0, 1fr))" }, gap: 2 }}>
        {PAID_PLAN_KEYS.map((planKey) => (
          <Stack key={planKey} spacing={1.5} sx={{ minWidth: 0, p: 2, border: 1, borderColor: "divider", borderRadius: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{PLAN_LABELS[planKey]}</Typography>
            {PERIOD_OPTIONS.map((period) => (
              <TextField
                key={`${planKey}-${period}`}
                label={`${period} ${t.monthsShort || "мес."}, UAH`}
                type="number"
                value={billingSettings.plan_prices_uah?.[planKey]?.[period] ?? ""}
                onChange={(event) => updatePrice(planKey, period, event.target.value)}
                disabled={!canManageBilling}
                fullWidth
              />
            ))}
          </Stack>
        ))}
      </Box>

      <Divider />
      <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{t.billingTiming || "Timing"}</Typography>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "repeat(3, minmax(0, 1fr))" }, gap: 2 }}>
        <NumberField t={t} disabled={!canManageBilling} label={t.invoiceValiditySeconds || "Invoice validity, sec"} field="invoice_validity_seconds" value={billingSettings.invoice_validity_seconds} onChange={updateField} />
        <NumberField t={t} disabled={!canManageBilling} label={t.webhookWaitSeconds || "Webhook wait, sec"} field="webhook_wait_seconds" value={billingSettings.webhook_wait_seconds} onChange={updateField} />
        <NumberField t={t} disabled={!canManageBilling} label={t.pollIntervalSeconds || "Poll interval, sec"} field="frontend_poll_interval_seconds" value={billingSettings.frontend_poll_interval_seconds} onChange={updateField} />
        <NumberField t={t} disabled={!canManageBilling} label={t.pollTimeoutSeconds || "Poll timeout, sec"} field="frontend_poll_timeout_seconds" value={billingSettings.frontend_poll_timeout_seconds} onChange={updateField} />
        <NumberField t={t} disabled={!canManageBilling} label={t.longProcessingSeconds || "Long processing, sec"} field="long_processing_seconds" value={billingSettings.long_processing_seconds} onChange={updateField} />
        <NumberField t={t} disabled={!canManageBilling} label={t.reconciliationIntervalSeconds || "Reconciliation interval, sec"} field="reconciliation_interval_seconds" value={billingSettings.reconciliation_interval_seconds} onChange={updateField} />
        <NumberField t={t} disabled={!canManageBilling} label={t.subscriptionRecoveryIntervalSeconds || "Subscription recovery interval, sec"} field="subscription_recovery_interval_seconds" value={billingSettings.subscription_recovery_interval_seconds} onChange={updateField} />
        <NumberField t={t} disabled={!canManageBilling} label={t.receiptRetryIntervalSeconds || "Receipt retry interval, sec"} field="receipt_retry_interval_seconds" value={billingSettings.receipt_retry_interval_seconds} onChange={updateField} />
        <NumberField t={t} disabled={!canManageBilling} label={t.receiptRetryDelaySeconds || "Receipt retry delay, sec"} field="receipt_retry_delay_seconds" value={billingSettings.receipt_retry_delay_seconds} onChange={updateField} />
        <NumberField t={t} disabled={!canManageBilling} label={t.receiptRetryMaxAttempts || "Receipt retry max attempts"} field="receipt_retry_max_attempts" value={billingSettings.receipt_retry_max_attempts} onChange={updateField} />
        <TextField
          select
          label={t.successRecheckIntervalDays || "Success recheck interval, days"}
          value={Number(billingSettings.success_recheck_interval_days)}
          onChange={(event) => updateField("success_recheck_interval_days", Number(event.target.value))}
          disabled={!canManageBilling}
          fullWidth
        >
          {[1, 2, 3, 4, 5, 6, 7].map((days) => (
            <MenuItem key={days} value={days}>{days}</MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label={t.successRecheckHour || "Success recheck hour"}
          value={Number(billingSettings.success_recheck_hour)}
          onChange={(event) => updateField("success_recheck_hour", Number(event.target.value))}
          disabled={!canManageBilling}
          fullWidth
        >
          {Array.from({ length: 24 }, (_, hour) => (
            <MenuItem key={hour} value={hour}>{String(hour).padStart(2, "0")}:00</MenuItem>
          ))}
        </TextField>
        <NumberField t={t} disabled={!canManageBilling} label={t.successRecheckWindowDays || "Success recheck window, days"} field="success_recheck_window_days" value={billingSettings.success_recheck_window_days} onChange={updateField} />
        <TextField
          select
          label={t.subscriptionExpirationHour || "Subscription expiration hour"}
          value={Number(billingSettings.subscription_expiration_hour)}
          onChange={(event) => updateField("subscription_expiration_hour", Number(event.target.value))}
          disabled={!canManageBilling}
          fullWidth
        >
          {Array.from({ length: 24 }, (_, hour) => (
            <MenuItem key={hour} value={hour}>{String(hour).padStart(2, "0")}:00</MenuItem>
          ))}
        </TextField>
      </Box>

      <Divider />
      <TextField
        label={t.billingOfferTitle || "Offer text"}
        value={billingSettings.offer_text}
        onChange={(event) => updateField("offer_text", event.target.value)}
        disabled={!canManageBilling}
        multiline
        minRows={10}
        fullWidth
        helperText={t.billingOfferSettingsHint || "This text is shown in the client checkout offer reader."}
      />

      <Button type="submit" variant="contained" disabled={!canManageBilling || saveSettings.isPending || settingsQuery.isLoading} sx={{ alignSelf: "flex-start" }}>
        {saveSettings.isPending ? t.saving : t.save}
      </Button>
      <DangerousActionOtpDialog
        t={t}
        open={dangerDialogOpen}
        title={dangerActionTitle}
        text={dangerActionText}
        otp={dangerActionOtp}
        devOtpHint={dangerActionChallenge?.dev_otp_hint}
        error={
          updateBillingProviderSettings.isError ? updateBillingProviderSettings.error.message || t.actionError : ""
        }
        pending={updateBillingProviderSettings.isPending}
        onOtpChange={setDangerActionOtp}
        onCancel={closeDangerDialog}
        onConfirm={confirmDangerAction}
      />
    </Stack>
  );
}

function NumberField({ label, field, value, disabled, onChange }) {
  return (
    <TextField
      label={label}
      type="number"
      value={value ?? ""}
      onChange={(event) => onChange(field, event.target.value)}
      disabled={disabled}
      fullWidth
    />
  );
}

function normalizeBillingSettings(value) {
  const source = { ...DEFAULT_BILLING_SETTINGS, ...(value || {}) };
  return {
    ...source,
    enabled_period_months: Array.isArray(source.enabled_period_months) ? source.enabled_period_months.map(Number) : [1, 3, 6, 12],
    plan_prices_uah: PAID_PLAN_KEYS.reduce((payload, planKey) => {
      payload[planKey] = PERIOD_OPTIONS.reduce((prices, period) => {
        prices[period] = source.plan_prices_uah?.[planKey]?.[String(period)] ?? source.plan_prices_uah?.[planKey]?.[period] ?? "";
        return prices;
      }, {});
      return payload;
    }, {}),
  };
}
