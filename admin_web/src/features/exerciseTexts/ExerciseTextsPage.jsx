import { useMemo } from "react";
import { Alert, Box, Button, Chip, IconButton, MenuItem, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "@mui/material";
import { FileText, Pencil, Plus } from "lucide-react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { ArchiveTabs, CrudPage, CrudTableSurface, EmptyState, FilterBar, LoadingLine, LogToolbar, MultiSelect, Pager } from "../../shared/components";
import { dataTableContainerSx } from "../../shared/components/dataTableStyles";
import { filterControlSx } from "../../shared/components/filterControls";
import { applyExerciseTextsParamUpdates, exerciseTextsParamsFromSearch } from "./helpers/listParams";
import { useExerciseTextsList } from "./hooks/useExerciseTextsList";

const STATUS_COLOR = {
  archived: "default",
  draft: "default",
  generated: "info",
  published: "success",
  ready: "warning",
};

export function ExerciseTextsPage({ t }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const params = useMemo(() => exerciseTextsParamsFromSearch(searchParams), [searchParams]);
  const { grammarTopicsQuery, listQuery, referenceQuery } = useExerciseTextsList(params);
  const reference = referenceQuery.data || {};
  const grammarTopics = grammarTopicsQuery.data?.items || [];
  const items = listQuery.data?.items || [];
  const loading = listQuery.isFetching || referenceQuery.isFetching || grammarTopicsQuery.isFetching;
  const error = listQuery.error || referenceQuery.error || grammarTopicsQuery.error;

  function updateParams(updates) {
    setSearchParams((current) => applyExerciseTextsParamUpdates(current, updates));
  }

  function openEditor(exerciseTextId) {
    const target = exerciseTextId ? `/admin/exercise-texts/${exerciseTextId}` : "/admin/exercise-texts/new";
    navigate(target, { state: { backTo: `${location.pathname}${location.search}${location.hash}` } });
  }

  return (
    <CrudPage
      title={t.exerciseTexts || "Texts for exercises"}
      breadcrumbs={[{ title: "CronoLex", path: "/admin" }, { title: t.exerciseTexts || "Texts for exercises" }]}
      actions={(
        <Button variant="contained" startIcon={<Plus size={16} />} onClick={() => openEditor(null)}>
          {t.create || "Create"}
        </Button>
      )}
    >
      <FilterBar>
        <LogToolbar
          t={t}
          search={params.search}
          onSearch={(value) => updateParams({ search: value, page: 1 })}
        />
        <MultiSelect
          label={t.difficultyBand || "Difficulty"}
          options={toOptions(reference.difficulty_bands)}
          value={params.difficultyBands}
          onChange={(difficultyBands) => updateParams({ difficultyBands, page: 1 })}
        />
        <MultiSelect
          label={t.status}
          options={toOptions(reference.statuses)}
          value={params.statuses}
          onChange={(statuses) => updateParams({ statuses, page: 1 })}
        />
        <MultiSelect
          label={t.textType || "Text type"}
          options={toOptions(reference.text_types)}
          value={params.textTypes}
          onChange={(textTypes) => updateParams({ textTypes, page: 1 })}
        />
        <MultiSelect
          label={t.grammarTopics || "Grammar topics"}
          options={grammarTopics.map((topic) => ({ value: String(topic.id), label: topic.title || topic.code || String(topic.id) }))}
          value={params.topicIds}
          onChange={(topicIds) => updateParams({ topicIds, page: 1 })}
        />
        <TextField
          select
          size="small"
          label={t.sort || "Sort"}
          value={params.sort}
          onChange={(event) => updateParams({ sort: event.target.value, page: 1 })}
          sx={filterControlSx}
        >
          <MenuItem value="updated_desc">{t.updated || "Updated"}</MenuItem>
          <MenuItem value="created_desc">{t.date || "Created"}</MenuItem>
          <MenuItem value="title_asc">{t.title || "Title"}</MenuItem>
          <MenuItem value="id_desc">ID</MenuItem>
        </TextField>
        <TextField
          select
          size="small"
          label={t.hasQuiz || "Quiz"}
          value={params.hasQuiz}
          onChange={(event) => updateParams({ hasQuiz: event.target.value, page: 1 })}
          sx={filterControlSx}
        >
          <MenuItem value="all">{t.all}</MenuItem>
          <MenuItem value="yes">{t.yes || "Yes"}</MenuItem>
          <MenuItem value="no">{t.no || "No"}</MenuItem>
        </TextField>
        <TextField
          select
          size="small"
          label={t.hasTts || "TTS"}
          value={params.hasTts}
          onChange={(event) => updateParams({ hasTts: event.target.value, page: 1 })}
          sx={filterControlSx}
        >
          <MenuItem value="all">{t.all}</MenuItem>
          <MenuItem value="yes">{t.yes || "Yes"}</MenuItem>
          <MenuItem value="no">{t.no || "No"}</MenuItem>
        </TextField>
      </FilterBar>

      <ArchiveTabs
        labels={{ all: t.all, archived: t.archived }}
        value={params.archived ? "archived" : "all"}
        onChange={(value) => updateParams({ archived: value === "archived", page: 1 })}
      />
      {error && <Alert severity="error">{error.message || t.loadError}</Alert>}

      <CrudTableSurface sx={dataTableContainerSx}>
        <Table size="small" sx={{ minWidth: 1320 }}>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>{t.title || "Title"}</TableCell>
              <TableCell>{t.difficultyBand || "Difficulty"}</TableCell>
              <TableCell>{t.grammarTopics || "Topics"}</TableCell>
              <TableCell>{t.textType || "Text types"}</TableCell>
              <TableCell>{t.status}</TableCell>
              <TableCell>{t.generationState || "Generation"}</TableCell>
              <TableCell>{t.translations}</TableCell>
              <TableCell>{t.hasQuiz || "Quiz"}</TableCell>
              <TableCell>{t.hasTts || "TTS"}</TableCell>
              <TableCell>{t.date}</TableCell>
              <TableCell>{t.updated}</TableCell>
              <TableCell align="right">{t.actions || "Actions"}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((item) => {
              const content = item.content_jsonb || {};
              const generated = content.generated || {};
              return (
                <TableRow hover key={item.id}>
                  <TableCell sx={{ verticalAlign: "top" }}>{item.id}</TableCell>
                  <TableCell sx={{ verticalAlign: "top", minWidth: 220 }}>
                    <Stack spacing={0.25}>
                      <Typography variant="subtitle2">{item.title || generated.title || "-"}</Typography>
                      <Typography variant="caption" color="text.secondary">{item.uuid}</Typography>
                    </Stack>
                  </TableCell>
                  <TableCell sx={{ verticalAlign: "top" }}>{item.difficulty_band || generated.difficulty?.band || "-"}</TableCell>
                  <TableCell sx={{ verticalAlign: "top", minWidth: 220 }}>
                    <ChipList values={topicLabels(item.topic_ids, grammarTopics)} />
                  </TableCell>
                  <TableCell sx={{ verticalAlign: "top", minWidth: 160 }}>
                    <ChipList values={item.text_types || generated.text_types || []} />
                  </TableCell>
                  <TableCell sx={{ verticalAlign: "top" }}>
                    <Chip label={item.status || "-"} size="small" color={STATUS_COLOR[item.status] || "default"} variant={item.status === "draft" ? "outlined" : "filled"} />
                  </TableCell>
                  <TableCell sx={{ verticalAlign: "top", minWidth: 180 }}>
                    <GenerationState value={content.generation_state || {}} />
                  </TableCell>
                  <TableCell sx={{ verticalAlign: "top" }}>{hasTranslations(generated) ? t.yes || "Yes" : t.no || "No"}</TableCell>
                  <TableCell sx={{ verticalAlign: "top" }}>{hasQuiz(generated) ? t.yes || "Yes" : t.no || "No"}</TableCell>
                  <TableCell sx={{ verticalAlign: "top" }}>{hasTts(generated) ? t.yes || "Yes" : t.no || "No"}</TableCell>
                  <TableCell sx={{ verticalAlign: "top", minWidth: 150 }}>{item.created || "-"}</TableCell>
                  <TableCell sx={{ verticalAlign: "top", minWidth: 150 }}>{item.updated || "-"}</TableCell>
                  <TableCell align="right" sx={{ verticalAlign: "top" }}>
                    <IconButton size="small" title={t.edit || "Edit"} aria-label={t.edit || "Edit"} onClick={() => openEditor(item.id)} sx={exerciseTextActionIconSx}>
                      <Pencil size={18} />
                    </IconButton>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        {!error && items.length === 0 && !loading && (
          <Box sx={{ p: 3 }}>
            <EmptyState text={t.emptyExerciseTexts || "No exercise texts yet."} />
          </Box>
        )}
        {loading && <LoadingLine text={t.loading} />}
      </CrudTableSurface>
      <Pager
        page={params.page}
        pageSize={params.pageSize}
        total={listQuery.data?.total || 0}
        onPageChange={(page) => updateParams({ page })}
        onPageSizeChange={(pageSize) => updateParams({ pageSize, page: 1 })}
      />
    </CrudPage>
  );
}

const exerciseTextActionIconSx = {
  border: 1,
  borderColor: "divider",
  borderRadius: 1,
  height: 34,
  width: 34,
};

function ChipList({ values }) {
  const normalized = values.filter(Boolean);
  if (normalized.length === 0) return <Typography color="text.secondary">-</Typography>;
  return (
    <Stack direction="row" spacing={0.75} useFlexGap sx={{ flexWrap: "wrap" }}>
      {normalized.map((value) => <Chip key={value} label={value} size="small" variant="outlined" />)}
    </Stack>
  );
}

function GenerationState({ value }) {
  const entries = Object.entries(value).filter(([, state]) => Boolean(state));
  if (entries.length === 0) return <Typography color="text.secondary">-</Typography>;
  return (
    <Stack spacing={0.5}>
      {entries.map(([stage, state]) => (
        <Stack key={stage} direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
          <FileText size={14} />
          <Typography variant="caption" component="span">{stage}: {state}</Typography>
        </Stack>
      ))}
    </Stack>
  );
}

function hasTranslations(generated) {
  const paragraphs = Array.isArray(generated.paragraphs) ? generated.paragraphs : [];
  return paragraphs.some((paragraph) => paragraph.translations && Object.keys(paragraph.translations).length > 0);
}

function hasQuiz(generated) {
  return Array.isArray(generated.questions) && generated.questions.length > 0;
}

function hasTts(generated) {
  const audio = generated.audio || {};
  return Array.isArray(audio.files) && audio.files.length > 0;
}

function toOptions(values) {
  return (values || []).map((value) => ({ value: String(value), label: String(value) }));
}

function topicLabels(topicIds, grammarTopics) {
  const topicsById = new Map(grammarTopics.map((topic) => [String(topic.id), topic]));
  return (topicIds || []).map((topicId) => {
    const topic = topicsById.get(String(topicId));
    return topic?.title || topic?.code || `#${topicId}`;
  });
}
