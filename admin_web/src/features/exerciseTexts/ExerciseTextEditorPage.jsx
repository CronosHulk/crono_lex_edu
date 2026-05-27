import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { ArrowLeft, Bot, FileText, Save, WandSparkles } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { CrudEditPage, CrudFormSurface, DetailPanel, JsonPreview, LoadingLine, MultiSelect } from "../../shared/components";
import { filterControlSx } from "../../shared/components/filterControls";
import { useExerciseTextEditor } from "./hooks/useExerciseTextEditor";

const DEFAULT_FORM = {
  difficultyBand: "",
  sourceText: "",
  textTypes: [],
  title: "",
  topicIds: [],
  voiceCode: "",
};
const TRANSLATION_TABS = ["uk", "ru", "pl"];
const STAGE_LABELS = {
  all: "Generate All",
  content: "Generate Content",
  quiz: "Generate Quiz",
  translations: "Generate Translations",
  tts: "Generate TTS",
};

export function ExerciseTextEditorPage({ exerciseTextId, t }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState(DEFAULT_FORM);
  const [formLoadedForId, setFormLoadedForId] = useState(null);
  const [error, setError] = useState("");
  const [needsForceSave, setNeedsForceSave] = useState(false);
  const [highlightedEvidence, setHighlightedEvidence] = useState(null);
  const [taskIds, setTaskIds] = useState([]);
  const [translationTab, setTranslationTab] = useState("uk");
  const {
    confirmParagraphStageMutation,
    detailQuery,
    generationMutation,
    grammarTopicsQuery,
    isNew,
    referenceQuery,
    saveMutation,
    taskQueries,
    ttsVoicesQuery,
  } = useExerciseTextEditor(exerciseTextId, taskIds);
  const detail = detailQuery.data || null;
  const content = detail?.content_jsonb || {};
  const generated = content.generated || {};
  const reference = referenceQuery.data || {};
  const grammarTopics = grammarTopicsQuery.data?.items || [];
  const ttsVoices = ttsVoicesQuery.data?.items || [];
  const loading = detailQuery.isFetching || referenceQuery.isFetching || grammarTopicsQuery.isFetching || ttsVoicesQuery.isFetching;
  const loadError = detailQuery.error || referenceQuery.error || grammarTopicsQuery.error || ttsVoicesQuery.error;
  const mutationError = saveMutation.error || generationMutation.error || confirmParagraphStageMutation.error;
  const backTo = location.state?.backTo || "/admin/exercise-texts";
  const title = isNew ? t.create || "Create" : detail?.title || generated.title || `ID: ${exerciseTextId}`;
  const taskRows = taskQueries.map((query) => query.data?.task).filter(Boolean);

  useEffect(() => {
    const nextId = detail?.id || "new";
    if (!isNew && detail && formLoadedForId !== nextId) {
      setForm(buildForm(detail));
      setFormLoadedForId(nextId);
    }
    if (isNew && formLoadedForId !== "new") {
      setForm(DEFAULT_FORM);
      setFormLoadedForId("new");
    }
  }, [detail, formLoadedForId, isNew]);

  function setField(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  function goBack() {
    navigate(backTo);
  }

  async function submit(event, force = false) {
    event.preventDefault();
    setError("");
    setNeedsForceSave(false);
    try {
      const payload = buildPayload(form, detail, force);
      const saved = await saveMutation.mutateAsync(payload);
      if (isNew && saved?.id) {
        navigate(`/admin/exercise-texts/${saved.id}`, { replace: true, state: { backTo } });
      }
    } catch (err) {
      const message = err?.message || t.saveError || "Save failed";
      setError(message);
      setNeedsForceSave(message.includes("Selected grammar topic"));
    }
  }

  async function generate(stage) {
    if (!exerciseTextId) return;
    setError("");
    if (isFormDirty(form, detail)) {
      setError(t.saveBeforeGenerate || "Save changes before generation.");
      return;
    }
    try {
      const response = await generationMutation.mutateAsync({ stage, voiceCode: form.voiceCode || undefined });
      const nextTaskIds = response.tasks ? response.tasks.map((task) => task.id) : [response.task?.id];
      setTaskIds((current) => [...new Set([...current, ...nextTaskIds.filter(Boolean)])]);
    } catch (err) {
      setError(err?.message || t.actionError || "Action failed");
    }
  }

  async function confirmParagraphStage(paragraphId, stage) {
    if (!detail?.version) return;
    setError("");
    try {
      await confirmParagraphStageMutation.mutateAsync({ paragraphId, stage, version: detail.version });
    } catch (err) {
      setError(err?.message || t.actionError || "Action failed");
    }
  }

  return (
    <CrudEditPage
      title={title}
      breadcrumbs={[
        { title: "CronoLex", path: "/admin" },
        { title: t.exerciseTexts || "Texts for exercises", path: "/admin/exercise-texts" },
        { title },
      ]}
      actions={(
        <Button type="button" variant="outlined" startIcon={<ArrowLeft size={16} />} onClick={goBack}>
          {t.close || "Close"}
        </Button>
      )}
    >
      <CrudFormSurface sx={{ width: "100%", gap: 2.5 }}>
        {(loadError || error || mutationError) && (
          <Alert severity="error">{error || mutationError?.message || loadError?.message || t.loadError}</Alert>
        )}
        {needsForceSave && (
          <Alert
            severity="warning"
            action={(
              <Button color="inherit" size="small" disabled={saveMutation.isPending} onClick={(event) => submit(event, true)}>
                {t.forceSave || "Force Save"}
              </Button>
            )}
          >
            {t.topicDifficultyWarning || "Selected topic is above this difficulty. Confirm to save anyway."}
          </Alert>
        )}
        <Box
          component="form"
          id="exercise-text-form"
          onSubmit={submit}
          sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "minmax(0, 1fr) minmax(280px, 360px)" } }}
        >
          <Stack spacing={2}>
            <TextField label={t.title || "Title"} value={form.title} onChange={(event) => setField("title", event.target.value)} fullWidth />
            <TextField
              label={t.source || "Source"}
              value={form.sourceText}
              onChange={(event) => setField("sourceText", event.target.value)}
              multiline
              minRows={8}
              fullWidth
            />
          </Stack>
          <Stack spacing={2}>
            <TextField
              select
              label={t.difficultyBand || "Difficulty"}
              value={form.difficultyBand}
              onChange={(event) => setField("difficultyBand", event.target.value)}
              fullWidth
            >
              <MenuItem value="">{t.empty || "Empty"}</MenuItem>
              {toOptions(reference.difficulty_bands).map((option) => (
                <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
              ))}
            </TextField>
            <MultiSelect
              label={t.textType || "Text type"}
              options={toOptions(reference.text_types)}
              value={form.textTypes}
              onChange={(textTypes) => setField("textTypes", textTypes)}
            />
            <MultiSelect
              label={t.grammarTopics || "Grammar topics"}
              options={grammarTopics.map((topic) => ({ value: String(topic.id), label: topic.title || topic.code || String(topic.id) }))}
              value={form.topicIds}
              onChange={(topicIds) => setField("topicIds", topicIds)}
            />
            <TextField
              select
              label={t.voice || "Voice"}
              value={form.voiceCode}
              onChange={(event) => setField("voiceCode", event.target.value)}
              fullWidth
              sx={filterControlSx}
            >
              <MenuItem value="">{t.auto || "Auto"}</MenuItem>
              {ttsVoices.map((voice) => (
                <MenuItem key={voice.code} value={voice.code}>{voice.display_name || voice.code}</MenuItem>
              ))}
            </TextField>
          </Stack>
        </Box>
        {loading && <LoadingLine text={t.loading || "Loading..."} />}
        <Stack direction="row" spacing={1.5} sx={{ justifyContent: "flex-end" }}>
          <Button type="button" variant="outlined" onClick={goBack}>{t.close || "Close"}</Button>
          <Button type="submit" form="exercise-text-form" variant="contained" startIcon={<Save size={16} />} disabled={saveMutation.isPending || loading}>
            {saveMutation.isPending ? t.saving || "Saving..." : t.save || "Save"}
          </Button>
        </Stack>
      </CrudFormSurface>

      {!isNew && (
        <Stack spacing={2.5}>
          <GenerationPanel
            disabled={generationMutation.isPending || loading}
            generationState={content.generation_state || {}}
            onGenerate={generate}
            taskRows={taskRows}
            t={t}
          />
          <PreviewPanel
            confirmDisabled={confirmParagraphStageMutation.isPending || loading}
            generated={generated}
            highlightedEvidence={highlightedEvidence}
            onConfirmParagraphStage={confirmParagraphStage}
            onEvidenceHighlight={setHighlightedEvidence}
            translationTab={translationTab}
            onTranslationTabChange={setTranslationTab}
            t={t}
          />
          <JsonPreview title="content_jsonb" value={content} />
        </Stack>
      )}
    </CrudEditPage>
  );
}

function GenerationPanel({ disabled, generationState, onGenerate, taskRows, t }) {
  return (
    <DetailPanel title={t.generationState || "Generation"}>
      <Stack spacing={1.5}>
        <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
          {["content", "translations", "quiz", "tts", "all"].map((stage) => (
            <Button
              key={stage}
              variant={stage === "all" ? "contained" : "outlined"}
              startIcon={stage === "all" ? <WandSparkles size={16} /> : <Bot size={16} />}
              disabled={disabled}
              onClick={() => onGenerate(stage)}
            >
              {STAGE_LABELS[stage]}
            </Button>
          ))}
        </Stack>
        <ChipRow values={generationState} />
        {taskRows.length > 0 && (
          <Stack spacing={0.75}>
            {taskRows.map((task) => (
              <Stack key={task.id} direction="row" spacing={1} sx={{ alignItems: "center" }}>
                {task.status === "processing" && <CircularProgress size={14} />}
                <Typography variant="body2">Task #{task.id}</Typography>
                <Chip size="small" label={task.status} color={task.status === "success" ? "success" : task.status === "error" ? "error" : "info"} />
              </Stack>
            ))}
          </Stack>
        )}
      </Stack>
    </DetailPanel>
  );
}

function PreviewPanel({
  confirmDisabled,
  generated,
  highlightedEvidence,
  onConfirmParagraphStage,
  onEvidenceHighlight,
  translationTab,
  onTranslationTabChange,
  t,
}) {
  const paragraphs = Array.isArray(generated.paragraphs) ? generated.paragraphs : [];
  const questions = Array.isArray(generated.questions) ? generated.questions : [];
  const paragraphTextById = Object.fromEntries(
    paragraphs.map((paragraph) => [paragraph.id, localizedSource(paragraph.text)]).filter(([, text]) => Boolean(text)),
  );
  return (
    <DetailPanel title={t.preview || "Preview"}>
      <Stack spacing={2}>
        <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
          <Chip icon={<FileText size={14} />} label={generated.title || "-"} variant="outlined" />
          {(generated.text_types || []).map((item) => <Chip key={item} label={item} size="small" />)}
        </Stack>
        <Tabs value={translationTab} onChange={(_event, value) => onTranslationTabChange(value)} variant="scrollable">
          {TRANSLATION_TABS.map((lang) => <Tab key={lang} value={lang} label={lang.toUpperCase()} />)}
        </Tabs>
        <Stack spacing={1.5} divider={<Divider flexItem />}>
          {paragraphs.length === 0 && <Typography color="text.secondary">{t.emptyExerciseTexts || "No generated paragraphs yet."}</Typography>}
          {paragraphs.map((paragraph, index) => (
            <Box key={paragraph.id || index}>
              <Typography variant="subtitle2">{paragraph.id || `#${index + 1}`}</Typography>
              <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                <HighlightedText paragraph={paragraph} text={localizedSource(paragraph.text)} highlightedEvidence={highlightedEvidence} />
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75, whiteSpace: "pre-wrap" }}>
                {localizedTranslation(paragraph.text, translationTab) || "-"}
              </Typography>
              <ChipRow values={paragraph.status || {}} sx={{ mt: 1 }} />
              <ConfirmStageButtons
                disabled={confirmDisabled}
                onConfirm={(stage) => onConfirmParagraphStage(paragraph.id, stage)}
                status={paragraph.status || {}}
                t={t}
              />
            </Box>
          ))}
        </Stack>
        <Stack spacing={1.25}>
          <Typography variant="subtitle2">{t.hasQuiz || "Quiz"}</Typography>
          {questions.length === 0 && <Typography color="text.secondary">-</Typography>}
          {questions.map((question) => (
            <Box key={question.id} sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1.25 }}>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>{localizedSource(question.question) || question.id}</Typography>
              <Stack spacing={0.75} sx={{ mt: 1 }}>
                {(question.options || []).map((option) => (
                  <Stack
                    key={option.id}
                    direction="row"
                    spacing={1}
                    tabIndex={0}
                    onBlur={() => onEvidenceHighlight(null)}
                    onFocus={() => onEvidenceHighlight(option.evidence_span || null)}
                    onMouseEnter={() => onEvidenceHighlight(option.evidence_span || null)}
                    onMouseLeave={() => onEvidenceHighlight(null)}
                    sx={{ alignItems: "center" }}
                  >
                    <Chip size="small" label={option.is_correct ? "correct" : "option"} color={option.is_correct ? "success" : "default"} />
                    <Typography variant="body2">{localizedSource(option.text) || option.id}</Typography>
                    <EvidenceChip option={option} paragraphTextById={paragraphTextById} />
                  </Stack>
                ))}
              </Stack>
            </Box>
          ))}
        </Stack>
      </Stack>
    </DetailPanel>
  );
}

function HighlightedText({ paragraph, text, highlightedEvidence }) {
  if (!text) return "-";
  if (!highlightedEvidence || highlightedEvidence.paragraph_id !== paragraph.id) return text;
  const start = highlightedEvidence.start_char;
  const end = highlightedEvidence.end_char;
  if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end <= start || end > text.length) return text;
  return (
    <>
      {text.slice(0, start)}
      <Box component="mark" sx={{ bgcolor: "warning.light", color: "warning.contrastText", px: 0.25 }}>
        {text.slice(start, end)}
      </Box>
      {text.slice(end)}
    </>
  );
}

function ConfirmStageButtons({ disabled, onConfirm, status, t }) {
  const entries = Object.entries(status || {}).filter(([stage, state]) => (
    ["content", "translations", "quiz"].includes(stage) && ["stale", "failed"].includes(state)
  ));
  if (entries.length === 0) return null;
  return (
    <Stack direction="row" spacing={0.75} useFlexGap sx={{ flexWrap: "wrap", mt: 1 }}>
      {entries.map(([stage]) => (
        <Button key={stage} size="small" variant="outlined" disabled={disabled} onClick={() => onConfirm(stage)}>
          {(t.confirmStage || "Confirm")} {stage}
        </Button>
      ))}
    </Stack>
  );
}

function EvidenceChip({ option, paragraphTextById }) {
  const span = option.evidence_span;
  const quote = option.evidence_quote;
  const paragraphText = span?.paragraph_id ? paragraphTextById[span.paragraph_id] : "";
  const isValid = (
    typeof quote === "string"
    && paragraphText
    && Number.isInteger(span?.start_char)
    && Number.isInteger(span?.end_char)
    && paragraphText.slice(span.start_char, span.end_char) === quote
  );
  return <Chip size="small" label={isValid ? "evidence ok" : "evidence mismatch"} color={isValid ? "success" : "error"} variant="outlined" />;
}

function ChipRow({ values, sx }) {
  const entries = Object.entries(values || {}).filter(([, state]) => Boolean(state));
  if (entries.length === 0) return <Typography color="text.secondary">-</Typography>;
  return (
    <Stack direction="row" spacing={0.75} useFlexGap sx={{ flexWrap: "wrap", ...sx }}>
      {entries.map(([stage, state]) => <Chip key={stage} size="small" label={`${stage}: ${state}`} variant="outlined" />)}
    </Stack>
  );
}

function buildForm(item) {
  const content = item?.content_jsonb || {};
  const source = content.source || {};
  return {
    difficultyBand: item?.difficulty_band || source.generation_constraints?.difficulty_band || "",
    sourceText: source.english_text || source.text || "",
    textTypes: item?.text_types || source.generation_constraints?.text_types || [],
    title: item?.title || content.generated?.title || "",
    topicIds: (item?.topic_ids || source.generation_constraints?.topic_ids || []).map(String),
    voiceCode: content.generated?.audio?.voice_code || "",
  };
}

function buildPayload(form, item, force) {
  const topicIds = form.topicIds.map(Number).filter((value) => Number.isInteger(value) && value > 0);
  const content = {
    ...(item?.content_jsonb || {}),
    schema_version: 1,
    source: {
      ...((item?.content_jsonb || {}).source || {}),
      english_text: form.sourceText.trim(),
      generation_constraints: buildGenerationConstraints(form, topicIds),
    },
  };
  const payload = {
    title: form.title.trim() || null,
    difficulty_band: form.difficultyBand || null,
    text_types: form.textTypes,
    topic_ids: topicIds,
    content_jsonb: content,
  };
  if (item?.version) payload.version = item.version;
  if (force) payload.force_topic_difficulty = { reason: "Confirmed in admin UI" };
  return payload;
}

function isFormDirty(form, item) {
  if (!item) return false;
  const payload = buildPayload(form, item, false);
  const source = item.content_jsonb?.source || {};
  return (
    payload.title !== (item.title || null)
    || payload.difficulty_band !== (item.difficulty_band || null)
    || JSON.stringify(payload.text_types) !== JSON.stringify(item.text_types || [])
    || JSON.stringify(payload.topic_ids) !== JSON.stringify(item.topic_ids || [])
    || payload.content_jsonb.source.english_text !== (source.english_text || source.text || "")
    || JSON.stringify(payload.content_jsonb.source.generation_constraints || {}) !== JSON.stringify(source.generation_constraints || {})
  );
}

function buildGenerationConstraints(form, topicIds) {
  const constraints = {};
  if (form.difficultyBand) constraints.difficulty_band = form.difficultyBand;
  if (form.textTypes.length > 0) constraints.text_types = form.textTypes;
  if (topicIds.length > 0) constraints.topic_ids = topicIds;
  return constraints;
}

function localizedSource(value) {
  return value?.source?.content || "";
}

function localizedTranslation(value, lang) {
  const translations = Array.isArray(value?.translations) ? value.translations : [];
  const found = translations.find((item) => item.lang === lang);
  return found?.content || "";
}

function toOptions(values) {
  return (values || []).map((value) => ({ value: String(value), label: String(value) }));
}
