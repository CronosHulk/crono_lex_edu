import { Box, Button, Chip, Divider, IconButton, Paper, Stack, Tab, Tabs, Tooltip, Typography } from "@mui/material";
import { ArrowLeft, ArrowRight, CirclePlay, Play, Volume2, X } from "lucide-react";
import { useState } from "react";
import { Link as RouterLink, useSearchParams } from "react-router-dom";

import { useAnswerTraining, useCardAction, useContinueTraining, useFinishTraining, useLearningState, useReadyAction, useStartTraining } from "./api/learningApi";
import { LearningWordTable } from "./components/LearningWordTable";
import {
  escapeRegExp,
  isQuizOptionDisabled,
  parseProgressRows,
  progressSymbolColor,
  progressSymbolLabel,
  quizOptionFeedbackSx,
  readFeedbackOptionLabels,
  readQuizOptionFeedbackState,
  readQuizOptionLabel,
} from "./helpers/trainingExerciseHelpers";
import { playAudio } from "../../shared/helpers/audio";
import { useClientI18n } from "../../shared/i18n/clientI18n";

const LEARNING_TABS = new Set(["training", "learning", "learned"]);

export function LearningPage() {
  const { t } = useClientI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = LEARNING_TABS.has(searchParams.get("tab")) ? searchParams.get("tab") : "training";
  const topicFilter = searchParams.get("topic") || "";

  function setTab(tabValue) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.set("tab", tabValue);
      if (tabValue !== "learning") next.delete("topic");
      return next;
    });
  }

  function openTopic(topic) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.set("tab", "learning");
      next.set("topic", topic);
      next.set("page", "1");
      return next;
    });
  }

  return (
    <Stack spacing={2}>
      <Typography variant="h5" component="h1" fontWeight={700}>{t("navWordLearning")}</Typography>
      <Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable" scrollButtons="auto">
        <Tab component={RouterLink} to={learningTabPath("training")} value="training" label={t("tabTraining")} />
        <Tab component={RouterLink} to={learningTabPath("learning", topicFilter)} value="learning" label={t("tabLearning")} />
        <Tab component={RouterLink} to={learningTabPath("learned")} value="learned" label={t("tabLearned")} />
      </Tabs>
      {tab === "training" && <TrainingTab onOpenTopic={openTopic} />}
      {tab === "learning" && <LearningWordTable mode="learning" topicFilter={topicFilter} />}
      {tab === "learned" && <LearningWordTable mode="learned" allowReviewAction />}
    </Stack>
  );
}

function learningTabPath(tab, topic = "") {
  const params = new URLSearchParams({ tab });
  if (tab === "learning" && topic) params.set("topic", topic);
  return `/learning?${params.toString()}`;
}

export function HomeworkPage() {
  const { t } = useClientI18n();
  return (
    <Paper variant="outlined" sx={{ p: 2, borderColor: "divider" }}>
      <Typography variant="h6" component="h1" fontWeight={700}>{t("navHomework")}</Typography>
    </Paper>
  );
}

function TrainingTab({ onOpenTopic }) {
  const { t } = useClientI18n();
  const state = useLearningState();
  const start = useStartTraining();
  const resume = useContinueTraining();
  const finish = useFinishTraining();
  const answer = useAnswerTraining();
  const cardAction = useCardAction();
  const readyAction = useReadyAction();
  const [acceptedSessionId, setAcceptedSessionId] = useState(null);
  const [quizFeedback, setQuizFeedback] = useState(null);
  const session = state.data?.active_session;
  const blocked = session && !session.is_owned_by_web;
  const isAccepted = session && acceptedSessionId === session.id;

  function startTraining() {
    start.mutate(undefined, { onSuccess: (data) => setAcceptedSessionId(data?.active_session?.id ?? null) });
  }

  function resumeTraining() {
    resume.mutate(undefined, { onSuccess: (data) => setAcceptedSessionId(data?.active_session?.id ?? session?.id ?? null) });
  }

  function answerTraining(payload, exercise) {
    setQuizFeedback({
      sessionWordId: payload.session_word_id,
      exercise,
      selectedIndex: payload.option_index,
      optionLabels: exercise.options,
    });
    answer.mutate(payload, {
      onSuccess: (data) => {
        const feedbackLabels = readFeedbackOptionLabels(data, exercise.options);
        setQuizFeedback({
          sessionWordId: payload.session_word_id,
          exercise,
          selectedIndex: payload.option_index,
          optionLabels: feedbackLabels,
          isResolved: true,
        });
        window.setTimeout(
          () => setQuizFeedback(null),
          Number(data?.screen?.metadata?.auto_advance_after_ms) || 1500,
        );
      },
      onError: () => setQuizFeedback(null),
    });
  }

  return (
    <Box sx={{ minHeight: "60vh", display: "grid", placeItems: "center" }}>
      <Paper variant="outlined" sx={{ width: "min(100%, 420px)", p: 3, borderColor: "divider" }}>
        <Stack spacing={2}>
          {!session || blocked || !isAccepted ? (
            <>
              {blocked && <Typography color="text.secondary">{t("telegramClaimed")}</Typography>}
              <Button variant="contained" startIcon={<Play size={18} />} onClick={startTraining} disabled={start.isPending}>
                {t("startTraining")}
              </Button>
              <Button variant="outlined" startIcon={<CirclePlay size={18} />} onClick={resumeTraining} disabled={resume.isPending}>
                {t("resumeLesson")}
              </Button>
            </>
          ) : (
            <TrainingExercise
              session={session}
              onOpenTopic={onOpenTopic}
              onCardAction={(payload) => cardAction.mutate(payload)}
              onAnswer={answerTraining}
              onReadyAction={(payload) => readyAction.mutate(payload)}
              onCancel={() => setAcceptedSessionId(null)}
              onFinish={() => finish.mutate(undefined, { onSuccess: () => setAcceptedSessionId(null) })}
              isReadyPending={readyAction.isPending}
              isAnswerPending={answer.isPending}
              isFinishPending={finish.isPending}
              quizFeedback={quizFeedback}
            />
          )}
        </Stack>
      </Paper>
    </Box>
  );
}

function TrainingExercise({
  session,
  onOpenTopic,
  onCardAction,
  onAnswer,
  onReadyAction,
  onCancel,
  onFinish,
  isReadyPending,
  isAnswerPending,
  isFinishPending,
  quizFeedback,
}) {
  const { t } = useClientI18n();
  const exercise = quizFeedback?.exercise || session.exercise;
  if (!exercise) {
    return <ReadyExerciseFallback onCancel={onCancel} />;
  }
  if (exercise.type === "ready") {
    return <ReadyExercise exercise={exercise} onReadyAction={onReadyAction} onCancel={onCancel} isPending={isReadyPending} />;
  }
  if (exercise.type === "summary") {
    return <SummaryExercise exercise={exercise} onFinish={onFinish} isPending={isFinishPending} />;
  }
  if (exercise.type === "card") {
    return (
      <>
        <Stack spacing={0.75}>
          <Typography variant="subtitle2" color="text.secondary">{t("cardIntro")}</Typography>
          <LessonProgress exercise={exercise} />
        </Stack>
        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
          <Typography variant="h4" component="div" fontWeight={700}>{exercise.word}</Typography>
          {exercise.audio_url && (
            <Tooltip title={t("listenPronunciation")}>
              <IconButton
                color="primary"
                aria-label={t("listenWordPronunciation", { word: exercise.word })}
                onClick={() => playAudio(exercise.audio_url)}
              >
                <Volume2 />
              </IconButton>
            </Tooltip>
          )}
        </Stack>
        <Typography color="text.secondary">{exercise.transcription}</Typography>
        <Typography sx={{ fontSize: "1.4rem", fontWeight: 500, lineHeight: 1.45 }}>{exercise.translation || exercise.translation_uk}</Typography>
        <ExampleList word={exercise.word} examples={exercise.examples || []} />
        <TopicTags topics={exercise.categories || []} onOpenTopic={onOpenTopic} />
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <Button
            variant="outlined"
            startIcon={<ArrowLeft size={18} />}
            disabled={!exercise.can_go_back}
            onClick={() => onCardAction({ session_word_id: exercise.session_word_id, action: "back" })}
            fullWidth
          >
            {t("back")}
          </Button>
          <Button
            variant="contained"
            endIcon={<ArrowRight size={18} />}
            onClick={() => onCardAction({ session_word_id: exercise.session_word_id, action: exercise.next_action || "next" })}
            fullWidth
          >
            {exercise.next_action === "quiz" ? t("toExercises") : t("forward")}
          </Button>
        </Stack>
        <Button variant="outlined" onClick={() => onCardAction({ session_word_id: exercise.session_word_id, action: "known" })}>{t("alreadyKnow")}</Button>
      </>
    );
  }
  return (
    <>
      <Stack spacing={1}>
        <Typography variant="subtitle2" color="text.secondary">{exercise.title}</Typography>
        <LessonProgress exercise={exercise} />
      </Stack>
      {exercise.is_repeat && (
        <Box className="learning-repeat-notice-wrap">
          <Typography className="learning-repeat-notice" variant="caption">
            {t("repeatMistakeWord")}
          </Typography>
        </Box>
      )}
      <Box sx={{ pt: 2, pb: 2, width: "100%", display: "flex", justifyContent: "center" }}>
        <Typography variant="h5" fontWeight={700} sx={{ textAlign: "center" }}>
          {exercise.prompt}
        </Typography>
      </Box>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          gap: 1,
        }}
      >
        {exercise.options.map((option, index) => {
          const optionLabel = readQuizOptionLabel(quizFeedback, exercise, index, option);
          const feedbackState = readQuizOptionFeedbackState(quizFeedback, exercise, index, optionLabel);
          return (
            <Button
              key={`${option}:${index}`}
              variant="outlined"
              disabled={isQuizOptionDisabled(quizFeedback, exercise, feedbackState, isAnswerPending)}
              onClick={() => onAnswer({ session_word_id: exercise.session_word_id, option_index: index }, exercise)}
              sx={{
                minHeight: 44,
                whiteSpace: "normal",
                lineHeight: 1.2,
                ...(feedbackState ? { pointerEvents: "none" } : {}),
                ...quizOptionFeedbackSx(feedbackState),
              }}
            >
              {optionLabel}
            </Button>
          );
        })}
      </Box>
    </>
  );
}

function ReadyExercise({ exercise, onReadyAction, onCancel, isPending }) {
  const { t } = useClientI18n();
  return (
    <>
      <Stack spacing={0.75}>
        <Typography variant="subtitle2" color="text.secondary">{exercise.title}</Typography>
        <Typography>{exercise.prompt}</Typography>
      </Stack>
      <Button
        variant="contained"
        endIcon={<ArrowRight size={18} />}
        disabled={isPending}
        onClick={() => onReadyAction({ expected_stage: exercise.stage, decision: "yes" })}
      >
        {t("continue")}
      </Button>
      <Button variant="outlined" startIcon={<X size={18} />} onClick={onCancel}>
        {t("cancel")}
      </Button>
    </>
  );
}

function SummaryExercise({ exercise, onFinish, isPending }) {
  return (
    <>
      <Stack spacing={1}>
        <Typography variant="subtitle2" color="text.secondary">{exercise.title}</Typography>
        <SummaryPrompt text={exercise.prompt} />
      </Stack>
      <Button variant="contained" endIcon={<ArrowRight size={18} />} onClick={onFinish} disabled={isPending}>
        {exercise.finish_label}
      </Button>
    </>
  );
}

function SummaryPrompt({ text }) {
  const { t } = useClientI18n();
  const summaryMasteryHint = t("summaryMasteryHint");
  return (
    <Stack spacing={0.75}>
      {String(text || "").split("\n").map((line, index) => {
        if (line.trim() === summaryMasteryHint) {
          return (
            <Box
              key={`${line}:${index}`}
              component="blockquote"
              sx={{
                m: 0,
                pl: 1.5,
                py: 0.5,
                borderLeft: 2,
                borderColor: "divider",
                color: "text.secondary",
                fontSize: "0.8125rem",
                fontStyle: "italic",
                lineHeight: 1.45,
              }}
            >
              {line}
            </Box>
          );
        }
        return (
          <Typography key={`${line}:${index}`} sx={{ minHeight: line ? undefined : "0.75rem", lineHeight: 1.5 }}>
            {line}
          </Typography>
        );
      })}
    </Stack>
  );
}

function ReadyExerciseFallback({ onCancel }) {
  const { t } = useClientI18n();
  return (
    <>
      <Typography color="text.secondary">{t("readyFallback")}</Typography>
      <Button variant="outlined" startIcon={<X size={18} />} onClick={onCancel}>
        {t("cancel")}
      </Button>
    </>
  );
}

function LessonProgress({ exercise }) {
  const { t } = useClientI18n();
  const rows = parseProgressRows(exercise.progress_bar);
  return (
    <Stack spacing={0.75} sx={{ width: "100%", alignItems: "center" }}>
      <Divider sx={{ width: "100%" }} />
      <Stack spacing={0.35} sx={{ width: "100%", alignItems: "center" }} aria-label={t("lessonProgress")}>
        {rows.map((symbols, rowIndex) => (
          <Stack
            key={`progress-row:${rowIndex}`}
            component="span"
            direction="row"
            spacing={0.4}
            sx={{ display: "inline-flex", alignItems: "center" }}
          >
            {symbols.map((symbol, index) => (
              <Box
                key={`${rowIndex}:${symbol}:${index}`}
                component="span"
                sx={{ color: progressSymbolColor(symbol), fontWeight: 700, lineHeight: 1 }}
              >
                {progressSymbolLabel(symbol)}
              </Box>
            ))}
          </Stack>
        ))}
      </Stack>
      <Divider sx={{ width: "100%" }} />
    </Stack>
  );
}

function ExampleList({ word, examples }) {
  if (!examples.length) return null;
  return (
    <Stack component="blockquote" spacing={1} sx={{ m: 0, pl: 2, py: 0.5, borderLeft: 3, borderColor: "primary.main" }}>
      {examples.map((example, index) => (
        <Typography
          key={`${example}:${index}`}
          color="text.secondary"
          sx={{ fontSize: "1.15rem", fontStyle: "italic", lineHeight: 1.55 }}
        >
          {highlightWord(example, word)}
        </Typography>
      ))}
    </Stack>
  );
}

function TopicTags({ topics, onOpenTopic }) {
  if (!topics.length) return null;
  return (
    <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
      {topics.map((topic) => (
        <Chip key={topic} label={`#${topic}`} size="small" clickable onClick={() => onOpenTopic(topic)} />
      ))}
    </Stack>
  );
}

function highlightWord(example, word) {
  const normalizedWord = String(word || "").trim();
  if (!normalizedWord) return example;
  const pattern = new RegExp(`(${escapeRegExp(normalizedWord)})`, "ig");
  return String(example).split(pattern).map((part, index) => {
    if (part.toLowerCase() === normalizedWord.toLowerCase()) {
      return <Box key={`${part}:${index}`} component="strong" sx={{ color: "text.primary", fontStyle: "italic" }}>{part}</Box>;
    }
    return part;
  });
}
