import React, { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import {
  Archive,
  ExternalLink,
  History,
  KeyRound,
  Trash2,
  Unlink,
} from "lucide-react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
  MenuItem,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { CrudPage, CrudTableSurface, FilterBar, LogToolbar, MultiSelect, Pager } from "../../shared/components";
import { canAdminAccess } from "../../shared/acl/adminAcl";
import { dataTableContainerSx } from "../../shared/components/dataTableStyles";
import { filterControlSx } from "../../shared/components/filterControls";
import { dashboardQueryKeys } from "../dashboard/api/dashboardApi";
import {
  archiveUserById,
  deleteUserById,
  fetchUserFilterMetadata,
  fetchUsers,
  resetUserPasswordById,
  unassignTeacherStudent,
  updateUserSubscriptionTrial,
  usersQueryKeys,
} from "./api/usersApi";
import { applyUsersListParamUpdates, usersListParamsFromSearch } from "./helpers/listParams";
import { isTrialActive } from "./helpers/trial";

export function UsersPage({ t, user, onOpenUser, onOpenFullLoginHistory }) {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [resetTarget, setResetTarget] = useState(null);
  const canDelete = canAdminAccess(user, "users/delete");
  const canResetPassword = canAdminAccess(user, "users/reset_password");
  const canArchive = canAdminAccess(user, "users/archive");
  const canUpdateSubscription = canAdminAccess(user, "users/update_subscription");

  const listParams = useMemo(() => usersListParamsFromSearch(searchParams), [searchParams]);
  const filtersQuery = useQuery({
    queryKey: usersQueryKeys.filterMetadata(),
    queryFn: fetchUserFilterMetadata,
  });
  const usersQuery = useQuery({
    queryKey: usersQueryKeys.list(listParams),
    queryFn: () => fetchUsers(listParams),
  });

  const invalidateUsers = () => {
    queryClient.invalidateQueries({ queryKey: usersQueryKeys.lists() });
    queryClient.invalidateQueries({ queryKey: usersQueryKeys.details() });
    queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.all });
  };
  const archiveMutation = useMutation({
    mutationFn: archiveUserById,
    onSuccess: invalidateUsers,
  });
  const deleteMutation = useMutation({
    mutationFn: deleteUserById,
    onSuccess: invalidateUsers,
  });
  const resetPasswordMutation = useMutation({
    mutationFn: resetUserPasswordById,
    onSuccess: () => {
      setResetTarget(null);
      invalidateUsers();
    },
  });
  const unassignTeacherMutation = useMutation({
    mutationFn: unassignTeacherStudent,
    onSuccess: invalidateUsers,
  });
  const trialMutation = useMutation({
    mutationFn: updateUserSubscriptionTrial,
    onSuccess: invalidateUsers,
  });

  const items = usersQuery.data?.items || [];
  const filters = filtersQuery.data || null;
  const loading = usersQuery.isFetching;
  const actionPending = archiveMutation.isPending || deleteMutation.isPending || resetPasswordMutation.isPending || unassignTeacherMutation.isPending || trialMutation.isPending;
  const actionError = archiveMutation.error || deleteMutation.error || resetPasswordMutation.error || unassignTeacherMutation.error || trialMutation.error;

  function updateListParams(updates) {
    setSearchParams((current) => applyUsersListParamUpdates(current, updates));
  }

  function archiveUser(target) {
    archiveMutation.mutate(target.user_id);
  }

  function deleteUser(target) {
    deleteMutation.mutate(target.user_id);
  }

  function resetUserPassword(target) {
    if (!target) return;
    resetPasswordMutation.mutate(target.user_id);
  }

  function unassignStudentFromTeacher(student) {
    if (!student?.user_id) return;
    unassignTeacherMutation.mutate(student.user_id);
  }

  function toggleTrial(target) {
    if (!target?.user_id) return;
    trialMutation.mutate({
      targetId: target.user_id,
      isTrialEnabled: !isTrialActive(target),
    });
  }

  const resetTargetName = resetTarget
    ? [resetTarget.first_name, resetTarget.last_name].filter(Boolean).join(" ") || resetTarget.username || resetTarget.user_id
    : "";

  return (
    <CrudPage
      title={t.users}
      breadcrumbs={[{ title: "CronoLex", path: "/admin" }, { title: t.users }]}
    >
      <Box sx={{ borderBottom: 1, borderColor: "divider", minWidth: { xs: "100%", sm: 360 } }}>
        <Tabs
          value={listParams.userType}
          onChange={(_, userType) => {
            updateListParams({ userType, userId: "", page: 1 });
          }}
          aria-label="user type filter tabs"
          textColor="primary"
          indicatorColor="primary"
        >
          <Tab value="admin" label={t.admin || "Admin"} />
          <Tab value="student" label={t.student || "Student"} />
          <Tab value="teacher" label={t.teacher || "Teacher"} />
        </Tabs>
      </Box>

      <FilterBar>
        <LogToolbar
          t={t}
          search={listParams.search}
          onSearch={(value) => {
            updateListParams({ search: value, page: 1 });
          }}
        />
        <TextField
          select
          label={t.status}
          value={listParams.archived ? "archived" : "active"}
          onChange={(event) => {
            updateListParams({ archived: event.target.value === "archived", page: 1 });
          }}
          sx={filterControlSx}
        >
          <MenuItem value="active">{t.active || "Active"}</MenuItem>
          <MenuItem value="archived">{t.archived}</MenuItem>
        </TextField>
        {listParams.userId && (
          <Chip
            label={`UUID: ${listParams.userId}`}
            onDelete={() => updateListParams({ userId: "", page: 1 })}
            variant="outlined"
          />
        )}
        <MultiSelect label={t.role} options={filters?.filters?.find((item) => item.name === "role")?.options || []} value={listParams.roles} onChange={(roles) => updateListParams({ roles, page: 1 })} />
      </FilterBar>
      {usersQuery.error && <Alert severity="error">{usersQuery.error.message || t.loadError}</Alert>}
      {actionError && <Alert severity="error">{actionError.message || t.loadError}</Alert>}

      <CrudTableSurface sx={dataTableContainerSx}>
        <Table size="small" sx={{ minWidth: 1100 }}>
          <TableHead>
            <TableRow>
              <TableCell>UUID</TableCell>
              <TableCell>{t.name}</TableCell>
              <TableCell>Username</TableCell>
              <TableCell>{t.role}</TableCell>
              <TableCell>{t.subscription || "Subscription"}</TableCell>
              <TableCell>{t.aiUsage || "AI Usage"}</TableCell>
              <TableCell>{t.status}</TableCell>
              <TableCell align="right">{t.actions}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((item) => (
              <React.Fragment key={item.user_id}>
                <TableRow hover>
                  <TableCell>{item.user_id}</TableCell>
                  <TableCell>
                    <Typography variant="subtitle2" component="strong">{[item.first_name, item.last_name].filter(Boolean).join(" ") || "-"}</Typography>
                  </TableCell>
                  <TableCell>{item.username ? `@${item.username}` : "-"}</TableCell>
                  <TableCell><Chip label={item.acl_group_title} size="small" variant="outlined" /></TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
                      <Chip label={item.subscription_plan_key || "-"} size="small" variant="outlined" />
                      {isTrialActive(item) && <Chip label={t.trial || "Trial"} size="small" color="info" variant="outlined" />}
                    </Stack>
                  </TableCell>
                  <TableCell>{formatAiUsageSummary(item.ai_usage_summary)}</TableCell>
                  <TableCell>{item.status}</TableCell>
                  <TableCell align="right" sx={{ minWidth: 420 }}>
                    <Stack direction="row" spacing={1} justifyContent="flex-end" flexWrap="wrap" useFlexGap sx={{ width: "100%" }}>
                      <Button size="small" variant="outlined" startIcon={<History size={16} />} onClick={() => onOpenFullLoginHistory(item.user_id)}>{t.openLoginHistory}</Button>
                      {canUpdateSubscription && (
                        <Button
                          size="small"
                          color={isTrialActive(item) ? "info" : "inherit"}
                          variant="outlined"
                          disabled={actionPending}
                          onClick={() => toggleTrial(item)}
                        >
                          {isTrialActive(item) ? t.disableTrial || "Trial off" : t.enableTrial || "Trial"}
                        </Button>
                      )}
                      {canArchive && !listParams.archived && item.user_id !== user.user_id && (
                        <Button size="small" variant="outlined" startIcon={<Archive size={16} />} disabled={actionPending} onClick={() => archiveUser(item)}>{t.archive}</Button>
                      )}
                      {canResetPassword && item.user_id !== user.user_id && (
                        <Button size="small" color="warning" variant="outlined" startIcon={<KeyRound size={16} />} disabled={actionPending} onClick={() => setResetTarget(item)}>{t.resetPassword}</Button>
                      )}
                      {canDelete && item.user_id !== user.user_id && (
                        <Button size="small" color="error" variant="outlined" startIcon={<Trash2 size={16} />} disabled={actionPending} onClick={() => deleteUser(item)}>{t.delete}</Button>
                      )}
                      <IconButton
                        size="small"
                        title={t.openUser}
                        aria-label={t.openUser}
                        onClick={() => onOpenUser(item.user_id)}
                        sx={userActionIconSx}
                      >
                        <ExternalLink size={18} />
                      </IconButton>
                    </Stack>
                  </TableCell>
                </TableRow>
                {listParams.userType === "teacher" && (
                  <TableRow>
                    <TableCell />
                    <TableCell colSpan={7} sx={{ bgcolor: "action.hover", py: 1.25 }}>
                      <TeacherStudentsList
                        students={item.students || []}
                        t={t}
                        disabled={actionPending}
                        onOpenStudent={(studentId) => updateListParams({ userType: "student", userId: studentId, search: "", roles: [], page: 1 })}
                        onUnassignStudent={unassignStudentFromTeacher}
                      />
                    </TableCell>
                  </TableRow>
                )}
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
        {loading && (
          <Stack alignItems="center" justifyContent="center" spacing={1} sx={{ position: "absolute", inset: 0, minHeight: 160, bgcolor: "rgba(15, 17, 22, 0.68)", backdropFilter: "blur(1px)" }}>
            <CircularProgress size={28} />
            <Typography variant="body2">{t.loading}</Typography>
          </Stack>
        )}
      </CrudTableSurface>
      <Dialog open={Boolean(resetTarget)} onClose={() => setResetTarget(null)} maxWidth="xs" fullWidth>
        <DialogTitle>{t.resetPasswordConfirmTitle}</DialogTitle>
        <DialogContent>
          <DialogContentText>{t.resetPasswordConfirmText}</DialogContentText>
          {resetTarget && (
            <Typography variant="subtitle2" sx={{ mt: 2 }}>
              {resetTargetName}
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetTarget(null)} disabled={resetPasswordMutation.isPending}>{t.close}</Button>
          <Button color="warning" variant="contained" onClick={() => resetUserPassword(resetTarget)} disabled={!resetTarget || resetPasswordMutation.isPending}>
            {resetPasswordMutation.isPending ? t.saving : t.resetPassword}
          </Button>
        </DialogActions>
      </Dialog>
      <Pager page={listParams.page} pageSize={listParams.pageSize} total={usersQuery.data?.total || 0} onPageChange={(page) => updateListParams({ page })} onPageSizeChange={(pageSize) => updateListParams({ pageSize, page: 1 })} />
    </CrudPage>
  );
}

const userActionIconSx = {
  border: 1,
  borderColor: "divider",
  borderRadius: 1,
  width: 34,
  height: 34,
  ml: "auto",
};

function formatAiUsageSummary(summary) {
  const value = Number(summary?.estimated_cost_usd || 0);
  const requests = Number(summary?.request_count || 0);
  if (!value && !requests) return "-";
  return `$${value.toFixed(6)} · ${requests} req`;
}

function TeacherStudentsList({ students, t, disabled, onOpenStudent, onUnassignStudent }) {
  if (!students.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        {t.noStudents || "No students"}
      </Typography>
    );
  }

  return (
    <Stack spacing={0.75}>
      {students.map((student) => (
        <Stack
          key={student.user_id}
          direction={{ xs: "column", md: "row" }}
          spacing={1}
          alignItems={{ xs: "flex-start", md: "center" }}
          justifyContent="space-between"
          sx={{ py: 0.5, borderBottom: 1, borderColor: "divider", "&:last-child": { borderBottom: 0 } }}
        >
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
            <Typography variant="body2" fontWeight={600}>
              {[student.first_name, student.last_name].filter(Boolean).join(" ") || "-"}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {student.username ? `@${student.username}` : "-"}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {student.user_id}
            </Typography>
            <Chip label={student.subscription_plan_key || "-"} size="small" variant="outlined" />
            <Chip label={student.status || "-"} size="small" variant="outlined" />
          </Stack>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button
              size="small"
              variant="outlined"
              startIcon={<ExternalLink size={16} />}
              onClick={() => onOpenStudent(student.user_id)}
            >
              {t.openUser}
            </Button>
            <Button
              size="small"
              color="warning"
              variant="outlined"
              startIcon={<Unlink size={16} />}
              disabled={disabled}
              onClick={() => onUnassignStudent(student)}
            >
              {t.unassignTeacherStudent || "Unassign"}
            </Button>
          </Stack>
        </Stack>
      ))}
    </Stack>
  );
}
