import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, ExternalLink, Volume2 } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import {
  fetchUserDictionaryEntryDetail,
  fetchUserDictionaryEntries,
  fetchUserDictionaryFilterMetadata,
  bulkActionUserDictionaryEntries,
  userDictionaryQueryKeys,
} from "./api/userDictionaryApi";
import {
  applyUserDictionaryParamUpdates,
  userDictionaryParamsFromSearch,
} from "./helpers/listParams";
import {
  CrudPage,
  CrudTableSurface,
  DetailGrid,
  DetailPanel,
  EmptyState,
  FilterBar,
  JsonPreview,
  LinkButton,
  LogField,
  LogToolbar,
  MultiSelect,
  Pager,
  Placeholder,
} from "../../shared/components";
import { dataTableContainerSx } from "../../shared/components/dataTableStyles";
import { filterActionButtonSx, filterControlSx } from "../../shared/components/filterControls";

const USER_DICTIONARY_BULK_ACTIONS = [
  { value: "promote_to_base", labelKey: "promoteToBase", fallback: "Promote to base" },
  { value: "reject", labelKey: "rejectUserWords", fallback: "Reject" },
  { value: "rebuild_details", labelKey: "rebuildDetails", fallback: "Rebuild details" },
  { value: "rebuild_embedding", labelKey: "rebuildEmbedding", fallback: "Rebuild embedding" },
];

const userDictionaryActionIconSx = {
  border: 1,
  borderColor: "divider",
  borderRadius: 1,
};

const FAILURE_REASON_SUMMARY_MAX_LENGTH = 72;

export function UserDictionaryPage({ t, onOpenEntry }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const [selectedIds, setSelectedIds] = useState([]);
  const [bulkAction, setBulkAction] = useState("promote_to_base");
  const params = useMemo(() => userDictionaryParamsFromSearch(searchParams), [searchParams]);
  const filtersQuery = useQuery({
    queryKey: userDictionaryQueryKeys.filterMetadata(),
    queryFn: fetchUserDictionaryFilterMetadata,
  });
  const entriesQuery = useQuery({
    queryKey: userDictionaryQueryKeys.list(params),
    queryFn: () => fetchUserDictionaryEntries(params),
  });
  const filters = filtersQuery.data || null;
  const items = useMemo(() => entriesQuery.data?.items || [], [entriesQuery.data?.items]);
  const loading = entriesQuery.isFetching;
  const bulkMutation = useMutation({
    mutationFn: bulkActionUserDictionaryEntries,
    onSuccess: () => {
      setSelectedIds([]);
      queryClient.invalidateQueries({ queryKey: userDictionaryQueryKeys.all });
    },
  });
  const selectableItems = useMemo(() => items.filter((item) => isSelectableForBulkAction(item, bulkAction)), [items, bulkAction]);
  const selectedIdSet = useMemo(() => new Set(selectedIds), [selectedIds]);
  const allSelected = selectableItems.length > 0 && selectableItems.every((item) => selectedIdSet.has(item.id));
  const error = entriesQuery.error || bulkMutation.error;

  useEffect(() => {
    setSelectedIds((current) => {
      const next = current.filter((id) => selectableItems.some((item) => item.id === id));
      return next.length === current.length ? current : next;
    });
  }, [selectableItems]);

  function updateParams(updates) {
    setSearchParams((current) => applyUserDictionaryParamUpdates(current, updates));
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

  function executeBulkAction() {
    if (selectedIds.length === 0) return;
    bulkMutation.mutate({ action: bulkAction, entryIds: selectedIds });
  }

  return (
    <CrudPage
      title={t.userDictionary || "User words"}
      breadcrumbs={[
        { title: "CronoLex", path: "/admin" },
        { title: t.dictionary, path: "/admin" },
        { title: t.userDictionary || "User words" },
      ]}
    >
      <FilterBar>
        <LogToolbar
          t={t}
          search={params.search}
          onSearch={(search) => updateParams({ search, page: 1 })}
        />
        <MultiSelect label={t.status} options={filterOptions(filters, "status")} value={params.statuses} onChange={(statuses) => updateParams({ statuses, page: 1 })} />
        <MultiSelect label={t.partOfSpeech || t.pos} options={filterOptions(filters, "part_of_speech")} value={params.partsOfSpeech} onChange={(partsOfSpeech) => updateParams({ partsOfSpeech, page: 1 })} />
        <MultiSelect label={t.level || "Level"} options={filterOptions(filters, "level_id")} value={params.levelIds} onChange={(levelIds) => updateParams({ levelIds, page: 1 })} />
        <FormControl size="small" sx={filterControlSx}>
          <InputLabel id="user-dictionary-bulk-action-label">{t.bulkAction || "Bulk action"}</InputLabel>
          <Select
            labelId="user-dictionary-bulk-action-label"
            label={t.bulkAction || "Bulk action"}
            value={bulkAction}
            onChange={(event) => {
              setBulkAction(event.target.value);
              setSelectedIds([]);
            }}
          >
            {USER_DICTIONARY_BULK_ACTIONS.map((action) => (
              <MenuItem key={action.value} value={action.value}>
                {t[action.labelKey] || action.fallback}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button
          variant="outlined"
          startIcon={<CheckCircle2 size={16} />}
          disabled={selectedIds.length === 0 || bulkMutation.isPending}
          onClick={executeBulkAction}
          sx={filterActionButtonSx}
        >
          {t.execute || "Execute"} {selectedIds.length ? `(${selectedIds.length})` : ""}
        </Button>
      </FilterBar>
      {error && <Alert severity="error">{error.message || t.loadError}</Alert>}

      <CrudTableSurface sx={dataTableContainerSx}>
        <Table size="small" sx={{ minWidth: 1180 }}>
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  size="small"
                  checked={allSelected}
                  indeterminate={selectedIds.length > 0 && !allSelected}
                  disabled={selectableItems.length === 0 || bulkMutation.isPending}
                  onChange={(event) => toggleAllSelected(event.target.checked)}
                />
              </TableCell>
              <TableCell>{t.word}</TableCell>
              <TableCell>{t.status}</TableCell>
              <TableCell>{t.level || "Level"}</TableCell>
              <TableCell>{t.partOfSpeech || t.pos}</TableCell>
              <TableCell>{t.translations}</TableCell>
              <TableCell>{t.examples}</TableCell>
              <TableCell>{t.assignments || "Assignments"}</TableCell>
              <TableCell>{t.audio}</TableCell>
              <TableCell>{t.created || "Created"}</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((item) => {
              const selectable = isSelectableForBulkAction(item, bulkAction);
              const failureReasonSummary = summarizeFailureReason(item.failure_reason);
              return (
                <TableRow hover key={item.id}>
                  <TableCell padding="checkbox" sx={{ verticalAlign: "top" }}>
                    <Checkbox
                      size="small"
                      checked={selectedIdSet.has(item.id)}
                      disabled={!selectable || bulkMutation.isPending}
                      onChange={(event) => toggleSelected(item.id, event.target.checked)}
                    />
                  </TableCell>
                  <TableCell sx={{ verticalAlign: "top", minWidth: 170 }}>
                    <Stack spacing={0.25} sx={{ alignItems: "flex-start" }}>
                      <Typography variant="subtitle2" component="strong" sx={{ display: "block" }}>
                        {item.word || `#${item.id}`}
                      </Typography>
                      {item.promoted_dictionary_entry_id && (
                        <Chip label={`Core #${item.promoted_dictionary_entry_id}`} size="small" variant="outlined" />
                      )}
                    </Stack>
                  </TableCell>
                  <TableCell sx={{ verticalAlign: "top", minWidth: 140 }}>
                    <Stack spacing={0.5} sx={{ alignItems: "flex-start" }}>
                      <Chip label={item.status || "-"} size="small" variant="outlined" />
                      {failureReasonSummary && (
                        <Typography
                          variant="caption"
                          color="error.main"
                          title={item.failure_reason}
                          sx={{
                            display: "block",
                            maxWidth: 180,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {failureReasonSummary}
                        </Typography>
                      )}
                    </Stack>
                  </TableCell>
                  <TableCell sx={{ verticalAlign: "top", minWidth: 84 }}>
                    {item.level_title || (item.level_id ? `#${item.level_id}` : "-")}
                  </TableCell>
                  <TableCell sx={{ verticalAlign: "top", color: "text.secondary", minWidth: 120 }}>
                    {item.part_of_speech || "-"}
                  </TableCell>
                  <TableCell sx={{ verticalAlign: "top", minWidth: 180 }}>
                    <Stack spacing={0.25}>
                      {translationRows(item).map((row) => (
                        <Typography variant="body2" color="text.secondary" key={row.label}>
                          {row.label}: {row.value}
                        </Typography>
                      ))}
                    </Stack>
                  </TableCell>
                  <TableCell sx={{ verticalAlign: "top", minWidth: 200 }}>
                    <Stack spacing={0.75}>
                      {(item.examples_json || []).slice(0, 3).map((example, index) => (
                        <Typography variant="body2" color="text.secondary" key={index}>{example}</Typography>
                      ))}
                    </Stack>
                  </TableCell>
                  <TableCell sx={{ verticalAlign: "top", minWidth: 120 }}>
                    {item.assignment_count ?? 0}
                  </TableCell>
                  <TableCell sx={{ verticalAlign: "top", minWidth: 160 }}>
                    {item.audio_url ? (
                      <Box component="audio" controls preload="none" src={item.audio_url} sx={{ width: 160, maxWidth: "100%" }} />
                    ) : (
                      <Stack direction="row" spacing={0.75} color="text.secondary" sx={{ alignItems: "center" }}>
                        <Volume2 size={16} />
                        <Typography variant="body2">{t.missingAudio}</Typography>
                      </Stack>
                    )}
                  </TableCell>
                  <TableCell sx={{ verticalAlign: "top", minWidth: 150, color: "text.secondary" }}>
                    {item.created || "-"}
                  </TableCell>
                  <TableCell align="right" sx={{ verticalAlign: "top", width: 48, minWidth: 48 }}>
                    <IconButton
                      size="small"
                      title={t.showDetails || "Details"}
                      aria-label={t.showDetails || "Details"}
                      onClick={() => onOpenEntry?.(item.id)}
                      sx={userDictionaryActionIconSx}
                    >
                      <ExternalLink size={18} />
                    </IconButton>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        {!error && items.length === 0 && !loading && <EmptyState text={t.emptyLogs} />}
        {loading && (
          <Stack
            spacing={1}
            sx={{
              alignItems: "center",
              position: "absolute",
              inset: 0,
              justifyContent: "center",
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
      <Pager page={params.page} pageSize={params.pageSize} total={entriesQuery.data?.total || 0} onPageChange={(page) => updateParams({ page })} onPageSizeChange={(pageSize) => updateParams({ pageSize, page: 1 })} />
    </CrudPage>
  );
}

export function UserDictionaryEntryDetailPage({ t, entryId, onBack, onOpenErrorLogSearch }) {
  const detailQuery = useQuery({
    queryKey: userDictionaryQueryKeys.detail(entryId),
    queryFn: () => fetchUserDictionaryEntryDetail(entryId),
    enabled: Boolean(entryId),
  });
  if (!entryId) return <Placeholder title={t.userDictionaryEntryDetail || "User word details"} description={t.sectionScaffold} />;

  const entry = detailQuery.data?.entry || {};
  const importItems = entry.import_items || [];
  return (
    <CrudPage
      title={`${t.userDictionaryEntryDetail || "User word details"} #${entryId}`}
      breadcrumbs={[
        { title: "CronoLex", path: "/admin" },
        { title: t.userDictionary || "User words", path: "/admin/user-dictionary" },
        { title: t.userDictionaryEntryDetail || "Details" },
      ]}
      actions={
        <Button variant="outlined" startIcon={<ArrowLeft size={16} />} onClick={onBack}>
          {t.userDictionary || "User words"}
        </Button>
      }
    >
      {detailQuery.error && <Alert severity="error">{detailQuery.error.message || t.loadError}</Alert>}
      {detailQuery.isFetching && <Typography color="text.secondary">{t.loading}</Typography>}
      {detailQuery.data && (
        <Stack spacing={2}>
          {entry.failure_reason && <Alert severity="error">{entry.failure_reason}</Alert>}
          <DetailGrid>
            <DetailPanel title={t.word || "Word"}>
              <LogField label="ID" value={entry.id} />
              <LogField label={t.word || "Word" } value={entry.word} />
              <LogField label={t.status || "Status"} value={entry.status} />
              <LogField label={t.level || "Level"} value={entry.level_title || entry.level_id} />
              <LogField label={t.partOfSpeech || t.pos} value={entry.part_of_speech} />
              <LogField label="Entry type" value={entry.entry_type} />
            </DetailPanel>
            <DetailPanel title={t.translations || "Translations"}>
              {translationRows(entry).map((row) => (
                <LogField key={row.label} label={row.label} value={row.value} />
              ))}
              {translationRows(entry).length === 0 && <Typography color="text.secondary">-</Typography>}
            </DetailPanel>
            <DetailPanel title={t.context || "Context"}>
              <LogField label={t.assignments || "Assignments"} value={entry.assignment_count ?? 0} />
              <LogField label="Embedding" value={entry.is_embedding_ready ? "ready" : "not ready"} />
              <LogField label="Model" value={entry.embedding_model} />
              <LogField label={t.created || "Created"} value={entry.created} />
              <LogField label={t.updated || "Updated"} value={entry.updated} />
            </DetailPanel>
          </DetailGrid>
          <DetailGrid>
            <DetailPanel title={t.examples || "Examples"}>
              <Stack spacing={0.75}>
                {(entry.examples_json || []).map((example, index) => (
                  <Typography key={index} variant="body2">{example}</Typography>
                ))}
                {(entry.examples_json || []).length === 0 && <Typography color="text.secondary">-</Typography>}
              </Stack>
            </DetailPanel>
            <DetailPanel title={t.errorText || "Error"}>
              <LogField label={t.errorText || "Error"} value={entry.failure_reason} />
              <LinkButton onClick={() => onOpenErrorLogSearch?.(entry.error_log_search || `user_dictionary_entry_id=${entryId}`)}>
                {t.errorLog || "Error log"}
              </LinkButton>
            </DetailPanel>
            <DetailPanel title={t.importItems || "Import items"}>
              <Stack spacing={1}>
                {importItems.map((item) => (
                  <Box key={item.id} sx={{ borderBottom: 1, borderColor: "divider", pb: 1 }}>
                    <LogField layout="inline" label="ID" value={item.id} />
                    <LogField layout="inline" label={t.status || "Status"} value={item.status} />
                    <LogField layout="inline" label={t.importJob || "Import job"} value={item.import_job_id} />
                    <LogField layout="inline" label={t.errorText || "Error"} value={item.error_text} />
                  </Box>
                ))}
                {importItems.length === 0 && <Typography color="text.secondary">-</Typography>}
              </Stack>
            </DetailPanel>
          </DetailGrid>
          <JsonPreview title="Provider status" value={entry.source_provider_status_json} />
        </Stack>
      )}
    </CrudPage>
  );
}

function isSelectableForBulkAction(item, action) {
  if (action === "promote_to_base") return isPromotableUserDictionaryEntry(item);
  if (action === "reject") return item.status !== "rejected" && !item.promoted_dictionary_entry_id;
  if (action === "rebuild_details") return item.status === "details_failed";
  if (action === "rebuild_embedding") return canRebuildEmbedding(item);
  return false;
}

function isPromotableUserDictionaryEntry(item) {
  return item.status === "ready_for_rotation" && !item.promoted_dictionary_entry_id;
}

function canRebuildEmbedding(item) {
  if (item.is_embedding_ready) return false;
  if (!["queued_for_embedding", "embedding_failed"].includes(item.status)) return false;
  if (!item.translation_uk || !item.part_of_speech) return false;
  return (item.examples_json || []).length > 0;
}

function summarizeFailureReason(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  if (text.includes("bad response/schema error:")) {
    return text.replace(/\s*bad response\/schema error:.*/u, " bad response").trim();
  }
  const firstLine = text.split(/\r?\n/u)[0].trim();
  if (firstLine.length <= FAILURE_REASON_SUMMARY_MAX_LENGTH) return firstLine;
  return `${firstLine.slice(0, FAILURE_REASON_SUMMARY_MAX_LENGTH - 3).trimEnd()}...`;
}

function filterOptions(filters, name) {
  return filters?.filters?.find((item) => item.name === name)?.options || [];
}

function translationRows(item) {
  return [
    { label: "uk", value: item.translation_uk },
    { label: "ru", value: item.translation_ru },
    { label: "pl", value: item.translation_pl },
  ].filter((row) => row.value);
}
