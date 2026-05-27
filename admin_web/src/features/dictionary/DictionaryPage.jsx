import React, { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, Archive, CheckCircle2, Pencil, Save, Trash2, Volume2 } from "lucide-react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  IconButton,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { ArchiveTabs, CrudEditPage, CrudFormSurface, CrudPage, CrudTableSurface, FilterBar, LogToolbar, MultiSelect, Pager } from "../../shared/components";
import { canAdminAccess } from "../../shared/acl/adminAcl";
import { dataTableContainerSx } from "../../shared/components/dataTableStyles";
import { filterControlSx } from "../../shared/components/filterControls";
import {
  archiveDictionaryEntry,
  deleteDictionaryEntry,
  dictionaryQueryKeys,
  fetchDictionaryEntries,
  fetchDictionaryEntry,
  fetchDictionaryFilterMetadata,
  updateDictionaryEntry,
  verifyDictionaryEntries,
} from "./api/dictionaryApi";
import {
  buildDictionaryEntryForm,
  buildDictionaryEntryPayload,
  buildSavedDictionaryListEntry,
  DICTIONARY_ENTRY_TYPE_OPTIONS,
  hasDictionaryField,
  normalizeDictionaryEntryResponse,
} from "./dictionaryEntry";
import { applyDictionaryListParamUpdates, dictionaryListParamsFromSearch } from "./helpers/listParams";

export function DictionaryPage({ t, user }) {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const canDelete = canAdminAccess(user, "dictionary/delete_word");
  const canArchive = canAdminAccess(user, "dictionary/archive_word");
  const canUpdate = canAdminAccess(user, "dictionary/update_word");
  const canVerify = canAdminAccess(user, "dictionary/verify_word");
  const [selectedIds, setSelectedIds] = useState([]);

  const listParams = useMemo(() => dictionaryListParamsFromSearch(searchParams), [searchParams]);
  const filtersQuery = useQuery({
    queryKey: dictionaryQueryKeys.filterMetadata(),
    queryFn: fetchDictionaryFilterMetadata,
  });
  const entriesQuery = useQuery({
    queryKey: dictionaryQueryKeys.list(listParams),
    queryFn: () => fetchDictionaryEntries(listParams),
  });

  const invalidateDictionary = () => {
    queryClient.invalidateQueries({ queryKey: dictionaryQueryKeys.lists() });
    queryClient.invalidateQueries({ queryKey: dictionaryQueryKeys.details() });
  };
  const archiveMutation = useMutation({
    mutationFn: archiveDictionaryEntry,
    onSuccess: invalidateDictionary,
  });
  const deleteMutation = useMutation({
    mutationFn: deleteDictionaryEntry,
    onSuccess: invalidateDictionary,
  });
  const verifyMutation = useMutation({
    mutationFn: verifyDictionaryEntries,
    onSuccess: () => {
      setSelectedIds([]);
      invalidateDictionary();
    },
  });

  const items = useMemo(() => entriesQuery.data?.items || [], [entriesQuery.data?.items]);
  const filters = filtersQuery.data || null;
  const loading = entriesQuery.isFetching;
  const actionPending = archiveMutation.isPending || deleteMutation.isPending || verifyMutation.isPending;
  const actionError = archiveMutation.error || deleteMutation.error || verifyMutation.error;
  const selectableItems = useMemo(
    () => items.filter((item) => !item.is_teacher_verified && !item.is_archived),
    [items],
  );
  const selectedIdSet = useMemo(() => new Set(selectedIds), [selectedIds]);
  const allSelected = selectableItems.length > 0 && selectableItems.every((item) => selectedIdSet.has(item.id));

  useEffect(() => {
    setSelectedIds((current) => {
      const next = current.filter((id) => selectableItems.some((item) => item.id === id));
      return next.length === current.length ? current : next;
    });
  }, [selectableItems]);

  function updateListParams(updates) {
    setSearchParams((current) => applyDictionaryListParamUpdates(current, updates));
  }

  function archiveEntry(id) {
    archiveMutation.mutate(id);
  }

  function deleteEntry(id) {
    deleteMutation.mutate(id);
  }

  function toggleSelected(id, checked) {
    setSelectedIds((current) => {
      if (checked) return current.includes(id) ? current : [...current, id];
      return current.filter((entryId) => entryId !== id);
    });
  }

  function toggleAllSelected(checked) {
    setSelectedIds(checked ? selectableItems.map((item) => item.id) : []);
  }

  function verifySelected() {
    if (selectedIds.length === 0) return;
    verifyMutation.mutate({ entryIds: selectedIds });
  }

  function editEntry(id) {
    navigate(`/admin/dictionary/${id}/edit`, {
      state: { backTo: `${location.pathname}${location.search}${location.hash}` },
    });
  }

  return (
    <CrudPage
      title={t.dictionary}
      breadcrumbs={[{ title: "CronoLex", path: "/admin" }, { title: t.dictionary }]}
    >
      <FilterBar>
        <LogToolbar
          t={t}
          search={listParams.search}
          onSearch={(value) => {
            updateListParams({ search: value, page: 1 });
          }}
        />
        <MultiSelect label={t.entryType} options={filters?.filters?.find((item) => item.name === "entry_type")?.options || []} value={listParams.entryTypes} onChange={(entryTypes) => updateListParams({ entryTypes, page: 1 })} />
        <MultiSelect label={t.pos} options={filters?.filters?.find((item) => item.name === "part_of_speech")?.options || []} value={listParams.partsOfSpeech} onChange={(partsOfSpeech) => updateListParams({ partsOfSpeech, page: 1 })} />
        <TextField
          select
          size="small"
          label={t.verification}
          value={listParams.verified}
          onChange={(event) => updateListParams({ verified: event.target.value, page: 1 })}
          sx={filterControlSx}
        >
          <MenuItem value="all">{t.all}</MenuItem>
          <MenuItem value="verified">{t.verified}</MenuItem>
          <MenuItem value="unverified">{t.unverified}</MenuItem>
        </TextField>
        {canVerify && (
          <Button
            variant="outlined"
            startIcon={<CheckCircle2 size={16} />}
            disabled={selectedIds.length === 0 || actionPending}
            onClick={verifySelected}
            sx={{ minHeight: 56, alignSelf: "stretch", px: 2.25 }}
          >
            {t.markVerified} {selectedIds.length ? `(${selectedIds.length})` : ""}
          </Button>
        )}
      </FilterBar>

      <ArchiveTabs
        labels={{ all: t.all, archived: t.archived }}
        value={listParams.archived ? "archived" : "all"}
        onChange={(value) => {
          updateListParams({ archived: value === "archived", page: 1 });
        }}
      />
      {entriesQuery.error && <Alert severity="error">{entriesQuery.error.message || t.loadError}</Alert>}
      {actionError && <Alert severity="error">{actionError.message || t.loadError}</Alert>}

      <CrudTableSurface sx={dataTableContainerSx}>
        <Table size="small" sx={{ minWidth: 1280 }}>
          <TableHead>
            <TableRow>
              {canVerify && (
                <TableCell padding="checkbox">
                  <Checkbox
                    size="small"
                    checked={allSelected}
                    indeterminate={selectedIds.length > 0 && !allSelected}
                    disabled={selectableItems.length === 0 || actionPending}
                    onChange={(event) => toggleAllSelected(event.target.checked)}
                  />
                </TableCell>
              )}
              <TableCell>{t.word}</TableCell>
              <TableCell>{t.level}</TableCell>
              <TableCell>{t.pos}</TableCell>
              <TableCell>{t.translations}</TableCell>
              <TableCell>{t.examples}</TableCell>
              <TableCell>{t.categories}</TableCell>
              <TableCell>{t.audio}</TableCell>
              <TableCell align="right">{t.actions}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((item) => (
              <TableRow hover key={item.id}>
                {canVerify && (
                  <TableCell padding="checkbox" sx={{ verticalAlign: "top" }}>
                    <Checkbox
                      size="small"
                      checked={selectedIdSet.has(item.id)}
                      disabled={item.is_teacher_verified || item.is_archived || actionPending}
                      onChange={(event) => toggleSelected(item.id, event.target.checked)}
                    />
                  </TableCell>
                )}
                <TableCell sx={{ verticalAlign: "top", minWidth: 160 }}>
                  <Stack spacing={0.25} alignItems="flex-start">
                    <Stack direction="row" spacing={0.75} alignItems="center">
                      <Typography variant="subtitle2" component="strong" sx={{ display: "block" }}>{item.word}</Typography>
                      {item.is_teacher_verified && (
                        <Box component="span" sx={{ color: "success.main", display: "inline-flex" }} title={t.verified}>
                          <CheckCircle2 size={16} />
                        </Box>
                      )}
                    </Stack>
                    <Typography variant="caption" component="span" color="text.secondary" sx={{ display: "block" }}>
                      {item.transcription || item.phonetic_us}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell sx={{ verticalAlign: "top", minWidth: 84 }}>
                  {item.level_title || (item.level_id ? `#${item.level_id}` : "-")}
                </TableCell>
                <TableCell sx={{ verticalAlign: "top", color: "text.secondary" }}>{(item.parts_of_speech || []).join(", ")}</TableCell>
                <TableCell sx={{ verticalAlign: "top", whiteSpace: "pre-line", minWidth: 180 }}>{item.translations_multiline}</TableCell>
                <TableCell sx={{ verticalAlign: "top", minWidth: 220 }}>
                  <Stack spacing={0.75}>
                    {(item.examples_json || []).map((example, index) => (
                      <Typography variant="body2" color="text.secondary" key={index}>{example}</Typography>
                    ))}
                  </Stack>
                </TableCell>
                <TableCell sx={{ verticalAlign: "top", minWidth: 160 }}>
                  <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
                    {(item.categories || []).map((cat) => (
                      <Chip key={cat} label={cat} size="small" variant="outlined" />
                    ))}
                  </Stack>
                </TableCell>
                <TableCell sx={{ verticalAlign: "top", minWidth: 180 }}>
                  {item.audio_url ? (
                    <Box component="audio" controls preload="none" src={item.audio_url} sx={{ width: 180, maxWidth: "100%" }} />
                  ) : (
                    <Stack direction="row" spacing={0.75} alignItems="center" color="text.secondary">
                      <Volume2 size={16} />
                      <Typography variant="body2">{t.missingAudio}</Typography>
                    </Stack>
                  )}
                </TableCell>
                <TableCell align="right" sx={{ verticalAlign: "top", minWidth: 120 }}>
                  <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                    {canUpdate && (
                      <IconButton
                        size="small"
                        title={t.edit}
                        aria-label={t.edit}
                        onClick={() => editEntry(item.id)}
                        sx={dictionaryActionIconSx}
                      >
                        <Pencil size={18} />
                      </IconButton>
                    )}
                    {canArchive && !listParams.archived && (
                      <IconButton
                        size="small"
                        title={t.archive}
                        aria-label={t.archive}
                        disabled={actionPending}
                        onClick={() => archiveEntry(item.id)}
                        sx={dictionaryActionIconSx}
                      >
                        <Archive size={18} />
                      </IconButton>
                    )}
                    {canDelete && (
                      <IconButton
                        size="small"
                        color="error"
                        title={t.delete}
                        aria-label={t.delete}
                        disabled={actionPending}
                        onClick={() => deleteEntry(item.id)}
                        sx={dictionaryActionIconSx}
                      >
                        <Trash2 size={18} />
                      </IconButton>
                    )}
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {loading && (
          <Stack
            alignItems="center"
            justifyContent="center"
            spacing={1}
            sx={{
              position: "absolute",
              inset: 0,
              minHeight: 160,
              bgcolor: "rgba(15, 17, 22, 0.68)",
              backdropFilter: "blur(1px)",
            }}
          >
            <CircularProgress size={28} />
            <Typography variant="body2">{t.loading}</Typography>
          </Stack>
        )}
      </CrudTableSurface>
      <Pager page={listParams.page} pageSize={listParams.pageSize} total={entriesQuery.data?.total || 0} onPageChange={(page) => updateListParams({ page })} onPageSizeChange={(pageSize) => updateListParams({ pageSize, page: 1 })} />
    </CrudPage>
  );
}

const dictionaryActionIconSx = {
  border: 1,
  borderColor: "divider",
  borderRadius: 1,
  width: 34,
  height: 34,
};

export function DictionaryEntryEditPage({ t, entryId, onBack }) {
  const queryClient = useQueryClient();
  const [detail, setDetail] = useState(null);
  const [form, setForm] = useState(() => buildDictionaryEntryForm(null));
  const [error, setError] = useState("");
  const entryQuery = useQuery({
    queryKey: dictionaryQueryKeys.detail(entryId),
    queryFn: () => fetchDictionaryEntry(entryId),
  });
  const saveMutation = useMutation({
    mutationFn: updateDictionaryEntry,
  });

  useEffect(() => {
    const loaded = normalizeDictionaryEntryResponse(entryQuery.data);
    if (!loaded) return;
    setDetail(loaded);
    setForm(buildDictionaryEntryForm(loaded));
  }, [entryQuery.data]);

  function setField(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      const payload = buildDictionaryEntryPayload(form, detail);
      const response = await saveMutation.mutateAsync({ entryId, payload });
      const saved = normalizeDictionaryEntryResponse(response) || {};
      queryClient.setQueryData(dictionaryQueryKeys.detail(entryId), saved);
      queryClient.invalidateQueries({ queryKey: dictionaryQueryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: dictionaryQueryKeys.detail(entryId) });
      onBack(buildSavedDictionaryListEntry(detail, detail, form, saved));
    } catch (err) {
      setError(err.message || t.saveError);
    }
  }

  const hasTranscription = hasDictionaryField(detail, null, "transcription");
  const hasPhoneticUs = hasDictionaryField(detail, null, "phonetic_us");
  const title = detail?.word || `ID: ${entryId}`;

  return (
    <CrudEditPage
      title={t.editEntry}
      breadcrumbs={[
        { title: "CronoLex", path: "/admin" },
        { title: t.dictionary, path: "/admin" },
        { title },
      ]}
      actions={(
        <Button type="button" variant="outlined" startIcon={<ArrowLeft size={16} />} onClick={() => onBack()}>
          {t.close}
        </Button>
      )}
    >
      <CrudFormSurface sx={{ width: "100%" }}>
        <Stack spacing={0.5}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{title}</Typography>
          <Typography variant="body2" color="text.secondary">ID: {entryId}</Typography>
        </Stack>
        <Box id="dictionary-entry-form" component="form" onSubmit={submit} sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {(error || entryQuery.error) && <Alert severity="error">{error || entryQuery.error?.message || t.loadError}</Alert>}
          <TextField label={t.word} value={form.word} onChange={(event) => setField("word", event.target.value)} required fullWidth />
          <TextField
            label={t.entryType}
            value={form.entry_type}
            onChange={(event) => setField("entry_type", event.target.value)}
            select
            fullWidth
          >
            {DICTIONARY_ENTRY_TYPE_OPTIONS.map((option) => (
              <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
            ))}
          </TextField>
          {hasTranscription && (
            <TextField label={t.transcription} value={form.transcription} onChange={(event) => setField("transcription", event.target.value)} fullWidth />
          )}
          {hasPhoneticUs && (
            <TextField label={t.phoneticUs} value={form.phonetic_us} onChange={(event) => setField("phonetic_us", event.target.value)} fullWidth />
          )}
          <TextField label={t.translationUk} value={form.translation_uk} onChange={(event) => setField("translation_uk", event.target.value)} fullWidth />
          <TextField label={t.translationRu} value={form.translation_ru} onChange={(event) => setField("translation_ru", event.target.value)} fullWidth />
          <TextField label={t.translationPl} value={form.translation_pl} onChange={(event) => setField("translation_pl", event.target.value)} fullWidth />
          <TextField
            label={t.examplesOnePerLine}
            value={form.examples_text}
            onChange={(event) => setField("examples_text", event.target.value)}
            multiline
            minRows={6}
            fullWidth
          />
          {entryQuery.isFetching && (
            <Stack direction="row" spacing={1} alignItems="center" color="text.secondary">
              <CircularProgress size={18} />
              <Typography variant="body2">{t.loading}</Typography>
            </Stack>
          )}
        </Box>

        <Stack direction="row" justifyContent="flex-end" spacing={1.5} sx={{ pt: 1 }}>
          <Button type="button" variant="outlined" onClick={() => onBack()}>{t.close}</Button>
          <Button type="submit" form="dictionary-entry-form" variant="contained" startIcon={<Save size={16} />} disabled={saveMutation.isPending || entryQuery.isFetching}>
            {saveMutation.isPending ? t.saving : t.save}
          </Button>
        </Stack>
      </CrudFormSurface>
    </CrudEditPage>
  );
}
