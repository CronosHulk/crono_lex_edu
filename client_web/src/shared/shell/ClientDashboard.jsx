import { Box, Button, Card, CardContent, Chip, Divider, Stack, Typography } from "@mui/material";
import { BookOpen, Clock, Import, Play, Settings, Trophy } from "lucide-react";
import { Link as RouterLink } from "react-router-dom";

import { useLearningState, useLearningWords } from "../../features/learning/api/learningApi";
import { useSettings } from "../../features/settings/api/settingsApi";
import { useClientI18n } from "../i18n/clientI18n";

export function ClientDashboard() {
  const { intlLocale, t } = useClientI18n();
  const state = useLearningState();
  const settings = useSettings();
  const learningWords = useLearningWords({ mode: "learning", page: 1, pageSize: 1 });
  const learnedWords = useLearningWords({ mode: "learned", page: 1, pageSize: 1 });
  const importedWords = useLearningWords({ mode: "imported_rotation", page: 1, pageSize: 1 });
  const profile = settings.data?.profile;
  const activeSession = state.data?.active_session;

  const cards = [
    {
      label: t("inProgress"),
      value: readTotal(learningWords, intlLocale),
      helper: t("wordsToAutomate"),
      trend: t("trainingBadge"),
      icon: <BookOpen />,
    },
    {
      label: t("learned"),
      value: readTotal(learnedWords, intlLocale),
      helper: t("learnedWithoutMistakes"),
      trend: t("stableBadge"),
      icon: <Trophy />,
    },
    {
      label: t("imported"),
      value: readTotal(importedWords, intlLocale),
      helper: t("personalRotationWords"),
      trend: t("dictionaryBadge"),
      icon: <Import />,
    },
  ];

  return (
    <Stack spacing={3}>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1.5fr) minmax(320px, 0.8fr)" },
          gap: 2,
        }}
      >
        <Card variant="outlined" sx={{ overflow: "hidden" }}>
          <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
            <Stack spacing={2.25}>
              <Typography variant="overline" color="text.secondary">{t("dashboardOverline")}</Typography>
              <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" }, gap: 1.5 }}>
                <SummaryMetric
                  icon={<BookOpen />}
                  label={t("wordTrainings")}
                  value={readTotal(learningWords, intlLocale)}
                  helper={t("activeRotationWords")}
                />
              </Box>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25}>
                <Button component={RouterLink} to="/learning?tab=training" variant="contained" startIcon={<Play />}>
                  {t("startTraining")}
                </Button>
              </Stack>
            </Stack>
          </CardContent>
        </Card>
        <Card variant="outlined">
          <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
            <Stack spacing={2}>
              <Stack direction="row" spacing={1.5} alignItems="center">
                <Box sx={{ display: "grid", placeItems: "center", width: 42, height: 42, borderRadius: 2, bgcolor: "primary.main", color: "primary.contrastText" }}>
                  <Clock />
                </Box>
                <Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{t("currentMode")}</Typography>
                  <Typography variant="body2" color="text.secondary">{activeSession ? t("activeLesson") : t("lessonNotStarted")}</Typography>
                </Box>
              </Stack>
              <Divider />
              <DashboardFact label={t("level")} value={profile?.language_level_title || "-"} />
              <DashboardFact label={t("wordsInTraining")} value={String(profile?.words_per_session || "-")} />
              <DashboardFact label={t("reminder")} value={formatReminder(profile, t)} />
              <Button component={RouterLink} to="/settings/reminders" variant="text" startIcon={<Settings />} sx={{ alignSelf: "flex-start" }}>
                {t("configure")}
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" }, gap: 2 }}>
        {cards.map((card) => (
          <StatCard key={card.label} {...card} />
        ))}
      </Box>

    </Stack>
  );
}

function StatCard({ label, value, helper, trend, icon }) {
  return (
    <Card variant="outlined">
      <CardContent sx={{ p: 2.5 }}>
        <Stack spacing={2}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
            <Box sx={{ display: "grid", placeItems: "center", width: 38, height: 38, borderRadius: 2, color: "primary.main", bgcolor: (theme) => theme.palette.mode === "dark" ? "rgba(92, 200, 167, 0.12)" : "rgba(99, 91, 255, 0.08)" }}>
              {icon}
            </Box>
            <Chip size="small" label={trend} />
          </Stack>
          <Box>
            <Typography variant="body2" color="text.secondary">{label}</Typography>
            <Typography variant="h4" sx={{ fontWeight: 800 }}>{value}</Typography>
          </Box>
          <Typography variant="body2" color="text.secondary">{helper}</Typography>
        </Stack>
      </CardContent>
    </Card>
  );
}

function DashboardFact({ label, value }) {
  return (
    <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2}>
      <Typography variant="body2" color="text.secondary">{label}</Typography>
      <Typography variant="body2" sx={{ fontWeight: 700 }}>{value}</Typography>
    </Stack>
  );
}

function SummaryMetric({ icon, label, value, helper }) {
  return (
    <Box
      sx={{
        p: 1.5,
        border: 1,
        borderColor: "divider",
        borderRadius: 2,
        display: "grid",
        gridTemplateColumns: "auto minmax(0, 1fr)",
        gap: 1.25,
        alignItems: "center",
      }}
    >
      <Box sx={{ display: "grid", placeItems: "center", width: 40, height: 40, borderRadius: 2, color: "primary.main", bgcolor: (theme) => theme.palette.mode === "dark" ? "rgba(92, 200, 167, 0.12)" : "rgba(99, 91, 255, 0.08)" }}>
        {icon}
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="body2" color="text.secondary">{label}</Typography>
        <Typography variant="h5" sx={{ fontWeight: 800, lineHeight: 1.1 }}>{value}</Typography>
        <Typography variant="caption" color="text.secondary">{helper}</Typography>
      </Box>
    </Box>
  );
}

function readTotal(query, intlLocale) {
  if (query.isLoading) return "...";
  return Number(query.data?.total || 0).toLocaleString(intlLocale);
}

function formatReminder(profile, t) {
  const rows = (profile?.reminder_schedule || []).filter((row) => row.status === "enabled");
  if (rows.length > 0) {
    const first = [...rows].sort((left, right) => left.weekday - right.weekday || left.hour - right.hour)[0];
    return `${formatHour(first.hour)} · ${rows.length}`;
  }
  const hour = profile?.daily_reminder_hour;
  if (hour === null || hour === undefined || hour === "") return t("notSet");
  return formatHour(hour);
}

function formatHour(hour) {
  return `${String(hour).padStart(2, "0")}:00`;
}
