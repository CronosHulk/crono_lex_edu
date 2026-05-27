import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Box, Button, Chip, CircularProgress, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { ExternalLink } from "lucide-react";
import { CrudPage, DetailPanel, LogField, Placeholder } from "../../shared/components";
import { canAdminAccess } from "../../shared/acl/adminAcl";
import { fetchUserDetail, updateUserLearningRole, updateUserRole, updateUserSubscription, updateUserSubscriptionTrial, usersQueryKeys } from "./api/usersApi";
import { LoginHistoryList } from "./components/LoginHistoryList";
import { isTrialActive } from "./helpers/trial";
import { formatUserTitle, normalizeLoginHistory } from "./loginHistory";

const SUBSCRIPTION_PLANS = [
  { value: "free", label: "free" },
  { value: "premium", label: "premium" },
  { value: "premium_plus", label: "premium +" },
  { value: "permanent_premium", label: "permanent premium" },
  { value: "teacher_free", label: "teacher free" },
  { value: "teacher_premium", label: "teacher premium" },
];

export function UserDetailPage({ t, user, userId, onBack, onOpenTaskLog, onOpenFullLoginHistory }) {
  const queryClient = useQueryClient();
  const detailQuery = useQuery({
    queryKey: usersQueryKeys.detail(userId),
    queryFn: () => fetchUserDetail(userId),
    enabled: Boolean(userId),
  });
  const invalidateUsers = () => {
    queryClient.invalidateQueries({ queryKey: usersQueryKeys.lists() });
    queryClient.invalidateQueries({ queryKey: usersQueryKeys.detail(userId) });
  };
  const roleMutation = useMutation({ mutationFn: updateUserRole, onSuccess: invalidateUsers });
  const learningRoleMutation = useMutation({ mutationFn: updateUserLearningRole, onSuccess: invalidateUsers });
  const subscriptionMutation = useMutation({ mutationFn: updateUserSubscription, onSuccess: invalidateUsers });
  const trialMutation = useMutation({ mutationFn: updateUserSubscriptionTrial, onSuccess: invalidateUsers });

  if (!userId) return <Placeholder title={t.userDetail} description={t.sectionScaffold} />;

  const data = detailQuery.data;
  const target = data?.user || {};
  const taskLogs = data?.recent_task_logs || [];
  const loginHistory = normalizeLoginHistory({ items: data?.latest_login_history || [] });
  const canUpdateLearningRole = canAdminAccess(user, "users/update_learning_role");
  const canUpdateSubscription = canAdminAccess(user, "users/update_subscription");
  const canUpdateAccessRole =
    canAdminAccess(user, "users/update_role_to_student") ||
    canAdminAccess(user, "users/update_role_to_admin") ||
    canAdminAccess(user, "users/update_role_to_admin_editor");
  const mutationError = roleMutation.error || learningRoleMutation.error || subscriptionMutation.error || trialMutation.error;
  const mutationPending = roleMutation.isPending || learningRoleMutation.isPending || subscriptionMutation.isPending || trialMutation.isPending;

  function changeAccessRole(role) {
    if (!role || role === target.acl_group_title) return;
    roleMutation.mutate({ targetId: userId, role });
  }

  function changeLearningRole(learningRole) {
    if (!learningRole || learningRole === target.learning_role) return;
    learningRoleMutation.mutate({ targetId: userId, learningRole });
  }

  function changeSubscription(planKey) {
    if (!planKey || planKey === target.subscription_plan_key) return;
    subscriptionMutation.mutate({ targetId: userId, planKey });
  }

  function toggleTrial() {
    trialMutation.mutate({ targetId: userId, isTrialEnabled: !isTrialActive(target) });
  }

  return (
    <CrudPage
      title={`${t.userDetail} #${userId}`}
      breadcrumbs={[{ title: "CronoLex", path: "/admin" }, { title: t.users, path: "/admin/users" }, { title: t.userDetail }]}
      actions={<Button variant="outlined" onClick={onBack}>{t.users}</Button>}
    >
      <Typography variant="body2" color="text.secondary">{target.username ? `@${target.username}` : formatUserTitle(target)}</Typography>
      {detailQuery.error && <Alert severity="error">{detailQuery.error.message || t.loadError}</Alert>}
      {mutationError && <Alert severity="error">{mutationError.message || t.loadError}</Alert>}
      {detailQuery.isFetching && (
        <Stack direction="row" spacing={1} alignItems="center" color="text.secondary">
          <CircularProgress size={18} />
          <Typography variant="body2">{t.loading}</Typography>
        </Stack>
      )}
      {data && (
        <>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "repeat(2, minmax(0, 1fr))" }, gap: 2 }}>
            <DetailPanel title={t.users}>
              <LogField layout="inline" label="UUID" value={target.user_id} />
              <LogField layout="inline" label={t.name} value={[target.first_name, target.last_name].filter(Boolean).join(" ")} />
              <LogField layout="inline" label="Username" value={target.username ? `@${target.username}` : ""} />
              {canUpdateAccessRole ? (
                <TextField
                  select
                  size="small"
                  label={t.role}
                  value={target.acl_group_title || "student"}
                  disabled={mutationPending || String(user?.user_id || "") === String(userId)}
                  onChange={(event) => changeAccessRole(event.target.value)}
                  sx={{ maxWidth: 280 }}
                >
                  <MenuItem value="student">{t.userRole || "user"}</MenuItem>
                  <MenuItem value="admin">{t.admin || "admin"}</MenuItem>
                  <MenuItem value="admin_editor">{t.adminEditor || "admin editor"}</MenuItem>
                </TextField>
              ) : (
                <LogField layout="inline" label={t.role} value={target.acl_group_title} />
              )}
              {canUpdateLearningRole ? (
                <TextField
                  select
                  size="small"
                  label={t.learningStatus || "Learning status"}
                  value={target.learning_role || "student"}
                  disabled={mutationPending}
                  onChange={(event) => changeLearningRole(event.target.value)}
                  sx={{ maxWidth: 280 }}
                >
                  <MenuItem value="student">{t.student || "student"}</MenuItem>
                  <MenuItem value="teacher">{t.teacher || "teacher"}</MenuItem>
                </TextField>
              ) : (
                <LogField layout="inline" label={t.learningStatus || "Learning status"} value={target.learning_role || "student"} />
              )}
              {canUpdateSubscription ? (
                <TextField
                  select
                  size="small"
                  label={t.subscription || "Subscription"}
                  value={target.subscription_plan_key || "free"}
                  disabled={mutationPending}
                  onChange={(event) => changeSubscription(event.target.value)}
                  sx={{ maxWidth: 280 }}
                >
                  {SUBSCRIPTION_PLANS.map((plan) => (
                    <MenuItem key={plan.value} value={plan.value}>{plan.label}</MenuItem>
                  ))}
                </TextField>
              ) : (
                <LogField layout="inline" label={t.subscription || "Subscription"} value={target.subscription_plan_key || "-"} />
              )}
              {canUpdateSubscription && (
                <Button
                  size="small"
                  variant="outlined"
                  color={isTrialActive(target) ? "info" : "inherit"}
                  disabled={mutationPending}
                  onClick={toggleTrial}
                  sx={{ alignSelf: "flex-start" }}
                >
                  {isTrialActive(target) ? t.disableTrial || "Disable trial" : t.enableTrial || "Enable trial"}
                </Button>
              )}
              <LogField layout="inline" label={t.trial || "Trial"} value={target.trial_end || "-"} />
              <LogField layout="inline" label={t.accountStatus || "Account status"} value={target.status} />
              <LogField layout="inline" label="Locale" value={target.interface_locale || target.language_code} />
            </DetailPanel>
            <DetailPanel title={t.aiUsage || "AI Usage"}>
              <LogField layout="inline" label="Cost" value={`$${Number(target.ai_usage_summary?.estimated_cost_usd || 0).toFixed(6)}`} />
              <LogField layout="inline" label="Requests" value={target.ai_usage_summary?.request_count || 0} />
              <LogField layout="inline" label="Tokens" value={target.ai_usage_summary?.total_tokens || 0} />
              <LogField layout="inline" label="Sessions" value={target.ai_usage_summary?.session_count || 0} />
            </DetailPanel>
            <DetailPanel title={t.userSettings}>
              <LogField layout="inline" label={t.level} value={target.language_level_title || target.language_level_id} />
              <LogField layout="inline" label="Words/session" value={target.words_per_session} />
              <LogField layout="inline" label="Reminder hour" value={target.daily_reminder_hour} />
              <LogField layout="inline" label="Preferred gender" value={target.preferred_gender} />
              <LogField layout="inline" label="Google Doc" value={target.import_google_doc_id ? "linked" : "-"} />
              <LogField layout="inline" label="Auto sync" value={target.is_import_google_doc_auto_sync_enabled ? "yes" : "no"} />
              <LogField layout="inline" label="Last sync" value={target.import_google_doc_last_synced} />
              {target.import_google_doc_last_error && <Alert severity="error" sx={{ mt: 1 }}>{target.import_google_doc_last_error}</Alert>}
            </DetailPanel>
          </Box>
          <Paper variant="outlined" sx={{ p: 2, borderColor: "divider" }}>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ justifyContent: "space-between", alignItems: { xs: "stretch", sm: "center" }, mb: 1.5 }}>
              <Typography variant="subtitle1">{t.latestLoginHistory}</Typography>
              <Button size="small" variant="outlined" startIcon={<ExternalLink size={16} />} onClick={() => onOpenFullLoginHistory(userId)}>
                {t.fullLoginHistory}
              </Button>
            </Stack>
            <LoginHistoryList t={t} records={loginHistory} loading={false} error="" compact horizontal />
          </Paper>
          <Paper variant="outlined" sx={{ p: 2, borderColor: "divider" }}>
            <Typography variant="subtitle1" sx={{ mb: 1.5 }}>{t.recentTasks}</Typography>
            <Stack spacing={1}>
              {taskLogs.length === 0 && <Typography color="text.secondary">{t.emptyLogs}</Typography>}
              {taskLogs.map((item) => (
                <Paper variant="outlined" key={item.id} sx={{ p: 1.5, borderColor: "divider" }}>
                  <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={2}>
                    <Box>
                      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                        <Chip label={item.status} size="small" variant="outlined" />
                        <Typography variant="subtitle2">{item.task_type}</Typography>
                      </Stack>
                      {item.description && <Typography variant="body2" sx={{ whiteSpace: "pre-line", mt: 1 }}>{item.description}</Typography>}
                    </Box>
                    <Stack spacing={0.5} alignItems={{ xs: "flex-start", md: "flex-end" }}>
                      <LogField layout="inline" label={t.started} value={item.started} />
                      <LogField layout="inline" label={t.finished} value={item.finished} />
                      <Button size="small" variant="outlined" startIcon={<ExternalLink size={16} />} onClick={() => onOpenTaskLog(item.id)}>{t.openTaskLog}</Button>
                    </Stack>
                  </Stack>
                </Paper>
              ))}
            </Stack>
          </Paper>
        </>
      )}
    </CrudPage>
  );
}
