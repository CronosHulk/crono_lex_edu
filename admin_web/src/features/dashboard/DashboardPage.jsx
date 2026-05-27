import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Box, Button, Stack, TextField, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import { CrudPage, EmptyState, ListCard, LoadingLine, SideMeta, TitleRow } from "../../shared/components";
import { assignTeacherStudent, dashboardQueryKeys, fetchDashboardSummary } from "./api/dashboardApi";

export function DashboardPage({ t }) {
  const queryClient = useQueryClient();
  const [teacherUserId, setTeacherUserId] = useState("");
  const [studentUserId, setStudentUserId] = useState("");
  const summaryQuery = useQuery({
    queryKey: dashboardQueryKeys.summary(),
    queryFn: fetchDashboardSummary,
  });
  const assignmentMutation = useMutation({
    mutationFn: assignTeacherStudent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.summary() });
    },
  });

  const summary = summaryQuery.data || {};
  const users = summary.users || {};
  const dictionary = summary.dictionary || {};
  const teacherAssignments = summary.teacher_assignments || {};
  const aiCosts = summary.ai_costs || {};

  function assignStudent() {
    assignmentMutation.mutate({
      teacherUserId: teacherUserId.trim(),
      studentUserId: studentUserId.trim(),
    });
  }

  return (
    <CrudPage
      title={t.dashboard}
      breadcrumbs={[{ title: "CronoLex", path: "/admin" }, { title: t.dashboard }]}
    >
      {summaryQuery.error && <Alert severity="error">{summaryQuery.error.message || t.loadError}</Alert>}
      {assignmentMutation.isSuccess && <Alert severity="success">{t.saved || "Saved"}</Alert>}
      {assignmentMutation.error && <Alert severity="error">{assignmentMutation.error.message || t.actionError}</Alert>}

      <Stack spacing={1.5}>
        <ListCard>
          <Box>
            <TitleRow label={t.users} title={String(users.total || 0)} />
            <Typography variant="body2" color="text.secondary">
              Students: {users.by_learning_role?.student || 0} · Teachers: {users.by_learning_role?.teacher || 0}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Weekly active free: {users.active_free_weekly || 0}
            </Typography>
          </Box>
          <SideMeta>
            <Typography variant="caption" color="text.secondary">Active links</Typography>
            <Typography variant="body2">{teacherAssignments.active_links || 0}</Typography>
            <Typography variant="caption" color="text.secondary">Unassigned students</Typography>
            <Typography variant="body2">{teacherAssignments.unassigned_active_students || 0}</Typography>
          </SideMeta>
        </ListCard>

        <ListCard>
          <Box>
            <TitleRow label={t.dictionary} title={String(dictionary.core_total || 0)} />
            <Typography variant="body2" color="text.secondary">
              User words: {dictionary.user_total || 0}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Core POS: {formatCounts(dictionary.core_by_part_of_speech)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              User POS: {formatCounts(dictionary.user_by_part_of_speech)}
            </Typography>
          </Box>
        </ListCard>

        <ListCard>
          <Box>
            <TitleRow label="Levels" title={formatCounts(summary.levels)} />
            <Typography variant="body2" color="text.secondary">
              Subscriptions: {summary.subscriptions?.implemented ? "enabled" : "not implemented"}
            </Typography>
          </Box>
        </ListCard>

        <ListCard>
          <Box>
            <TitleRow label="AI" title="Cost" />
            <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap>
              {Object.entries(aiCosts).map(([period, item]) => (
                <Typography key={period} variant="body2" color="text.secondary">
                  {period}: ${Number(item.estimated_cost_usd || 0).toFixed(6)}
                  {" · avg/user "}
                  ${Number(item.average_cost_per_active_user_usd || 0).toFixed(6)}
                  {" · avg/AI user "}
                  ${Number(item.average_cost_per_ai_active_user_usd || 0).toFixed(6)}
                </Typography>
              ))}
            </Stack>
          </Box>
          <Button component={RouterLink} to="/admin/ai-usage" variant="outlined" size="small">
            {t.aiUsage || "AI Usage"}
          </Button>
        </ListCard>

        <ListCard>
          <Box sx={{ width: "100%" }}>
            <TitleRow label="Teacher" title="Assign student" />
            <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ mt: 1 }}>
              <TextField
                label="Teacher UUID"
                value={teacherUserId}
                onChange={(event) => setTeacherUserId(event.target.value)}
                fullWidth
              />
              <TextField
                label="Student UUID"
                value={studentUserId}
                onChange={(event) => setStudentUserId(event.target.value)}
                fullWidth
              />
              <Button
                variant="contained"
                disabled={!teacherUserId.trim() || !studentUserId.trim() || assignmentMutation.isPending}
                onClick={assignStudent}
                sx={{ minWidth: 140 }}
              >
                {assignmentMutation.isPending ? t.saving || "Saving" : t.save || "Save"}
              </Button>
            </Stack>
          </Box>
        </ListCard>

        {summaryQuery.isFetching && <LoadingLine text={t.loading} />}
        {!summaryQuery.isFetching && !summaryQuery.error && !summaryQuery.data && <EmptyState text={t.emptyLogs} />}
      </Stack>
    </CrudPage>
  );
}

function formatCounts(value) {
  const entries = Object.entries(value || {});
  if (entries.length === 0) return "-";
  return entries.map(([key, count]) => `${key}: ${count}`).join(" · ");
}
