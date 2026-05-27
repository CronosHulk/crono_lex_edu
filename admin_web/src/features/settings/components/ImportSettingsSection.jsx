import { useMutation } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { Alert, Button, Divider, FormControlLabel, MenuItem, Stack, Switch, TextField, Typography } from "@mui/material";

import { requestAdminActionOtp } from "../../auth/api/actionOtpApi";
import { DangerousActionOtpDialog } from "../../../shared/components";

export const DEFAULT_IMPORT_SETTINGS = {
  enrich_after_google_doc_import_enabled: false,
  embedding_build_enabled: false,
  attribute_build_hour: 2,
  attribute_build_weekdays: null,
  audio_build_hour: 2,
  audio_build_weekdays: null,
  google_doc_sync_hour: 0,
  google_doc_sync_interval_days: 3,
  google_doc_sync_weekdays: null,
  max_import_entries_per_submission: 100,
  scheduler_tick_minutes: 10,
  validation_batch_size: 10,
};

const HOUR_OPTIONS = Array.from({ length: 24 }, (_, hour) => ({ value: hour, label: `${String(hour).padStart(2, "0")}:00` }));
const WEEKDAY_PRESET_OPTIONS = [
  { value: "legacy_interval", weekdays: null, labelKey: "importSettingsSyncLegacyInterval", fallback: "Legacy interval" },
  { value: "every_day", weekdays: [0, 1, 2, 3, 4, 5, 6], labelKey: "importSettingsSyncEveryDay", fallback: "Every day" },
  { value: "mon_wed_fri", weekdays: [0, 2, 4], labelKey: "importSettingsSyncMonWedFri", fallback: "Mon / Wed / Fri" },
  { value: "tue_thu_sat", weekdays: [1, 3, 5], labelKey: "importSettingsSyncTueThuSat", fallback: "Tue / Thu / Sat" },
  { value: "mon_thu", weekdays: [0, 3], labelKey: "importSettingsSyncMonThu", fallback: "Mon / Thu" },
];
const IMPORT_ENTRY_LIMIT_OPTIONS = [10, 25, 50, 100, 150, 200];
const SCHEDULER_TICK_OPTIONS = [1, 5, 10, 30, 60];
const VALIDATION_BATCH_SIZE_OPTIONS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

export function ImportSettingsSection({
  t,
  settingsQuery,
  saveMutation,
  importSettings,
  canManageImportSettings,
  canDeleteImportData,
  deleteImportDataMutation,
  onChange,
  onSubmit,
}) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteOtp, setDeleteOtp] = useState("");
  const [deleteChallenge, setDeleteChallenge] = useState(null);
  const requestDeleteOtp = useMutation({
    mutationFn: () => requestAdminActionOtp({ action_key: "delete_import_data" }),
    onSuccess: (data) => {
      setDeleteChallenge(data);
      setDeleteOtp("");
      setDeleteDialogOpen(true);
    },
  });

  function confirmDeleteImportData() {
    if (!deleteChallenge?.challenge_id) return;
    deleteImportDataMutation.mutate(
      { challenge_id: deleteChallenge.challenge_id, otp: deleteOtp },
      {
        onSuccess: () => {
          setDeleteDialogOpen(false);
          setDeleteOtp("");
          setDeleteChallenge(null);
        },
      },
    );
  }

  return (
    <Stack component="form" spacing={2} onSubmit={onSubmit}>
      {settingsQuery.isError && <Alert severity="error">{settingsQuery.error.message || t.loadError}</Alert>}
      {saveMutation.isSuccess && <Alert severity="success">{t.settingsSaved}</Alert>}
      {saveMutation.isError && <Alert severity="error">{saveMutation.error.message || t.saveError}</Alert>}
      {deleteImportDataMutation?.isSuccess && <Alert severity="success">{t.deleteAllImportDataSuccess}</Alert>}
      {requestDeleteOtp.isError && <Alert severity="error">{requestDeleteOtp.error.message || t.actionError}</Alert>}
      {!canManageImportSettings && <Alert severity="info">{t.importSettingsReadOnly || "Import settings are read-only for this account."}</Alert>}
      <Stack spacing={0.5}>
        <Typography variant="subtitle1">{t.importSettingsGoogleDocTitle || "Google Doc import"}</Typography>
        <Typography variant="body2" color="text.secondary">
          {t.importSettingsGoogleDocDescription || "Controls automatic Google Doc sync and word details enrichment."}
        </Typography>
      </Stack>
      <FormControlLabel
        control={
          <Switch
            checked={Boolean(importSettings.enrich_after_google_doc_import_enabled)}
            onChange={(event) => onChange("enrich_after_google_doc_import_enabled", event.target.checked)}
            disabled={!canManageImportSettings}
          />
        }
        label={t.importSettingsImmediateEnrichment || "Fill word details immediately after Google Doc import"}
      />
      <FormControlLabel
        control={
          <Switch
            checked={Boolean(importSettings.embedding_build_enabled)}
            onChange={(event) => onChange("embedding_build_enabled", event.target.checked)}
            disabled={!canManageImportSettings}
          />
        }
        label={t.importSettingsEmbeddingBuildEnabled || "Build embeddings for imported user words"}
      />
      <TextField
        select
        label={t.importSettingsAttributeBuildHour || "Word details job time"}
        value={Number(importSettings.attribute_build_hour)}
        onChange={(event) => onChange("attribute_build_hour", Number(event.target.value))}
        disabled={!canManageImportSettings}
        fullWidth
      >
        {HOUR_OPTIONS.map((option) => (
          <MenuItem key={`attribute-${option.value}`} value={option.value}>{option.label}</MenuItem>
        ))}
      </TextField>
      <TextField
        select
        label={t.importSettingsAttributeBuildWeekdays || "Word details job days"}
        value={weekdayPresetValue(importSettings.attribute_build_weekdays)}
        onChange={(event) => onChange("attribute_build_weekdays", weekdaysForPreset(event.target.value))}
        helperText={t.importSettingsAttributeBuildWeekdayHint || "Weekdays are counted from Monday."}
        disabled={!canManageImportSettings}
        fullWidth
      >
        {WEEKDAY_PRESET_OPTIONS.map((option) => (
          <MenuItem key={`attribute-days-${option.value}`} value={option.value}>{formatWeekdayPresetLabel(t, option, 1)}</MenuItem>
        ))}
      </TextField>
      <TextField
        select
        label={t.importSettingsAudioBuildHour || "Audio job time"}
        value={Number(importSettings.audio_build_hour)}
        onChange={(event) => onChange("audio_build_hour", Number(event.target.value))}
        helperText={t.importSettingsAudioBuildHourHint || "At the scheduled hour, audio is generated in batches until the queue is empty."}
        disabled={!canManageImportSettings}
        fullWidth
      >
        {HOUR_OPTIONS.map((option) => (
          <MenuItem key={`audio-${option.value}`} value={option.value}>{option.label}</MenuItem>
        ))}
      </TextField>
      <TextField
        select
        label={t.importSettingsAudioBuildWeekdays || "Audio job days"}
        value={weekdayPresetValue(importSettings.audio_build_weekdays)}
        onChange={(event) => onChange("audio_build_weekdays", weekdaysForPreset(event.target.value))}
        helperText={t.importSettingsAudioBuildWeekdayHint || "Weekdays are counted from Monday."}
        disabled={!canManageImportSettings}
        fullWidth
      >
        {WEEKDAY_PRESET_OPTIONS.map((option) => (
          <MenuItem key={`audio-days-${option.value}`} value={option.value}>{formatWeekdayPresetLabel(t, option, 1)}</MenuItem>
        ))}
      </TextField>
      <TextField
        select
        label={t.importSettingsGoogleDocSyncHour || "Google Doc sync time"}
        value={Number(importSettings.google_doc_sync_hour)}
        onChange={(event) => onChange("google_doc_sync_hour", Number(event.target.value))}
        disabled={!canManageImportSettings}
        fullWidth
      >
        {HOUR_OPTIONS.map((option) => (
          <MenuItem key={`sync-${option.value}`} value={option.value}>{option.label}</MenuItem>
        ))}
      </TextField>
      <TextField
        select
        label={t.importSettingsGoogleDocSyncInterval || "Google Doc sync days"}
        value={weekdayPresetValue(importSettings.google_doc_sync_weekdays)}
        onChange={(event) => onChange("google_doc_sync_weekdays", weekdaysForPreset(event.target.value))}
        helperText={t.importSettingsGoogleDocSyncWeekdayHint || "Weekdays are counted from Monday."}
        disabled={!canManageImportSettings}
        fullWidth
      >
        {WEEKDAY_PRESET_OPTIONS.map((option) => (
          <MenuItem key={option.value} value={option.value}>{formatWeekdayPresetLabel(t, option, importSettings.google_doc_sync_interval_days)}</MenuItem>
        ))}
      </TextField>
      <TextField
        select
        label={t.importSettingsSchedulerTickMinutes || "Scheduler tick interval"}
        value={Number(importSettings.scheduler_tick_minutes)}
        onChange={(event) => onChange("scheduler_tick_minutes", Number(event.target.value))}
        helperText={t.importSettingsSchedulerTickHint || "The background scheduler checks due import tasks at this interval."}
        disabled={!canManageImportSettings}
        fullWidth
      >
        {SCHEDULER_TICK_OPTIONS.map((minutes) => (
          <MenuItem key={minutes} value={minutes}>{formatTickLabel(t, minutes)}</MenuItem>
        ))}
      </TextField>
      <TextField
        select
        label={t.importSettingsMaxEntries || "Imported words per submission"}
        value={Number(importSettings.max_import_entries_per_submission)}
        onChange={(event) => onChange("max_import_entries_per_submission", Number(event.target.value))}
        disabled={!canManageImportSettings}
        fullWidth
      >
        {IMPORT_ENTRY_LIMIT_OPTIONS.map((count) => (
          <MenuItem key={count} value={count}>{count}</MenuItem>
        ))}
      </TextField>
      <TextField
        select
        label={t.importSettingsValidationBatchSize || "AI validation batch size"}
        value={Number(importSettings.validation_batch_size)}
        onChange={(event) => onChange("validation_batch_size", Number(event.target.value))}
        disabled={!canManageImportSettings}
        fullWidth
      >
        {VALIDATION_BATCH_SIZE_OPTIONS.map((count) => (
          <MenuItem key={count} value={count}>{count}</MenuItem>
        ))}
      </TextField>
      <Button type="submit" variant="contained" disabled={!canManageImportSettings || saveMutation.isPending || settingsQuery.isLoading}>
        {saveMutation.isPending ? t.saving : t.save}
      </Button>
      {canDeleteImportData && (
        <>
          <Divider />
          <Stack spacing={1}>
            <Typography variant="subtitle1" color="error">{t.dangerZone}</Typography>
            <Typography variant="body2" color="text.secondary">{t.deleteAllImportDataDescription}</Typography>
            <Button
              type="button"
              color="error"
              variant="outlined"
              startIcon={<Trash2 size={16} />}
              disabled={requestDeleteOtp.isPending || deleteImportDataMutation?.isPending}
              onClick={() => requestDeleteOtp.mutate()}
            >
              {t.deleteAllImportData}
            </Button>
          </Stack>
          <DangerousActionOtpDialog
            t={t}
            open={deleteDialogOpen}
            title={t.deleteAllImportDataConfirmTitle}
            text={t.deleteAllImportDataConfirmText}
            otp={deleteOtp}
            devOtpHint={deleteChallenge?.dev_otp_hint}
            error={deleteImportDataMutation?.isError ? deleteImportDataMutation.error.message || t.actionError : ""}
            pending={Boolean(deleteImportDataMutation?.isPending)}
            onOtpChange={setDeleteOtp}
            onCancel={() => {
              setDeleteDialogOpen(false);
              setDeleteOtp("");
            }}
            onConfirm={confirmDeleteImportData}
          />
        </>
      )}
    </Stack>
  );
}

export function weekdayPresetValue(weekdays) {
  if (weekdays == null) {
    return "legacy_interval";
  }
  const normalized = normalizeWeekdays(weekdays);
  const match = WEEKDAY_PRESET_OPTIONS.find((option) => sameWeekdays(option.weekdays, normalized));
  return match?.value || "mon_wed_fri";
}

export function weekdaysForPreset(value) {
  const match = WEEKDAY_PRESET_OPTIONS.find((option) => option.value === value);
  if (match?.weekdays == null) {
    return null;
  }
  return [...match.weekdays];
}

function normalizeWeekdays(weekdays) {
  if (!Array.isArray(weekdays) || weekdays.length === 0) {
    return [];
  }
  return [...new Set(weekdays.map((value) => Number(value)).filter((value) => Number.isInteger(value)))].sort((left, right) => left - right);
}

function sameWeekdays(left, right) {
  if (!Array.isArray(left) || !Array.isArray(right)) {
    return false;
  }
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

function formatWeekdayPresetLabel(t, option, intervalDays) {
  if (option.value === "legacy_interval") {
    const days = Number(intervalDays) || 3;
    if (typeof t.importSettingsEveryDays === "string") {
      return t.importSettingsEveryDays.replace("{days}", String(days));
    }
    return `Every ${days} day${days === 1 ? "" : "s"}`;
  }
  return t[option.labelKey] || option.fallback;
}

function formatTickLabel(t, minutes) {
  if (typeof t.importSettingsSchedulerEveryMinutes === "string") {
    return t.importSettingsSchedulerEveryMinutes.replace("{minutes}", String(minutes));
  }
  return `Every ${minutes} min`;
}
