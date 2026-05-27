import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { Alert, Box, Button, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useSearchParams } from "react-router-dom";

import { requestAdminActionOtp } from "../auth/api/actionOtpApi";
import {
  CrudPage,
  DangerousActionOtpDialog,
  DetailGrid,
  InlineDetailBlock,
  InlineDetailGrid,
  DetailPanel,
  EmptyState,
  FilterBar,
  ListCard,
  LoadingLine,
  LogField,
  LogToolbar,
  Pager,
  SideMeta,
  TitleRow,
} from "../../shared/components";
import { filterActionButtonSx } from "../../shared/components/filterControls";
import { aiUsageQueryKeys, deleteAIUsageSessions, fetchAIUsageSessions, fetchAIUsageSummary } from "./api/aiUsageApi";

const PERIODS = ["day", "week", "month", "all"];

export function AIUsagePage({ t, user }) {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteOtp, setDeleteOtp] = useState("");
  const [deleteChallenge, setDeleteChallenge] = useState(null);
  const params = useMemo(() => ({
    page: Number(searchParams.get("page") || 1),
    pageSize: Number(searchParams.get("page_size") || 50),
    period: searchParams.get("period") || "week",
    search: searchParams.get("search") || "",
  }), [searchParams]);
  const summaryQuery = useQuery({
    queryKey: aiUsageQueryKeys.summary(params.period),
    queryFn: () => fetchAIUsageSummary(params.period),
  });
  const sessionsQuery = useQuery({
    queryKey: aiUsageQueryKeys.sessions(params),
    queryFn: () => fetchAIUsageSessions(params),
  });
  const requestDeleteOtp = useMutation({
    mutationFn: () => requestAdminActionOtp({ action_key: "delete_ai_usage_log" }),
    onSuccess: (data) => {
      setDeleteChallenge(data);
      setDeleteOtp("");
      setDeleteDialogOpen(true);
    },
  });
  const deleteSessions = useMutation({
    mutationFn: deleteAIUsageSessions,
    onSuccess: () => {
      setDeleteDialogOpen(false);
      setDeleteOtp("");
      setDeleteChallenge(null);
      queryClient.invalidateQueries({ queryKey: aiUsageQueryKeys.all });
    },
  });

  function updateParams(updates) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      Object.entries(updates).forEach(([key, value]) => {
        if (value === "" || value === null || value === undefined) next.delete(key);
        else next.set(key, String(value));
      });
      return next;
    });
  }

  const summaryItems = summaryQuery.data?.items || [];
  const sessions = sessionsQuery.data?.items || [];
  const totalCost = summaryItems.reduce((sum, item) => sum + Number(item.estimated_cost_usd || 0), 0);
  const canDeleteAIUsageLog = user?.acl_group_title === "super_admin";

  return (
    <CrudPage
      title={t.aiUsage || "AI Usage"}
      breadcrumbs={[{ title: "CronoLex", path: "/admin" }, { title: t.logs }, { title: t.aiUsage || "AI Usage" }]}
    >
      <FilterBar>
        <TextField select label={t.period || "Period"} value={params.period} onChange={(event) => updateParams({ period: event.target.value, page: 1 })} sx={{ minWidth: 160 }}>
          {PERIODS.map((period) => <MenuItem key={period} value={period}>{t[`period_${period}`] || period}</MenuItem>)}
        </TextField>
        <LogToolbar t={t} search={params.search} onSearch={(search) => updateParams({ search, page: 1 })} />
        {canDeleteAIUsageLog && (
          <Button
            color="error"
            variant="outlined"
            startIcon={<Trash2 size={16} />}
            disabled={requestDeleteOtp.isPending || deleteSessions.isPending}
            onClick={() => requestDeleteOtp.mutate()}
            sx={filterActionButtonSx}
          >
            {t.deleteAllAIUsageLog}
          </Button>
        )}
      </FilterBar>
      <Stack spacing={1.5}>
        {deleteSessions.isSuccess && <Alert severity="success">{t.deleteAllAIUsageLogSuccess}</Alert>}
        {requestDeleteOtp.isError && <Alert severity="error">{requestDeleteOtp.error.message || t.actionError}</Alert>}
        <DetailGrid>
          <DetailPanel title={t.aiUsageSummary || "Usage summary"}>
            <LogField label={t.period || "Period"} value={t[`period_${params.period}`] || params.period} />
            <LogField label={t.estimatedCost || "Estimated cost"} value={`$${totalCost.toFixed(6)}`} />
          </DetailPanel>
          <DetailPanel title={t.context}>
            <LogField label="Sessions" value={sessionsQuery.data?.total || 0} />
            <LogField label="Summary rows" value={summaryItems.length} />
          </DetailPanel>
          <DetailPanel title={t.status}>
            <LogField label={t.status} value={summaryQuery.isFetching || sessionsQuery.isFetching ? t.loading : "ready"} />
          </DetailPanel>
        </DetailGrid>
        {summaryItems.map((item) => (
          <ListCard key={`${item.task_scope}-${item.task_key}-${item.provider_key}-${item.model}`}>
            <Box sx={{ minWidth: 0 }}>
              <TitleRow label={item.task_scope} title={`${item.provider_key} / ${item.model}`} />
              <InlineDetailGrid>
                <InlineDetailBlock title={t.context}>
                  <LogField label="Task" value={item.task_key} />
                  <LogField label="Provider" value={item.provider_key} />
                  <LogField label="Model" value={item.model} />
                </InlineDetailBlock>
                <InlineDetailBlock title="Usage">
                  <LogField label="Requests" value={item.request_count} />
                  <LogField label="Tokens" value={item.total_tokens} />
                </InlineDetailBlock>
                <InlineDetailBlock title={t.estimatedCost || "Estimated cost"}>
                  <LogField label="USD" value={`$${Number(item.estimated_cost_usd || 0).toFixed(6)}`} />
                </InlineDetailBlock>
              </InlineDetailGrid>
            </Box>
          </ListCard>
        ))}
        {sessionsQuery.error && <Alert severity="error">{sessionsQuery.error.message || t.loadError}</Alert>}
        {!sessionsQuery.error && sessions.length === 0 && !sessionsQuery.isFetching && <EmptyState text={t.emptyLogs} />}
        {sessions.map((item) => (
          <ListCard key={item.id}>
            <Box sx={{ minWidth: 0 }}>
              <TitleRow label={item.task_scope} title={`${item.provider_key} / ${item.model}`} />
              <Typography variant="body2" color="text.secondary">
                {item.task_key} · User: {item.actor_user_id || "-"}
              </Typography>
              <InlineDetailGrid>
                <InlineDetailBlock title="Usage">
                  <LogField label="Requests" value={item.request_count} />
                  <LogField label="Tokens" value={item.total_tokens} />
                  <LogField label={t.estimatedCost || "Estimated cost"} value={`$${Number(item.estimated_cost_usd || 0).toFixed(6)}`} />
                </InlineDetailBlock>
                <InlineDetailBlock title={t.context}>
                  <LogField label="Actor" value={item.actor_user_id} />
                  <LogField label="Import job" value={item.import_job_id} />
                </InlineDetailBlock>
                <InlineDetailBlock title={t.description}>
                  {item.summary ? <Typography variant="body2">{item.summary}</Typography> : <Typography color="text.secondary">-</Typography>}
                </InlineDetailBlock>
              </InlineDetailGrid>
            </Box>
            <SideMeta>
              <LogField layout="inline" label="Import job" value={item.import_job_id} />
              <LogField layout="inline" label={t.created || "Created"} value={item.created} />
            </SideMeta>
          </ListCard>
        ))}
        {sessionsQuery.isFetching && <LoadingLine text={t.loading} />}
      </Stack>
      <Pager page={params.page} pageSize={params.pageSize} total={sessionsQuery.data?.total || 0} onPageChange={(page) => updateParams({ page })} onPageSizeChange={(pageSize) => updateParams({ pageSize, page: 1 })} />
      <DangerousActionOtpDialog
        t={t}
        open={deleteDialogOpen}
        title={t.deleteAllAIUsageLogConfirmTitle}
        text={t.deleteAllAIUsageLogConfirmText}
        otp={deleteOtp}
        devOtpHint={deleteChallenge?.dev_otp_hint}
        error={deleteSessions.isError ? deleteSessions.error.message || t.actionError : ""}
        pending={deleteSessions.isPending}
        onOtpChange={setDeleteOtp}
        onCancel={() => {
          setDeleteDialogOpen(false);
          setDeleteOtp("");
        }}
        onConfirm={() => {
          if (!deleteChallenge?.challenge_id) return;
          deleteSessions.mutate({ challenge_id: deleteChallenge.challenge_id, otp: deleteOtp });
        }}
      />
    </CrudPage>
  );
}
