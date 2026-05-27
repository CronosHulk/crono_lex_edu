import { PasswordField, PasswordRequirements } from "@cronolex/shared";
import { Alert, Box, Button, Divider, FormControlLabel, MenuItem, Stack, Switch, TextField, Typography } from "@mui/material";
import { useEffect, useState } from "react";

import { canAdminAccess } from "../../shared/acl/adminAcl";
import { CrudFormSurface, CrudPage } from "../../shared/components";
import {
  useAdminProviderSettings,
  useAdminSettings,
  useDeleteAllImportData,
  useMarkAdminPasswordPrompted,
  useSaveAdminProviderSettings,
  useSaveAdminSettings,
  useUpdateAdminPassword,
} from "./api/settingsApi";
import {
  isProviderTaskEnabled,
  providerTaskConfigFields,
  providerTaskConfigOptions,
  providerTaskEnabledLabel,
} from "./helpers/providerTaskState";
import { DEFAULT_IMPORT_SETTINGS, ImportSettingsSection } from "./components/ImportSettingsSection";

const LOCALE_OPTIONS = [
  { value: "uk", label: "UK" },
  { value: "ru", label: "RU" },
  { value: "pl", label: "PL" },
];
const PLAN_LIMIT_KEYS = ["free", "premium", "premium_plus"];
const PLAN_LABELS = { free: "Free", premium: "Premium", premium_plus: "Premium +" };
const IMPORT_MODE_OPTIONS = [
  { value: "lookup_only", label: "lookup_only" },
  { value: "ai_new_words", label: "ai_new_words" },
];
const DEFAULT_ANALYTICS_SETTINGS = {
  google_analytics_id: "",
  google_ads_id: "",
};

export function SettingsPage({ section = "profile", t, user, appVersion, onSettingsUpdate, onUserUpdate }) {
  const settings = useAdminSettings();
  const providerSettings = useAdminProviderSettings();
  const save = useSaveAdminSettings();
  const saveProviders = useSaveAdminProviderSettings();
  const updatePassword = useUpdateAdminPassword();
  const deleteImportData = useDeleteAllImportData();
  const markPrompted = useMarkAdminPasswordPrompted();
  const activeSection = section === "password" || section === "providers" || section === "analytics" || section === "import" || section === "plans" ? section : "profile";
  const sectionTitle = settingsSectionTitle(activeSection, t);
  const settingsData = settings.data?.settings || {};
  const canManageProviders = canAdminAccess(user, "acl/manage");
  const canManageAnalytics = canAdminAccess(user, "acl/manage");
  const [interfaceLocale, setInterfaceLocale] = useState(user?.interface_locale || "uk");
  const [version, setVersion] = useState(appVersion || "0.0.5");
  const [providerTasks, setProviderTasks] = useState([]);
  const [analyticsSettings, setAnalyticsSettings] = useState(DEFAULT_ANALYTICS_SETTINGS);
  const [importSettings, setImportSettings] = useState(DEFAULT_IMPORT_SETTINGS);
  const [planLimits, setPlanLimits] = useState({});
  const [currentPassword, setCurrentPassword] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const canManageVersion = canAdminAccess(user, "acl/manage");
  const canManageImportSettings = canAdminAccess(user, "acl/manage");
  const canDeleteImportData = user?.acl_group_title === "super_admin";
  const passwordMismatch = confirmPassword.length > 0 && password !== confirmPassword;
  const canSubmitPassword =
    password.length > 0 &&
    confirmPassword.length > 0 &&
    !passwordMismatch &&
    (!user?.has_password || currentPassword.length > 0);

  useEffect(() => {
    setInterfaceLocale(settingsData.interface_locale || user?.interface_locale || "uk");
    setVersion(settingsData.app_version || appVersion || "0.0.5");
  }, [appVersion, settingsData.app_version, settingsData.interface_locale, user?.interface_locale]);

  useEffect(() => {
    setProviderTasks(providerSettings.data?.tasks || settingsData.provider_tasks || []);
  }, [providerSettings.data?.tasks, settingsData.provider_tasks]);

  useEffect(() => {
    setAnalyticsSettings({ ...DEFAULT_ANALYTICS_SETTINGS, ...(settingsData.analytics_settings || {}) });
  }, [settingsData.analytics_settings]);

  useEffect(() => {
    setImportSettings({ ...DEFAULT_IMPORT_SETTINGS, ...(settingsData.import_settings || {}) });
  }, [settingsData.import_settings]);

  useEffect(() => {
    setPlanLimits(settingsData.plan_limits || {});
  }, [settingsData.plan_limits]);

  useEffect(() => {
    if (!user?.requires_password_setup || activeSection !== "password" || markPrompted.isPending || markPrompted.isSuccess) return;
    markPrompted.mutate(undefined, {
      onSuccess: (data) => {
        onUserUpdate?.(data.user);
      },
    });
  }, [activeSection, markPrompted, onUserUpdate, user?.requires_password_setup]);

  function saveProfile(event) {
    event.preventDefault();
    const payload = { interface_locale: interfaceLocale };
    if (canManageVersion) {
      payload.app_version = version;
    }
    save.mutate(payload, {
      onSuccess: (data) => {
        onSettingsUpdate?.(data);
      },
    });
  }

  function savePassword(event) {
    event.preventDefault();
    if (!canSubmitPassword) return;
    updatePassword.mutate(
      {
        current_password: user?.has_password ? currentPassword : null,
        password,
        confirm_password: confirmPassword,
      },
      {
        onSuccess: (data) => {
          onUserUpdate?.(data.user);
          setCurrentPassword("");
          setPassword("");
          setConfirmPassword("");
        },
      },
    );
  }

  function updateProviderTask(taskKey, patch) {
    setProviderTasks((current) => current.map((task) => (task.task_key === taskKey ? { ...task, ...patch } : task)));
  }

  function updateProviderConfig(taskKey, field, value) {
    setProviderTasks((current) =>
      current.map((task) =>
        task.task_key === taskKey
          ? {
              ...task,
              config: { ...(task.config || {}), [field]: value },
            }
          : task,
      ),
    );
  }

  function saveProviderSettings(event) {
    event.preventDefault();
    saveProviders.mutate({
      tasks: providerTasks.map((task) => ({
        task_key: task.task_key,
        provider_key: task.provider_key,
        is_enabled: isProviderTaskEnabled(task),
        config: task.config || {},
      })),
    });
  }

  function updateAnalyticsSetting(field, value) {
    setAnalyticsSettings((current) => ({ ...current, [field]: value }));
  }

  function saveAnalyticsSettings(event) {
    event.preventDefault();
    save.mutate(
      {
        analytics_settings: {
          google_analytics_id: analyticsSettings.google_analytics_id || "",
          google_ads_id: analyticsSettings.google_ads_id || "",
        },
      },
      {
        onSuccess: (data) => {
          onSettingsUpdate?.(data);
        },
      },
    );
  }

  function updateImportSetting(field, value) {
    setImportSettings((current) => ({ ...current, [field]: value }));
  }

  function saveImportSettings(event) {
    event.preventDefault();
    save.mutate(
      {
        import_settings: {
          enrich_after_google_doc_import_enabled: Boolean(importSettings.enrich_after_google_doc_import_enabled),
          embedding_build_enabled: Boolean(importSettings.embedding_build_enabled),
          attribute_build_hour: Number(importSettings.attribute_build_hour),
          attribute_build_weekdays: Array.isArray(importSettings.attribute_build_weekdays)
            ? importSettings.attribute_build_weekdays.map((value) => Number(value))
            : null,
          audio_build_hour: Number(importSettings.audio_build_hour),
          audio_build_weekdays: Array.isArray(importSettings.audio_build_weekdays)
            ? importSettings.audio_build_weekdays.map((value) => Number(value))
            : null,
          google_doc_sync_hour: Number(importSettings.google_doc_sync_hour),
          google_doc_sync_interval_days: Number(importSettings.google_doc_sync_interval_days),
          google_doc_sync_weekdays: Array.isArray(importSettings.google_doc_sync_weekdays)
            ? importSettings.google_doc_sync_weekdays.map((value) => Number(value))
            : null,
          max_import_entries_per_submission: Number(importSettings.max_import_entries_per_submission),
          scheduler_tick_minutes: Number(importSettings.scheduler_tick_minutes),
          validation_batch_size: Number(importSettings.validation_batch_size),
        },
      },
      {
        onSuccess: (data) => {
          onSettingsUpdate?.(data);
        },
      },
    );
  }

  function updatePlanLimit(planKey, field, value) {
    setPlanLimits((current) => ({
      ...current,
      [planKey]: {
        ...(current[planKey] || {}),
        [field]: value,
      },
    }));
  }

  function savePlanLimits(event) {
    event.preventDefault();
    save.mutate(
      {
        plan_limits: PLAN_LIMIT_KEYS.reduce((payload, planKey) => {
          const limits = planLimits[planKey] || {};
          payload[planKey] = {
            ...limits,
            reminders_per_day: Number(limits.reminders_per_day),
            new_import_words_per_week: limits.new_import_words_per_week === "" ? null : Number(limits.new_import_words_per_week),
            level_titles: csvOrNull(limits.level_titles),
            words_per_session_options: intCsvOrNull(limits.words_per_session_options),
            listening_training: Boolean(limits.listening_training),
            reading_training: Boolean(limits.reading_training),
          };
          return payload;
        }, {}),
      },
      {
        onSuccess: (data) => {
          onSettingsUpdate?.(data);
        },
      },
    );
  }

  return (
    <CrudPage
      title={sectionTitle}
      breadcrumbs={[
        { title: "CronoLex", path: "/admin" },
        { title: t.settings, path: "/admin/settings" },
        { title: sectionTitle },
      ]}
    >
      <CrudFormSurface sx={activeSection === "providers" || activeSection === "plans" ? { width: "100%", maxWidth: 1180 } : { width: "min(100%, 560px)" }}>
        <Stack spacing={2}>
          {activeSection === "profile" ? (
            <Stack component="form" spacing={2} onSubmit={saveProfile}>
              {settings.isError && <Alert severity="error">{settings.error.message || t.loadError}</Alert>}
              {save.isSuccess && <Alert severity="success">{t.settingsSaved}</Alert>}
              {save.isError && <Alert severity="error">{save.error.message || t.saveError}</Alert>}
              <TextField select label={t.interfaceLanguage} value={interfaceLocale} onChange={(event) => setInterfaceLocale(event.target.value)} fullWidth>
                {LOCALE_OPTIONS.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}
              </TextField>
              {canManageVersion && (
                <TextField
                  label={t.appVersion}
                  value={version}
                  onChange={(event) => setVersion(event.target.value)}
                  fullWidth
                  helperText={t.appVersionHint}
                />
              )}
              <Button type="submit" variant="contained" disabled={save.isPending || settings.isLoading}>
                {save.isPending ? t.saving : t.save}
              </Button>
            </Stack>
          ) : activeSection === "analytics" ? (
            <Stack component="form" spacing={2} onSubmit={saveAnalyticsSettings}>
              {settings.isError && <Alert severity="error">{settings.error.message || t.loadError}</Alert>}
              {save.isSuccess && <Alert severity="success">{t.settingsSaved}</Alert>}
              {save.isError && <Alert severity="error">{save.error.message || t.saveError}</Alert>}
              {!canManageAnalytics && <Alert severity="info">{t.analyticsSettingsReadOnly || "Analytics settings are read-only for this account."}</Alert>}
              <Alert severity="info">
                {t.analyticsSettingsHint || "Tracking scripts run only when a matching Google ID is configured. Empty fields keep scripts disabled."}
              </Alert>
              <TextField
                label={t.googleAnalyticsId || "Google Analytics ID"}
                value={analyticsSettings.google_analytics_id}
                onChange={(event) => updateAnalyticsSetting("google_analytics_id", event.target.value)}
                helperText={t.googleAnalyticsIdHint || "Format: G-XXXXXXXX. Empty = disabled."}
                disabled={!canManageAnalytics}
                fullWidth
              />
              <TextField
                label={t.googleAdsId || "Google Ads ID"}
                value={analyticsSettings.google_ads_id}
                onChange={(event) => updateAnalyticsSetting("google_ads_id", event.target.value)}
                helperText={t.googleAdsIdHint || "Format: AW-123456789. Empty = disabled."}
                disabled={!canManageAnalytics}
                fullWidth
              />
              <Button type="submit" variant="contained" disabled={!canManageAnalytics || save.isPending || settings.isLoading} sx={{ alignSelf: "flex-start" }}>
                {save.isPending ? t.saving : t.save}
              </Button>
            </Stack>
          ) : activeSection === "providers" ? (
            <Stack component="form" spacing={2} onSubmit={saveProviderSettings}>
              {providerSettings.isError && <Alert severity="error">{providerSettings.error.message || t.loadError}</Alert>}
              {saveProviders.isSuccess && <Alert severity="success">{t.settingsSaved}</Alert>}
              {saveProviders.isError && <Alert severity="error">{saveProviders.error.message || t.saveError}</Alert>}
              {!canManageProviders && <Alert severity="info">{t.providerSettingsReadOnly || "Provider settings are read-only for this account."}</Alert>}
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", lg: "repeat(2, minmax(0, 1fr))" },
                  gap: 2.5,
                  alignItems: "start",
                }}
              >
                {providerTasks.map((task) => (
                  <Stack key={task.task_key} spacing={1.5} sx={{ minWidth: 0 }}>
                    <Stack spacing={0.5}>
                      <Typography variant="subtitle1">{task.title}</Typography>
                      <Typography variant="body2" color="text.secondary">{task.description}</Typography>
                    </Stack>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={isProviderTaskEnabled(task)}
                          onChange={(event) => updateProviderTask(task.task_key, { is_enabled: event.target.checked })}
                          disabled={!canManageProviders || task.provider_key === "disabled"}
                        />
                      }
                      label={providerTaskEnabledLabel(task, t)}
                    />
                    <TextField
                      select
                      label={t.provider || "Provider"}
                      value={task.provider_key}
                      onChange={(event) => updateProviderTask(task.task_key, { provider_key: event.target.value, is_enabled: event.target.value !== "disabled" })}
                      disabled={!canManageProviders}
                      fullWidth
                    >
                      {(task.allowed_provider_keys || []).map((providerKey) => (
                        <MenuItem key={providerKey} value={providerKey}>{providerKey}</MenuItem>
                      ))}
                    </TextField>
                    {providerTaskConfigFields(task).map((field) => {
                      const options = providerTaskConfigOptions(task, field);
                      const value = task.config?.[field] || "";
                      return (
                        <TextField
                          key={`${task.task_key}-${field}`}
                          label={field}
                          value={value}
                          onChange={(event) => updateProviderConfig(task.task_key, field, event.target.value)}
                          disabled={!canManageProviders}
                          select={options.length > 0}
                          fullWidth
                        >
                          {options.map((option) => (
                            <MenuItem key={option} value={option}>{option}</MenuItem>
                          ))}
                        </TextField>
                      );
                    })}
                    <Divider sx={{ display: { xs: "block", lg: "none" } }} />
                  </Stack>
                ))}
              </Box>
              <Button type="submit" variant="contained" disabled={!canManageProviders || saveProviders.isPending || providerSettings.isLoading} sx={{ alignSelf: "flex-start" }}>
                {saveProviders.isPending ? t.saving : t.save}
              </Button>
            </Stack>
          ) : activeSection === "import" ? (
            <ImportSettingsSection
              t={t}
              settingsQuery={settings}
              saveMutation={save}
              importSettings={importSettings}
              canManageImportSettings={canManageImportSettings}
              canDeleteImportData={canDeleteImportData}
              deleteImportDataMutation={deleteImportData}
              onChange={updateImportSetting}
              onSubmit={saveImportSettings}
            />
          ) : activeSection === "plans" ? (
            <Stack component="form" spacing={2} onSubmit={savePlanLimits}>
              {settings.isError && <Alert severity="error">{settings.error.message || t.loadError}</Alert>}
              {save.isSuccess && <Alert severity="success">{t.settingsSaved}</Alert>}
              {save.isError && <Alert severity="error">{save.error.message || t.saveError}</Alert>}
              <Alert severity="info">
                {t.planLimitsHint || "These limits feed the central paywall module. Checkout is prepared for Mono, but client plan buttons currently switch plans instantly."}
              </Alert>
              <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "repeat(3, minmax(0, 1fr))" }, gap: 2 }}>
                {PLAN_LIMIT_KEYS.map((planKey) => {
                  const limits = planLimits[planKey] || {};
                  return (
                    <Stack key={planKey} spacing={1.5} sx={{ minWidth: 0, p: 2, border: 1, borderColor: "divider", borderRadius: 1 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{PLAN_LABELS[planKey]}</Typography>
                      <TextField
                        label={t.planLevels || "Levels"}
                        value={displayCsv(limits.level_titles)}
                        onChange={(event) => updatePlanLimit(planKey, "level_titles", event.target.value)}
                        helperText={t.planNullHint || "Empty = no limit"}
                        fullWidth
                      />
                      <TextField
                        label={t.planWordCounts || "Words/session options"}
                        value={displayCsv(limits.words_per_session_options)}
                        onChange={(event) => updatePlanLimit(planKey, "words_per_session_options", event.target.value)}
                        helperText={t.planNullHint || "Empty = no limit"}
                        fullWidth
                      />
                      <TextField
                        label={t.remindersPerDay || "Reminders/day"}
                        type="number"
                        value={limits.reminders_per_day ?? ""}
                        onChange={(event) => updatePlanLimit(planKey, "reminders_per_day", event.target.value)}
                        fullWidth
                      />
                      <TextField
                        select
                        label={t.importMode || "Import mode"}
                        value={limits.import_mode || "lookup_only"}
                        onChange={(event) => updatePlanLimit(planKey, "import_mode", event.target.value)}
                        fullWidth
                      >
                        {IMPORT_MODE_OPTIONS.map((option) => (
                          <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
                        ))}
                      </TextField>
                      <TextField
                        label={t.newWordsPerWeek || "New import words/week"}
                        value={limits.new_import_words_per_week ?? ""}
                        onChange={(event) => updatePlanLimit(planKey, "new_import_words_per_week", event.target.value)}
                        helperText={t.planNullHint || "Empty = no limit"}
                        fullWidth
                      />
                      <FormControlLabel
                        control={<Switch checked={Boolean(limits.listening_training)} onChange={(event) => updatePlanLimit(planKey, "listening_training", event.target.checked)} />}
                        label={t.listeningTraining || "Listening trainings"}
                      />
                      <FormControlLabel
                        control={<Switch checked={Boolean(limits.reading_training)} onChange={(event) => updatePlanLimit(planKey, "reading_training", event.target.checked)} />}
                        label={t.readingTraining || "Reading trainings"}
                      />
                    </Stack>
                  );
                })}
              </Box>
              <Button type="submit" variant="contained" disabled={save.isPending || settings.isLoading} sx={{ alignSelf: "flex-start" }}>
                {save.isPending ? t.saving : t.save}
              </Button>
            </Stack>
          ) : (
            <Stack component="form" spacing={2} onSubmit={savePassword}>
              {!user?.has_password && <Alert severity="info">{t.createPasswordLater}</Alert>}
              {updatePassword.isSuccess && <Alert severity="success">{t.passwordSaved}</Alert>}
              {updatePassword.isError && <Alert severity="error">{updatePassword.error.message || t.saveError}</Alert>}
              {user?.has_password && (
                <PasswordField label={t.currentPassword} value={currentPassword} onChange={setCurrentPassword} showLabel={t.showPassword} hideLabel={t.hidePassword} />
              )}
              <PasswordField
                label={user?.has_password ? t.newPassword : t.password}
                value={password}
                onChange={setPassword}
                showLabel={t.showPassword}
                hideLabel={t.hidePassword}
              />
              <PasswordField
                label={t.confirmPassword}
                value={confirmPassword}
                onChange={setConfirmPassword}
                error={passwordMismatch}
                helperText={passwordMismatch ? t.passwordsMismatch : ""}
                showLabel={t.showPassword}
                hideLabel={t.hidePassword}
              />
              <PasswordRequirements
                password={password}
                labels={{
                  length: t.passwordRuleLength,
                  letters: t.passwordRuleLetters,
                  digits: t.passwordRuleDigits,
                  special: t.passwordRuleSpecial,
                }}
              />
              <Button type="submit" variant="contained" disabled={updatePassword.isPending || !canSubmitPassword}>
                {updatePassword.isPending ? t.saving : user?.has_password ? t.changePassword : t.createPassword}
              </Button>
            </Stack>
          )}
        </Stack>
      </CrudFormSurface>
    </CrudPage>
  );
}

function settingsSectionTitle(section, t) {
  if (section === "analytics") return t.analyticsSettings || "Analytics";
  if (section === "providers") return t.providerSettings || "Providers";
  if (section === "import") return t.importSettings || "Import";
  if (section === "plans") return t.planLimitsSettings || "Plan limits";
  if (section === "password") return t.password;
  return t.profile;
}

function displayCsv(value) {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}

function csvOrNull(value) {
  if (value === null || value === undefined) return null;
  if (Array.isArray(value)) return value;
  const text = String(value).trim();
  if (!text) return null;
  return text.split(",").map((item) => item.trim()).filter(Boolean);
}

function intCsvOrNull(value) {
  const items = csvOrNull(value);
  return items === null ? null : items.map((item) => Number(item));
}
