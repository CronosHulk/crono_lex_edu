import {
  Alert,
  Box,
  Button,
  Chip,
  Collapse,
  Divider,
  FormControlLabel,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  Switch,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import { Bell, ChevronDown, Clock, Coffee, Moon, Pencil, Plus, Sun, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { useClientI18n } from "../../shared/i18n/clientI18n";
import { useSaveSettings, useSettings } from "./api/settingsApi";
import {
  REMINDER_HOURS,
  REMINDER_MINUTES,
  WEEKDAY_VALUES,
  defaultReminderTitle,
  exceedsWeekdayLimit,
  formatDays,
  formatTime,
  hasDuplicateReminderTime,
  hasRemainingWeekdayCapacity,
  normalizeReminderSchedule,
  rowsToRules,
  rulesToRows,
  weekdayShortOptions,
} from "./helpers/reminderSchedule";

const EMPTY_DRAFT = { title: "", weekdays: [0, 2, 4], hour: 9, minute: 0, status: "enabled" };

export function SettingsRemindersPage() {
  const { t } = useClientI18n();
  const settings = useSettings();
  const save = useSaveSettings();
  const profile = settings.data?.profile;
  const maxPerWeekday = settings.data?.subscription?.reminders_per_day || 1;
  const [rules, setRules] = useState([]);
  const [draft, setDraft] = useState({ ...EMPTY_DRAFT, title: t("reminderMorningTitle") });
  const [editingIndex, setEditingIndex] = useState(-1);
  const [isAddEditorExpanded, setAddEditorExpanded] = useState(false);
  const [hasManualEditorState, setHasManualEditorState] = useState(false);
  const [localError, setLocalError] = useState("");

  useEffect(() => {
    if (!profile) return;
    const rows = normalizeReminderSchedule(profile.reminder_schedule, profile);
    setRules(rowsToRules(rows, t));
    if (!hasManualEditorState) {
      setAddEditorExpanded(rows.length === 0);
    }
  }, [hasManualEditorState, profile, t]);

  useEffect(() => {
    if (draft.title) return;
    setDraft((current) => ({ ...current, title: defaultReminderTitle(current.hour, current.minute, t) }));
  }, [draft.title, draft.hour, draft.minute, t]);

  const preview = useMemo(
    () => t("reminderPreview", { days: formatDays(draft.weekdays, t), time: formatTime(draft.hour, draft.minute) }),
    [draft.hour, draft.minute, draft.weekdays, t],
  );
  const limitExceeded = exceedsWeekdayLimit(rules, draft, maxPerWeekday, editingIndex);
  const duplicateTime = hasDuplicateReminderTime(rules, draft, editingIndex);
  const canAddActiveReminder = hasRemainingWeekdayCapacity(rules, maxPerWeekday);
  const showAddSection = rules.length === 0 || editingIndex >= 0 || isAddEditorExpanded;
  const showEditor = showAddSection && (editingIndex >= 0 || canAddActiveReminder);
  const canApplyDraft = draft.title.trim().length > 0 && draft.weekdays.length > 0 && !limitExceeded && !duplicateTime;

  function openAddEditor() {
    setAddEditorExpanded(true);
    setHasManualEditorState(true);
    setEditingIndex(-1);
    setLocalError("");
  }

  function applyPreset(preset) {
    if (preset === "morning") {
      setDraft({ title: t("reminderMorningTitle"), weekdays: [0, 1, 2, 3, 4], hour: 9, minute: 0, status: "enabled" });
    }
    if (preset === "day") {
      setDraft({ title: t("reminderDayTitle"), weekdays: [0, 2, 4], hour: 14, minute: 0, status: "enabled" });
    }
    if (preset === "evening") {
      setDraft({ title: t("reminderEveningTitle"), weekdays: WEEKDAY_VALUES, hour: 20, minute: 30, status: "enabled" });
    }
    setLocalError("");
  }

  function applyDraft() {
    if (!canApplyDraft) {
      setLocalError(
        limitExceeded
          ? t("reminderLimitError", { count: maxPerWeekday })
          : duplicateTime
            ? t("reminderDuplicateError")
            : t("reminderRequiredError")
      );
      return;
    }
    const nextRule = {
      ...draft,
      title: draft.title.trim(),
      weekdays: [...draft.weekdays].sort((left, right) => left - right),
    };
    const nextRules = editingIndex < 0
      ? [...rules, nextRule]
      : rules.map((rule, index) => (index === editingIndex ? nextRule : rule));
    setRules(nextRules);
    saveRules(nextRules);
    setDraft({ ...EMPTY_DRAFT, title: t("reminderMorningTitle") });
    setEditingIndex(-1);
    setAddEditorExpanded(true);
    setHasManualEditorState(true);
    setLocalError("");
  }

  function editRule(index) {
    setDraft({ ...rules[index], weekdays: [...rules[index].weekdays] });
    setEditingIndex(index);
    setAddEditorExpanded(true);
    setHasManualEditorState(true);
    setLocalError("");
  }

  function deleteRule(index) {
    const nextRules = rules.filter((_rule, ruleIndex) => ruleIndex !== index);
    setRules(nextRules);
    saveRules(nextRules);
    if (editingIndex === index) {
      setEditingIndex(-1);
      setDraft({ ...EMPTY_DRAFT, title: t("reminderMorningTitle") });
    }
    if (nextRules.length === 0) {
      setAddEditorExpanded(true);
    }
  }

  function toggleRule(index) {
    const nextRules = rules.map((rule, ruleIndex) =>
      ruleIndex === index ? { ...rule, status: rule.status === "enabled" ? "disabled" : "enabled" } : rule
    );
    setRules(nextRules);
    saveRules(nextRules);
  }

  function saveRules(nextRules) {
    save.mutate({ reminder_schedule: rulesToRows(nextRules) });
  }

  return (
    <Paper variant="outlined" sx={{ width: "min(100%, 720px)", p: { xs: 2, sm: 3 }, borderColor: "divider" }}>
      <Stack spacing={3}>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <Box sx={{ display: "grid", placeItems: "center", width: 42, height: 42, borderRadius: 2, bgcolor: (theme) => alpha(theme.palette.primary.main, 0.12), color: "primary.main" }}>
            <Bell />
          </Box>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="h6" fontWeight={800}>{t("reminderSchedule")}</Typography>
            <Typography variant="body2" color="text.secondary">{t("reminderScheduleSubtitle")}</Typography>
          </Box>
        </Stack>

        {save.isSuccess && <Alert severity="success">{t("settingsSaved")}</Alert>}
        {save.isError && <Alert severity="error">{save.error.message}</Alert>}
        {localError && <Alert severity="warning">{localError}</Alert>}

        <Stack spacing={1.25}>
          {rules.length === 0 ? (
            <Typography variant="body2" color="text.secondary">{t("reminderScheduleEmpty")}</Typography>
          ) : (
            rules.map((rule, index) => (
              <ReminderRuleRow
                key={`${rule.hour}:${rule.minute}:${rule.status}:${rule.weekdays.join("-")}:${index}`}
                rule={rule}
                onToggle={() => toggleRule(index)}
                onEdit={() => editRule(index)}
                onDelete={() => deleteRule(index)}
                t={t}
              />
            ))
          )}
        </Stack>

        <Divider />

        {rules.length > 0 && editingIndex < 0 && !isAddEditorExpanded && (
          <Button
            type="button"
            variant="text"
            startIcon={<Plus />}
            endIcon={<ChevronDown />}
            onClick={openAddEditor}
            sx={{ alignSelf: "flex-start" }}
          >
            {t("addNewReminder")}
          </Button>
        )}

        <Collapse in={showAddSection} timeout="auto" unmountOnExit>
          <Stack spacing={1.5}>
            {showEditor ? (
              <Stack spacing={1.5}>
                <Typography variant="subtitle1" fontWeight={800}>{t("quickSetup")}</Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  <Button variant="outlined" startIcon={<Coffee />} onClick={() => applyPreset("morning")}>{t("morning")}</Button>
                  <Button variant="outlined" startIcon={<Sun />} onClick={() => applyPreset("day")}>{t("daytime")}</Button>
                  <Button variant="outlined" startIcon={<Moon />} onClick={() => applyPreset("evening")}>{t("evening")}</Button>
                </Stack>
              </Stack>
            ) : (
              <Alert severity="info">{t("reminderLimitReached")}</Alert>
            )}

            {showEditor && <Box sx={{ border: 1, borderColor: "divider", borderRadius: 2, p: { xs: 2, sm: 2.5 } }}>
          <Stack spacing={2}>
            <Typography variant="subtitle1" fontWeight={800}>
              {editingIndex >= 0 ? t("editReminder") : t("newReminder")}
            </Typography>
            <TextField
              label={t("name")}
              value={draft.title}
              onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))}
              fullWidth
            />
            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{t("trainingDays")}</Typography>
              <ToggleButtonGroup
                value={draft.weekdays}
                onChange={(_event, value) => setDraft((current) => ({ ...current, weekdays: value }))}
                size="small"
                sx={{ flexWrap: "wrap", gap: 0.75, "& .MuiToggleButtonGroup-grouped": { border: 1, borderColor: "divider", borderRadius: "6px !important" } }}
              >
                {weekdayShortOptions(t).map((option) => (
                  <ToggleButton key={option.value} value={option.value} aria-label={option.full}>
                    {option.label}
                  </ToggleButton>
                ))}
              </ToggleButtonGroup>
            </Box>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25} alignItems={{ xs: "stretch", sm: "center" }}>
              <TextField
                select
                label={t("reminderHour")}
                value={draft.hour}
                onChange={(event) => setDraft((current) => ({ ...current, hour: Number(event.target.value) }))}
                sx={{ minWidth: 140 }}
              >
                {REMINDER_HOURS.map((hour) => <MenuItem key={hour} value={hour}>{String(hour).padStart(2, "0")}</MenuItem>)}
              </TextField>
              <TextField
                select
                label={t("minute")}
                value={draft.minute}
                onChange={(event) => setDraft((current) => ({ ...current, minute: Number(event.target.value) }))}
                sx={{ minWidth: 120 }}
              >
                {REMINDER_MINUTES.map((minute) => <MenuItem key={minute} value={minute}>{String(minute).padStart(2, "0")}</MenuItem>)}
              </TextField>
              <FormControlLabel
                control={
                  <Switch
                    checked={draft.status === "enabled"}
                    onChange={(event) => setDraft((current) => ({ ...current, status: event.target.checked ? "enabled" : "disabled" }))}
                  />
                }
                label={t("active")}
              />
            </Stack>
            <Alert severity="success" icon={<Clock size={18} />}>{preview}</Alert>
            {limitExceeded && <Alert severity="warning">{t("reminderLimitError", { count: maxPerWeekday })}</Alert>}
            {duplicateTime && <Alert severity="warning">{t("reminderDuplicateError")}</Alert>}
            <Button type="button" variant="contained" startIcon={<Plus />} onClick={applyDraft} disabled={!canApplyDraft || save.isPending}>
              {editingIndex >= 0 ? t("updateReminder") : t("addReminder")}
            </Button>
          </Stack>
            </Box>}
          </Stack>
        </Collapse>
      </Stack>
    </Paper>
  );
}

function ReminderRuleRow({ rule, onToggle, onEdit, onDelete, t }) {
  const enabled = rule.status === "enabled";
  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: 2, p: 2 }}>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ xs: "stretch", sm: "center" }}>
        <Box sx={{ display: "grid", placeItems: "center", width: 42, height: 42, borderRadius: 2, color: enabled ? "primary.main" : "text.secondary", bgcolor: enabled ? (theme) => alpha(theme.palette.primary.main, 0.12) : "action.hover" }}>
          {rule.hour < 12 ? <Coffee /> : rule.hour < 18 ? <Sun /> : <Moon />}
        </Box>
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
            <Typography fontWeight={800}>{rule.title}</Typography>
            <Chip size="small" label={enabled ? t("enabled") : t("disabled")} color={enabled ? "success" : "default"} variant={enabled ? "filled" : "outlined"} />
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {formatDays(rule.weekdays, t)} {t("atTime")} {formatTime(rule.hour, rule.minute)}
          </Typography>
        </Box>
        <Stack direction="row" spacing={0.5} alignItems="center" justifyContent={{ xs: "flex-end", sm: "flex-start" }}>
          <Switch checked={enabled} onChange={onToggle} inputProps={{ "aria-label": t("toggleReminder") }} />
          <Tooltip title={t("edit")}>
            <IconButton type="button" aria-label={t("edit")} onClick={onEdit}>
              <Pencil />
            </IconButton>
          </Tooltip>
          <Tooltip title={t("delete")}>
            <IconButton type="button" aria-label={t("delete")} onClick={onDelete} color="error">
              <Trash2 />
            </IconButton>
          </Tooltip>
        </Stack>
      </Stack>
    </Box>
  );
}
