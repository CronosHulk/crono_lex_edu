import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { Alert, Box, Button, Stack, Typography } from "@mui/material";

import {
  ActionRow,
  CrudPage,
  DetailGrid,
  InlineDetailBlock,
  InlineDetailGrid,
  DetailPanel,
  EmptyState,
  EntityLinksFromJson,
  FilterBar,
  JsonPreview,
  LinkButton,
  ListCard,
  LoadingLine,
  LogField,
  LogToolbar,
  MultiSelect,
  Pager,
  Placeholder,
  PreLine,
  SideMeta,
  TitleRow,
} from "../../shared/components";
import {
  fetchErrorLogFilters,
  fetchErrorLogs,
  fetchTaskLogDetail,
  fetchTaskLogFilters,
  fetchTaskLogs,
  logsQueryKeys,
} from "./api/logsApi";
import {
  applyErrorLogsParamUpdates,
  applyTaskLogsParamUpdates,
  errorLogsParamsFromSearch,
  taskLogsParamsFromSearch,
} from "./helpers/listParams";

export function TaskLogsPage({ t, user, onOpenImportJob, onOpenUser, onOpenTaskLog }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const params = useMemo(() => ({ ...taskLogsParamsFromSearch(searchParams), scope: "operations" }), [searchParams]);
  const filtersQuery = useQuery({
    queryKey: logsQueryKeys.taskLogFilters("operations"),
    queryFn: () => fetchTaskLogFilters("operations"),
  });
  const taskLogsQuery = useQuery({
    queryKey: logsQueryKeys.taskLogList(params),
    queryFn: () => fetchTaskLogs(params),
  });
  const filters = filtersQuery.data || null;
  const items = taskLogsQuery.data?.items || [];
  const error = taskLogsQuery.error?.message || "";
  const loading = taskLogsQuery.isFetching;

  function updateParams(updates) {
    setSearchParams((current) => applyTaskLogsParamUpdates(current, updates));
  }

  return (
    <CrudPage
      title={t.taskLogs}
      breadcrumbs={[{ title: "CronoLex", path: "/admin" }, { title: t.logs }, { title: t.taskLogs }]}
    >
      <FilterBar>
        <LogToolbar
          t={t}
          search={params.search}
          onSearch={(value) => updateParams({ search: value, page: 1 })}
        />
        <MultiSelect label={t.taskType || "Task type"} options={filters?.filters?.find((item) => item.name === "task_type")?.options || []} value={params.taskTypes} onChange={(taskTypes) => updateParams({ taskTypes, page: 1 })} />
        <MultiSelect label={t.status} options={filters?.filters?.find((item) => item.name === "status")?.options || []} value={params.statuses} onChange={(statuses) => updateParams({ statuses, page: 1 })} />
      </FilterBar>
      {error && <Alert severity="error">{error}</Alert>}
      <Stack spacing={1.5}>
        {!error && items.length === 0 && !loading && <EmptyState text={t.emptyLogs} />}
        {items.map((item) => (
          <ListCard key={item.id}>
            <Box sx={{ minWidth: 0 }}>
              <TitleRow label={item.status} title={item.task_type} />
              <Typography variant="body2" color="text.secondary">
                ID: {item.id}{item.user_id ? ` · User: ${item.user_id}` : ""}{item.import_job_id ? ` · ${t.importJob}: ${item.import_job_id}` : ""}
              </Typography>
              <ActionRow>
                <LinkButton onClick={() => onOpenTaskLog(item.id)}>{t.openTaskLog}</LinkButton>
                {item.user_id && <LinkButton onClick={() => onOpenUser(item.user_id)}>{t.openUser}</LinkButton>}
                {item.import_job_id && <LinkButton onClick={() => onOpenImportJob(item.import_job_id)}>{t.openImportJob}</LinkButton>}
              </ActionRow>
              <InlineDetailGrid>
                <InlineDetailBlock title={t.description}>
                  {item.description ? <PreLine>{item.description}</PreLine> : <Typography color="text.secondary">-</Typography>}
                </InlineDetailBlock>
                <InlineDetailBlock title={t.context}>
                  <LogField label="User" value={item.user_id} />
                  <LogField label={t.importJob} value={item.import_job_id} />
                </InlineDetailBlock>
                <InlineDetailBlock title={t.errorText || "Error"}>
                  {item.error_text ? <Alert severity="error" sx={{ whiteSpace: "pre-line" }}>{item.error_text}</Alert> : <Typography color="text.secondary">-</Typography>}
                </InlineDetailBlock>
              </InlineDetailGrid>
              <EntityLinksFromJson
                value={item.result_json}
                t={t}
                user={user}
                taskType={item.task_type}
                onOpenImportJob={onOpenImportJob}
                onOpenUser={onOpenUser}
                onOpenTaskLog={onOpenTaskLog}
              />
            </Box>
            <SideMeta>
              <LogField layout="inline" label={t.source} value={[item.source_type, item.source_identifier].filter(Boolean).join(" · ")} />
              <LogField layout="inline" label={t.started} value={item.started} />
              <LogField layout="inline" label={t.finished} value={item.finished} />
              <LogField layout="inline" label={t.date} value={item.created} />
            </SideMeta>
          </ListCard>
        ))}
        {loading && <LoadingLine text={t.loading} />}
      </Stack>
      <Pager page={params.page} pageSize={params.pageSize} total={taskLogsQuery.data?.total || 0} onPageChange={(page) => updateParams({ page })} onPageSizeChange={(pageSize) => updateParams({ pageSize, page: 1 })} />
    </CrudPage>
  );
}

export function TaskLogDetailPage({ t, user, taskLogId, onBack, onOpenImportJob, onOpenUser, onOpenTaskLog }) {
  const detailQuery = useQuery({
    queryKey: logsQueryKeys.taskLogDetail(taskLogId),
    queryFn: () => fetchTaskLogDetail(taskLogId),
    enabled: Boolean(taskLogId),
  });

  if (!taskLogId) return <Placeholder title={t.taskLogDetail} description={t.sectionScaffold} />;

  const data = detailQuery.data;
  const task = data?.task_log || {};

  return (
    <CrudPage
      title={`${t.taskLogDetail} #${taskLogId}`}
      breadcrumbs={[{ title: "CronoLex", path: "/admin" }, { title: t.taskLogs, path: "/admin/task-logs" }, { title: t.taskLogDetail }]}
      actions={<Button variant="outlined" onClick={onBack}>{t.taskLogs}</Button>}
    >
      <Typography variant="body2" color="text.secondary">{task.task_type || "-"}</Typography>
      {detailQuery.error && <Alert severity="error">{detailQuery.error.message || t.loadError}</Alert>}
      {detailQuery.isFetching && <LoadingLine text={t.loading} />}
      {data && (
        <>
          <DetailGrid>
            <DetailPanel title={t.taskLogDetail}>
              <LogField label="ID" value={task.id} />
              <LogField label={t.taskType} value={task.task_type} />
              <LogField label={t.status} value={task.status} />
            </DetailPanel>
            <DetailPanel title={t.context}>
              <LogField label="User" value={task.user_id} />
              {task.user_id && <LinkButton onClick={() => onOpenUser(task.user_id)}>{t.openUser}</LinkButton>}
              <LogField label={t.importJob} value={task.import_job_id} />
              {task.import_job_id && <LinkButton onClick={() => onOpenImportJob(task.import_job_id)}>{t.openImportJob}</LinkButton>}
            </DetailPanel>
            <DetailPanel title={t.source}>
              <LogField label={t.source} value={[task.source_type, task.source_identifier].filter(Boolean).join(" · ")} />
              <LogField label={t.started} value={task.started} />
              <LogField label={t.finished} value={task.finished} />
              <LogField label={t.date} value={task.created} />
            </DetailPanel>
          </DetailGrid>
          <DetailGrid>
            <DetailPanel title={t.description}>
              {task.description ? <PreLine>{task.description}</PreLine> : <Typography color="text.secondary">-</Typography>}
            </DetailPanel>
            <DetailPanel title={t.errorText || "Error"}>
              {task.error_text ? <Alert severity="error" sx={{ whiteSpace: "pre-line" }}>{task.error_text}</Alert> : <Typography color="text.secondary">-</Typography>}
            </DetailPanel>
            <DetailPanel title={t.resultJson}>
              <EntityLinksFromJson
                value={task.result_json}
                t={t}
                user={user}
                taskType={task.task_type}
                onOpenImportJob={onOpenImportJob}
                onOpenUser={onOpenUser}
                onOpenTaskLog={onOpenTaskLog}
              />
            </DetailPanel>
          </DetailGrid>
          <JsonPreview title={t.resultJson} value={task.result_json} />
        </>
      )}
    </CrudPage>
  );
}

export function ErrorLogPage({ t, user, onOpenImportJob, onOpenUser, onOpenTaskLog }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const params = useMemo(() => errorLogsParamsFromSearch(searchParams), [searchParams]);
  const filtersQuery = useQuery({
    queryKey: logsQueryKeys.errorLogFilters(),
    queryFn: fetchErrorLogFilters,
  });
  const errorLogsQuery = useQuery({
    queryKey: logsQueryKeys.errorLogList(params),
    queryFn: () => fetchErrorLogs(params),
  });
  const filters = filtersQuery.data || null;
  const items = errorLogsQuery.data?.items || [];
  const error = errorLogsQuery.error?.message || "";
  const loading = errorLogsQuery.isFetching;

  function updateParams(updates) {
    setSearchParams((current) => applyErrorLogsParamUpdates(current, updates));
  }

  return (
    <CrudPage
      title={t.errorLog}
      breadcrumbs={[{ title: "CronoLex", path: "/admin" }, { title: t.logs }, { title: t.errorLog }]}
    >
      <FilterBar>
        <LogToolbar
          t={t}
          search={params.search}
          onSearch={(value) => updateParams({ search: value, page: 1 })}
        />
        <MultiSelect label={t.level} options={filters?.filters?.find((item) => item.name === "level")?.options || []} value={params.levels} onChange={(levels) => updateParams({ levels, page: 1 })} />
      </FilterBar>
      {error && <Alert severity="error">{error}</Alert>}
      <Stack spacing={1.5}>
        {!error && items.length === 0 && !loading && <EmptyState text={t.emptyLogs} />}
        {items.map((item) => (
          <ListCard key={item.id}>
            <Box sx={{ minWidth: 0 }}>
              <TitleRow label={item.level} title={`ID: ${item.id}`} />
              <InlineDetailGrid>
                <InlineDetailBlock title={t.description}>
                  <ErrorLogText text={item.text} t={t} />
                </InlineDetailBlock>
                <InlineDetailBlock title={t.context}>
                  <EntityLinksFromJson
                    value={item.context_json}
                    t={t}
                    user={user}
                    onOpenImportJob={onOpenImportJob}
                    onOpenUser={onOpenUser}
                    onOpenTaskLog={onOpenTaskLog}
                  />
                </InlineDetailBlock>
                <InlineDetailBlock title={t.level}>
                  <LogField label={t.level} value={item.level} />
                  <LogField label={t.date} value={item.created} />
                </InlineDetailBlock>
              </InlineDetailGrid>
            </Box>
            <SideMeta>
              <LogField layout="inline" label={t.level} value={item.level} />
              <LogField layout="inline" label={t.date} value={item.created} />
            </SideMeta>
          </ListCard>
        ))}
        {loading && <LoadingLine text={t.loading} />}
      </Stack>
      <Pager page={params.page} pageSize={params.pageSize} total={errorLogsQuery.data?.total || 0} onPageChange={(page) => updateParams({ page })} onPageSizeChange={(pageSize) => updateParams({ pageSize, page: 1 })} />
    </CrudPage>
  );
}

function ErrorLogText({ text, t }) {
  const [expanded, setExpanded] = useState(false);
  const value = text || "-";
  const hasOverflow = value.length > 220 || value.split("\n").length > 3;

  return (
    <Box sx={{ mt: 1 }}>
      <Typography
        variant="body2"
        sx={{
          whiteSpace: "pre-line",
          overflowWrap: "anywhere",
          overflow: expanded ? "visible" : "hidden",
          display: expanded ? "block" : "-webkit-box",
          WebkitBoxOrient: "vertical",
          WebkitLineClamp: expanded ? "unset" : 3,
        }}
      >
        {value}
      </Typography>
      {hasOverflow && (
        <Button
          size="small"
          variant="text"
          onClick={() => setExpanded((current) => !current)}
          sx={{ mt: 0.75, px: 0 }}
        >
          {expanded ? (t.hideDetails || "Сховати") : (t.showDetails || "Показати повністю")}
        </Button>
      )}
    </Box>
  );
}
