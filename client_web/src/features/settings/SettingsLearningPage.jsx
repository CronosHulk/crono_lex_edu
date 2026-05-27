import { Alert, Button, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useState } from "react";

import { useClientI18n } from "../../shared/i18n/clientI18n";
import { useSaveSettings, useSettings } from "./api/settingsApi";

export function SettingsLearningPage() {
  const { t } = useClientI18n();
  const settings = useSettings();
  const save = useSaveSettings();
  const profile = settings.data?.profile || {};
  const levels = settings.data?.levels || [];
  const wordsPerSessionOptions = settings.data?.words_per_session_options || [];
  const [languageLevel, setLanguageLevel] = useState("");
  const [wordsPerSession, setWordsPerSession] = useState("");

  useEffect(() => {
    if (!settings.data) return;
    setLanguageLevel(String(profile.language_level_title || ""));
    setWordsPerSession(profile.words_per_session ? String(profile.words_per_session) : "");
  }, [profile.language_level_title, profile.words_per_session, settings.data]);

  const hasLevelOptions = levels.length > 0;
  const hasWordsOptions = wordsPerSessionOptions.length > 0;
  const canSave = hasLevelOptions && hasWordsOptions && languageLevel && wordsPerSession && !save.isPending;

  function submit(event) {
    event.preventDefault();
    if (!canSave) return;
    save.mutate({
      language_level: languageLevel,
      words_per_session: Number(wordsPerSession),
    });
  }

  if (settings.isPending) {
    return (
      <Paper variant="outlined" sx={{ width: "min(100%, 560px)", p: { xs: 2, sm: 3 }, borderColor: "divider" }}>
        <Typography>{t("loading")}</Typography>
      </Paper>
    );
  }

  return (
    <Paper variant="outlined" sx={{ width: "min(100%, 560px)", p: { xs: 2, sm: 3 }, borderColor: "divider" }}>
      <Stack component="form" spacing={2} onSubmit={submit}>
        <Stack spacing={0.5}>
          <Typography variant="h6" fontWeight={700}>{t("learningSettingsTitle")}</Typography>
          <Typography variant="body2" color="text.secondary">{t("learningSettingsSubtitle")}</Typography>
        </Stack>
        {settings.isError && <Alert severity="error">{settings.error.message}</Alert>}
        {save.isSuccess && <Alert severity="success">{t("settingsSaved")}</Alert>}
        {save.isError && <Alert severity="error">{save.error.message}</Alert>}
        <TextField
          select
          label={t("learningSettingsLevel")}
          value={languageLevel}
          onChange={(event) => setLanguageLevel(event.target.value)}
          disabled={!hasLevelOptions || save.isPending}
          fullWidth
        >
          {levels.map((level) => (
            <MenuItem key={level} value={level}>{level}</MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label={t("learningSettingsWordsPerSession")}
          value={wordsPerSession}
          onChange={(event) => setWordsPerSession(event.target.value)}
          disabled={!hasWordsOptions || save.isPending}
          fullWidth
        >
          {wordsPerSessionOptions.map((count) => (
            <MenuItem key={count} value={String(count)}>{count}</MenuItem>
          ))}
        </TextField>
        <Button type="submit" variant="contained" disabled={!canSave}>
          {t("saveChanges")}
        </Button>
      </Stack>
    </Paper>
  );
}
