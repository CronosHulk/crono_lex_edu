import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Chip,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { formatUserTitle } from "../users";
import {
  fetchImportItemFilters,
  fetchImportItems,
  fetchImportJobDetail,
  fetchImportJobFilters,
  fetchImportJobItems,
  fetchImportJobs,
  importsQueryKeys,
} from "./api/importsApi";
import {
  applyImportItemsParamUpdates,
  applyImportJobItemsParamUpdates,
  applyImportJobsParamUpdates,
  importItemsParamsFromSearch,
  importJobItemsParamsFromSearch,
  importJobsParamsFromSearch,
} from "./helpers/listParams";
import {
  ActionRow,
  ChipRow,
  CrudPage,
  DetailGrid,
  InlineDetailBlock,
  InlineDetailGrid,
  DetailPanel,
  EmptyState,
  LinkButton,
  ListCard,
  LoadingLine,
  PreLine,
  SideMeta,
  TitleRow,
  FilterBar,
  JsonPreview,
  LogField,
  LogToolbar,
  MultiSelect,
  Pager,
  Placeholder,
} from "../../shared/components";
import { filterControlSx } from "../../shared/components/filterControls";

export function ImportJobsPage({ t, onOpenImportJob, onOpenUser, onOpenTaskLog }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const params = useMemo(() => importJobsParamsFromSearch(searchParams), [searchParams]);
  const filtersQuery = useQuery({
    queryKey: importsQueryKeys.jobFilters(),
    queryFn: fetchImportJobFilters,
  });
  const importJobsQuery = useQuery({
    queryKey: importsQueryKeys.jobList(params),
    queryFn: () => fetchImportJobs(params),
  });
  const filters = filtersQuery.data || null;
  const items = importJobsQuery.data?.items || [];
  const error = importJobsQuery.error?.message || "";
  const loading = importJobsQuery.isFetching;

  function updateParams(updates) {
    setSearchParams((current) => applyImportJobsParamUpdates(current, updates));
  }

  return (
    <CrudPage
      title={t.importJobs}
      breadcrumbs={[{ title: "CronoLex", path: "/admin" }, { title: t.logs }, { title: t.importJobs }]}
    >
      <FilterBar>
        <LogToolbar
          t={t}
          search={params.search}
          onSearch={(value) => updateParams({ search: value, page: 1 })}
        />
        <MultiSelect label={t.status} options={filters?.filters?.find((item) => item.name === "status")?.options || []} value={params.statuses} onChange={(statuses) => updateParams({ statuses, page: 1 })} />
        <MultiSelect label={t.source} options={filters?.filters?.find((item) => item.name === "source_type")?.options || []} value={params.sourceTypes} onChange={(sourceTypes) => updateParams({ sourceTypes, page: 1 })} />
      </FilterBar>
      {error && <Alert severity="error">{error}</Alert>}
      <Stack spacing={1.5}>
        {!error && items.length === 0 && !loading && <EmptyState text={t.emptyLogs} />}
        {items.map((item) => (
          <ListCard key={item.id}>
            <Box sx={{ minWidth: 0 }}>
              <TitleRow label={item.status} title={`${t.importJob} #${item.id}`} />
              <Typography variant="body2" color="text.secondary">{[item.source_type, item.source_identifier].filter(Boolean).join(" · ") || "-"}</Typography>
              <ActionRow>
                <LinkButton onClick={() => onOpenImportJob(item.id)}>{t.importJobDetail}</LinkButton>
                {item.user_id && <LinkButton onClick={() => onOpenUser(item.user_id)}>{t.openUser}</LinkButton>}
                {item.task_log_id && <LinkButton onClick={() => onOpenTaskLog(item.task_log_id)}>{t.openTaskLog}</LinkButton>}
              </ActionRow>
              <ChipRow>
                <Chip label={`Total: ${item.total_items ?? 0}`} size="small" variant="outlined" />
                <Chip label={`Processed: ${item.processed_items ?? 0}`} size="small" variant="outlined" />
                <Chip label={`Success: ${item.successful_items ?? 0}`} size="small" variant="outlined" />
                <Chip label={`Failed: ${item.failed_items ?? 0}`} size="small" variant="outlined" />
              </ChipRow>
              {item.last_error && <Alert severity="error" sx={{ mt: 1, whiteSpace: "pre-line" }}>{item.last_error}</Alert>}
            </Box>
            <SideMeta>
              <LogField layout="inline" label="User" value={item.user_id} />
              <LogField layout="inline" label={t.sourceType} value={item.source_type} />
              <LogField layout="inline" label={t.started} value={item.created} />
              <LogField layout="inline" label={t.finished} value={item.completed} />
            </SideMeta>
          </ListCard>
        ))}
        {loading && <LoadingLine text={t.loading} />}
      </Stack>
      <Pager page={params.page} pageSize={params.pageSize} total={importJobsQuery.data?.total || 0} onPageChange={(page) => updateParams({ page })} onPageSizeChange={(pageSize) => updateParams({ pageSize, page: 1 })} />
    </CrudPage>
  );
}

export function ImportItemsPage({ t, onOpenImportJob, onOpenUser, onOpenTaskLog }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const params = useMemo(() => importItemsParamsFromSearch(searchParams), [searchParams]);
  const filtersQuery = useQuery({
    queryKey: importsQueryKeys.itemFilters(),
    queryFn: fetchImportItemFilters,
  });
  const importItemsQuery = useQuery({
    queryKey: importsQueryKeys.itemList(params),
    queryFn: () => fetchImportItems(params),
  });
  const filters = filtersQuery.data || null;
  const items = importItemsQuery.data?.items || [];
  const error = importItemsQuery.error?.message || "";
  const loading = importItemsQuery.isFetching;

  function updateParams(updates) {
    setSearchParams((current) => applyImportItemsParamUpdates(current, updates));
  }

  return (
    <CrudPage
      title={t.importItems}
      breadcrumbs={[{ title: "CronoLex", path: "/admin" }, { title: t.logs }, { title: t.importItems }]}
    >
      <FilterBar>
        <LogToolbar
          t={t}
          search={params.search}
          onSearch={(value) => updateParams({ search: value, page: 1 })}
        />
        <MultiSelect label={t.status} options={filters?.filters?.find((item) => item.name === "status")?.options || []} value={params.statuses} onChange={(statuses) => updateParams({ statuses, page: 1 })} />
        <TextField label={t.importJob} inputMode="numeric" value={params.importJobId} sx={filterControlSx} onChange={(event) => updateParams({ importJobId: event.target.value, page: 1 })} />
        <TextField label="User UUID" value={params.userId} sx={filterControlSx} onChange={(event) => updateParams({ userId: event.target.value, page: 1 })} />
      </FilterBar>
      {error && <Alert severity="error">{error}</Alert>}
      <Stack spacing={1.5}>
        {!error && items.length === 0 && !loading && <EmptyState text={t.emptyLogs} />}
        {items.map((item) => (
          <ListCard key={item.id}>
            <Box sx={{ minWidth: 0 }}>
              <TitleRow label={item.status} title={item.lookup_word || item.raw_value || `${t.importItem} #${item.id}`} />
              <Typography variant="body2" color="text.secondary">{t.importJob}: {item.import_job_id} · User: {item.user_id}</Typography>
              <ActionRow>
                {item.import_job_id && <LinkButton onClick={() => onOpenImportJob(item.import_job_id)}>{t.openImportJob}</LinkButton>}
                {item.user_id && <LinkButton onClick={() => onOpenUser(item.user_id)}>{t.openUser}</LinkButton>}
                {item.task_log_id && <LinkButton onClick={() => onOpenTaskLog(item.task_log_id)}>{t.openTaskLog}</LinkButton>}
              </ActionRow>
              <PreLine>{item.raw_value || "-"}</PreLine>
              {(item.validated_lookup_word || item.validated_part_of_speech || item.validated_translation_uk || item.translation_hint) && (
                <Stack spacing={0.25} sx={{ mt: 1 }}>
                  {item.validated_lookup_word && <Typography variant="caption" color="text.secondary">{t.importAiForm}: {item.validated_lookup_word}</Typography>}
                  {item.validated_part_of_speech && <Typography variant="caption" color="text.secondary">{t.partOfSpeech}: {item.validated_part_of_speech}</Typography>}
                  {(item.validated_translation_uk || item.translation_hint) && <Typography variant="caption" color="text.secondary">{t.importParsedTranslation}: {item.validated_translation_uk || item.translation_hint}</Typography>}
                </Stack>
              )}
              <ChipRow>
                {item.existing_word_id && <Chip label={`Word #${item.existing_word_id}`} size="small" variant="outlined" />}
                {item.user_dictionary_entry_id && <Chip label={`User word #${item.user_dictionary_entry_id}`} size="small" variant="outlined" />}
                {item.task_log_id && <Chip label={`Task #${item.task_log_id}`} size="small" variant="outlined" />}
              </ChipRow>
              {item.error_text && <Alert severity="error" sx={{ mt: 1, whiteSpace: "pre-line" }}>{item.error_text}</Alert>}
            </Box>
            <SideMeta>
              <LogField layout="inline" label="ID" value={item.id} />
              <LogField layout="inline" label={t.lookupWord} value={item.lookup_word} />
              <LogField layout="inline" label={t.started} value={item.created} />
              <LogField layout="inline" label={t.finished} value={item.processed} />
            </SideMeta>
          </ListCard>
        ))}
        {loading && <LoadingLine text={t.loading} />}
      </Stack>
      <Pager page={params.page} pageSize={params.pageSize} total={importItemsQuery.data?.total || 0} onPageChange={(page) => updateParams({ page })} onPageSizeChange={(pageSize) => updateParams({ pageSize, page: 1 })} />
    </CrudPage>
  );
}

export function ImportJobDetailPage({ t, importJobId, onBack, onOpenUser, onOpenTaskLog }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const pageParams = useMemo(() => importJobItemsParamsFromSearch(searchParams), [searchParams]);
  const detailQuery = useQuery({
    queryKey: importsQueryKeys.jobDetail(importJobId),
    queryFn: () => fetchImportJobDetail(importJobId),
    enabled: Boolean(importJobId),
  });
  const itemsParams = useMemo(() => ({
    importJobId,
    page: pageParams.itemsPage,
    pageSize: pageParams.itemsPageSize,
    statuses: pageParams.itemStatuses,
  }), [importJobId, pageParams.itemStatuses, pageParams.itemsPage, pageParams.itemsPageSize]);
  const importItemsQuery = useQuery({
    queryKey: importsQueryKeys.jobItems(itemsParams),
    queryFn: () => fetchImportJobItems(itemsParams),
    enabled: Boolean(importJobId),
  });

  function updateItemsParams(updates) {
    setSearchParams((current) => applyImportJobItemsParamUpdates(current, updates));
  }

  if (!importJobId) return <Placeholder title={t.importJobDetail} description={t.sectionScaffold} />;

  const data = detailQuery.data;
  const items = importItemsQuery.data?.items || [];
  const job = data?.job || {};
  const submittedUser = data?.user;
  return (
    <CrudPage
      title={`${t.importJobDetail} #${importJobId}`}
      breadcrumbs={[{ title: "CronoLex", path: "/admin" }, { title: t.importJobs, path: "/admin/import-jobs" }, { title: t.importJobDetail }]}
      actions={<Button variant="outlined" onClick={onBack}>{t.importJobs}</Button>}
    >
      <Typography variant="body2" color="text.secondary">{[job.source_type, job.source_identifier].filter(Boolean).join(" · ") || "-"}</Typography>
      {detailQuery.error && <Alert severity="error">{detailQuery.error.message || t.loadError}</Alert>}
      {detailQuery.isFetching && <LoadingLine text={t.loading} />}
      {data && (
        <>
          <DetailGrid>
            <DetailPanel title={t.importJob}>
              <LogField label="ID" value={job.id} />
              <LogField label="Status" value={job.status} />
              <LogField label={t.submittedBy} value={submittedUser ? formatUserTitle(submittedUser) : job.user_id} />
              {job.user_id && <LinkButton onClick={() => onOpenUser(job.user_id)}>{t.openUser}</LinkButton>}
              <LogField label={t.source} value={[job.source_type, job.source_identifier].filter(Boolean).join(" · ")} />
              <LogField label="Storage" value={job.storage_path} />
              <LogField label={t.started} value={job.created} />
              <LogField label={t.finished} value={job.completed} />
            </DetailPanel>
            <DetailPanel title={t.statusCounts}>
              <ChipRow>
                {Object.entries(data.status_counts || {}).map(([status, count]) => (
                  <Chip
                    clickable
                    color={pageParams.itemStatuses.includes(status) ? "primary" : "default"}
                    label={`${status}: ${count}`}
                    key={status}
                    size="small"
                    variant={pageParams.itemStatuses.includes(status) ? "filled" : "outlined"}
                    onClick={() => updateItemsParams({ itemStatuses: pageParams.itemStatuses.includes(status) ? [] : [status], itemsPage: 1 })}
                  />
                ))}
              </ChipRow>
              {pageParams.itemStatuses.length > 0 && (
                <Button size="small" variant="text" onClick={() => updateItemsParams({ itemStatuses: [], itemsPage: 1 })}>
                  {t.clearFilters || "Clear filters"}
                </Button>
              )}
              {Object.keys(data.status_counts || {}).length === 0 && <Typography color="text.secondary">-</Typography>}
              <LogField label="Total" value={job.total_items} />
              <LogField label="Processed" value={job.processed_items} />
              <LogField label="Success" value={job.successful_items} />
              <LogField label="Failed" value={job.failed_items} />
            </DetailPanel>
            <DetailPanel title={t.context}>
              <LogField label={t.originTask} value={data.origin_task_log?.id} />
              {data.origin_task_log?.id && <LinkButton onClick={() => onOpenTaskLog(data.origin_task_log.id)}>{t.openTaskLog}</LinkButton>}
              <LogField label={t.processingTask} value={data.processing_task_log?.id} />
              {data.processing_task_log?.id && <LinkButton onClick={() => onOpenTaskLog(data.processing_task_log.id)}>{t.openTaskLog}</LinkButton>}
            </DetailPanel>
          </DetailGrid>
          {job.last_error && <Alert severity="error" sx={{ whiteSpace: "pre-line" }}>{job.last_error}</Alert>}
          <DetailGrid>
            <DetailPanel title={t.originTask}>
              <JsonPreview title={t.resultJson || "JSON"} value={data.origin_task_log} />
            </DetailPanel>
            <DetailPanel title={t.processingTask}>
              <JsonPreview title={t.resultJson || "JSON"} value={data.processing_task_log} />
            </DetailPanel>
            <DetailPanel title={t.context}>
              <LogField label="Storage" value={job.storage_path} />
              <LogField label={t.source} value={[job.source_type, job.source_identifier].filter(Boolean).join(" · ")} />
            </DetailPanel>
          </DetailGrid>
          <Stack spacing={1.5}>
            {!importItemsQuery.error && items.length === 0 && !importItemsQuery.isFetching && <EmptyState text={t.emptyLogs} />}
            {items.map((item) => (
              <ListCard key={item.id}>
                <Box sx={{ minWidth: 0 }}>
                  <TitleRow label={item.status} title={item.lookup_word || item.validated_lookup_word || `${t.importItem} #${item.id}`} />
                  <Typography variant="body2" color="text.secondary">
                    ID: {item.id} · {t.rawValue}: {item.raw_value || "-"}
                  </Typography>
                  <ActionRow>
                    {item.task_log_id && <LinkButton onClick={() => onOpenTaskLog(item.task_log_id)}>Task #{item.task_log_id}</LinkButton>}
                  </ActionRow>
                  <InlineDetailGrid>
                    <InlineDetailBlock title={t.importAiForm}>
                      <LogField label={t.lookupWord} value={item.validated_lookup_word || item.lookup_word} />
                      <LogField label={t.partOfSpeech} value={item.validated_part_of_speech} />
                      <LogField label={t.importParsedTranslation} value={item.validated_translation_uk || item.translation_hint} />
                    </InlineDetailBlock>
                    <InlineDetailBlock title={t.context}>
                      <ChipRow>
                        {item.existing_word_id && <Chip label={`Word #${item.existing_word_id}`} size="small" variant="outlined" />}
                        {item.user_dictionary_entry_id && <Chip label={`User word #${item.user_dictionary_entry_id}`} size="small" variant="outlined" />}
                        {item.task_log_id && <Chip label={`Task #${item.task_log_id}`} size="small" variant="outlined" />}
                      </ChipRow>
                    </InlineDetailBlock>
                    <InlineDetailBlock title={t.errorText}>
                      {item.error_text ? <Alert severity="error" sx={{ whiteSpace: "pre-line" }}>{item.error_text}</Alert> : <Typography color="text.secondary">-</Typography>}
                    </InlineDetailBlock>
                  </InlineDetailGrid>
                </Box>
                <SideMeta>
                  <LogField layout="inline" label={t.created || t.date} value={item.created} />
                  <LogField layout="inline" label={t.finished} value={item.processed} />
                </SideMeta>
              </ListCard>
            ))}
          </Stack>
          {importItemsQuery.error && <Alert severity="error">{importItemsQuery.error.message || t.loadError}</Alert>}
          {importItemsQuery.isFetching && <LoadingLine text={t.loading} />}
          <Pager
            page={pageParams.itemsPage}
            pageSize={pageParams.itemsPageSize}
            total={importItemsQuery.data?.total || 0}
            onPageChange={(itemsPage) => updateItemsParams({ itemsPage })}
            onPageSizeChange={(itemsPageSize) => updateItemsParams({ itemsPageSize, itemsPage: 1 })}
          />
        </>
      )}
    </CrudPage>
  );
}
