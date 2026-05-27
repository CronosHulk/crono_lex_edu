import React, { Suspense, lazy, useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Navigate, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Box } from "@mui/material";
import { useQueryClient } from "@tanstack/react-query";
import "@fontsource/roboto/400.css";
import "@fontsource/roboto/500.css";
import "@fontsource/roboto-mono/400.css";
import "@fontsource/roboto-mono/500.css";
import { adminApi as api, SESSION_INVALIDATED_EVENT } from "./api/adminApi";
import { useSaveAdminSettings } from "./features/settings/api/settingsApi";
import {
  activeFromPath,
  billingPathFromLegacySearch,
  importJobIdFromPath,
  loginHistoryUserIdFromPath,
  pathForAdminRoute,
  readMagicRequest,
  taskLogIdFromPath,
  userIdFromPath,
} from "./app/routes";
import { AppProviders, useThemeMode } from "./app/AppProviders";
import { AdminShell } from "./shared/shell/AdminShell";
import "./styles.css";

import { i18n } from "./i18n/translations";

const LoginPage = lazyNamed(() => import("./features/auth/AuthPages"), "LoginPage");
const AIUsagePage = lazyNamed(() => import("./features/aiUsage/AIUsagePage"), "AIUsagePage");
const BillingPage = lazyNamed(() => import("./features/billing/BillingPage"), "BillingPage");
const DashboardPage = lazyNamed(() => import("./features/dashboard/DashboardPage"), "DashboardPage");
const DictionaryEntryEditPage = lazyNamed(() => import("./features/dictionary"), "DictionaryEntryEditPage");
const DictionaryPage = lazyNamed(() => import("./features/dictionary"), "DictionaryPage");
const ExerciseTextEditorPage = lazyNamed(() => import("./features/exerciseTexts"), "ExerciseTextEditorPage");
const ExerciseTextsPage = lazyNamed(() => import("./features/exerciseTexts"), "ExerciseTextsPage");
const LoginHistoryPage = lazyNamed(() => import("./features/users"), "LoginHistoryPage");
const UserDetailPage = lazyNamed(() => import("./features/users"), "UserDetailPage");
const UsersPage = lazyNamed(() => import("./features/users"), "UsersPage");
const ImportJobDetailPage = lazyNamed(() => import("./features/imports/ImportPages"), "ImportJobDetailPage");
const ImportItemsPage = lazyNamed(() => import("./features/imports/ImportPages"), "ImportItemsPage");
const ImportJobsPage = lazyNamed(() => import("./features/imports/ImportPages"), "ImportJobsPage");
const ErrorLogPage = lazyNamed(() => import("./features/logs/LogPages"), "ErrorLogPage");
const SettingsPage = lazyNamed(() => import("./features/settings/SettingsPage"), "SettingsPage");
const TaskLogDetailPage = lazyNamed(() => import("./features/logs/LogPages"), "TaskLogDetailPage");
const TaskLogsPage = lazyNamed(() => import("./features/logs/LogPages"), "TaskLogsPage");
const UserDictionaryEntryDetailPage = lazyNamed(() => import("./features/userDictionary/UserDictionaryPage"), "UserDictionaryEntryDetailPage");
const UserDictionaryPage = lazyNamed(() => import("./features/userDictionary/UserDictionaryPage"), "UserDictionaryPage");

function lazyNamed(loader, exportName) {
  return lazy(() => loader().then((module) => ({ default: module[exportName] })));
}

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [user, setUser] = useState(null);
  const [bootstrap, setBootstrap] = useState(null);
  const [locale, setLocale] = useState("uk");
  const [loading, setLoading] = useState(true);
  const [importJobBackTarget, setImportJobBackTarget] = useState("import_jobs");
  const [taskLogBackTarget, setTaskLogBackTarget] = useState("task_logs");
  const [sessionNotice, setSessionNotice] = useState("");
  const { mode, toggleMode } = useThemeMode();
  const saveSettings = useSaveAdminSettings();

  const routePath = location.pathname + location.search + location.hash;
  const active = activeFromPath(routePath);
  const importJobId = importJobIdFromPath(routePath);
  const loginHistoryUserId = loginHistoryUserIdFromPath(routePath);
  const userDetailId = userIdFromPath(routePath);
  const taskLogDetailId = taskLogIdFromPath(routePath);
  const t = i18n[locale] || i18n.uk;

  const navigateTo = useCallback((nextActive, context = {}, options = {}) => {
    const path = pathForAdminRoute(nextActive, context);
    if (location.pathname + location.search + location.hash === path) return;
    navigate(path, { replace: Boolean(options.replace) });
  }, [location.hash, location.pathname, location.search, navigate]);

  const applySettingsResult = useCallback((data) => {
    if (data?.user) {
      setUser(data.user);
      setLocale(data.user.interface_locale || "uk");
    }
    if (data?.settings?.app_version) {
      setBootstrap((current) => ({ ...(current || {}), version: data.settings.app_version }));
    }
  }, []);

  useEffect(() => {
    function onSessionInvalidated() {
      setUser(null);
      setBootstrap(null);
      queryClient.clear();
      setSessionNotice(t.sessionExpired || t.sessionChanged);
      navigate("/admin", { replace: true });
    }
    window.addEventListener(SESSION_INVALIDATED_EVENT, onSessionInvalidated);
    return () => window.removeEventListener(SESSION_INVALIDATED_EVENT, onSessionInvalidated);
  }, [navigate, queryClient, t.sessionChanged, t.sessionExpired]);

  useEffect(() => {
    const magicRequest = readMagicRequest();
    if (magicRequest) {
      api("/auth/magic", { method: "POST", body: JSON.stringify({ token: magicRequest.token }) })
        .then(async (data) => {
          await onAuthed(data);
          const targetPath = data.target_path || magicRequest.next;
          navigate(targetPath.startsWith("/admin") ? targetPath : "/admin", { replace: true });
        })
        .catch(() => {
          setSessionNotice(t.magicLoginFailed);
          navigate("/admin", { replace: true });
        })
        .finally(() => setLoading(false));
      return;
    }
    api("/auth/me")
      .then((data) => {
        setUser(data.user);
        setLocale(data.user.interface_locale || "uk");
        return api("/app/bootstrap");
      })
      .then(setBootstrap)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [navigate, t.magicLoginFailed]);

  useEffect(() => {
    if (!user?.requires_password_setup) return;
    if (location.pathname === "/admin/settings/password") return;
    navigate("/admin/settings/password", { replace: true });
  }, [location.pathname, navigate, user?.requires_password_setup]);

  async function onAuthed(data) {
    setUser(data.user);
    setLocale(data.user.interface_locale || "uk");
    setSessionNotice("");
    setBootstrap(await api("/app/bootstrap"));
  }

  async function logout() {
    await api("/auth/logout", { method: "POST", body: "{}" });
    setUser(null);
    setBootstrap(null);
  }

  function updateUser(nextUser) {
    setUser(nextUser);
    if (nextUser?.interface_locale) {
      setLocale(nextUser.interface_locale);
    }
  }

  function handleLocaleChange(nextLocale) {
    if (nextLocale === locale || saveSettings.isPending) return;
    saveSettings.mutate(
      { interface_locale: nextLocale },
      { onSuccess: applySettingsResult },
    );
  }

  function openImportJobDetail(jobId, backTarget = active === "import_job_detail" ? "import_jobs" : active) {
    setImportJobBackTarget(backTarget || "import_jobs");
    navigateTo("import_job_detail", { importJobId: jobId });
  }

  function openUserDetail(userId) {
    navigateTo("user_detail", { userId });
  }

  function openTaskLogDetail(taskLogId, backTarget = active === "task_log_detail" ? "task_logs" : active) {
    setTaskLogBackTarget(backTarget || "task_logs");
    navigateTo("task_log_detail", { taskLogId });
  }

  function openUserDictionaryEntry(entryId) {
    navigateTo("user_dictionary_detail", { userDictionaryEntryId: entryId });
  }

  function openErrorLogSearch(search) {
    const query = new URLSearchParams();
    if (search) query.set("search", search);
    navigate(`/admin/error-log${query.toString() ? `?${query.toString()}` : ""}`);
  }

  const pageFallback = <Box className="loading">{t.loading}</Box>;

  if (loading) return <Box className="boot">CronoLex</Box>;
  if (!user) {
    return (
      <Suspense fallback={pageFallback}>
        <LoginPage t={t} notice={sessionNotice} onAuthed={onAuthed} />
      </Suspense>
    );
  }
  const version = bootstrap?.version || "0.0.5";
  const currentUser = { ...user, acl_capabilities: bootstrap?.acl?.capabilities || [] };

  return (
    <AdminShell
      user={currentUser}
      active={active}
      title={formatActiveTitle(active, t)}
      version={version}
      locale={locale}
      localePending={saveSettings.isPending}
      mode={mode}
      t={t}
      onToggleMode={toggleMode}
      onLocaleChange={handleLocaleChange}
      onLogout={logout}
    >
      <Suspense fallback={pageFallback}>
        <Routes>
          <Route path="/admin" element={<DictionaryPage t={t} user={currentUser} />} />
          <Route path="/admin/dictionary/:entryId/edit" element={<DictionaryEntryEditRoute t={t} />} />
          <Route path="/admin/exercise-texts" element={<ExerciseTextsPage t={t} />} />
          <Route path="/admin/exercise-texts/new" element={<ExerciseTextEditorRoute t={t} />} />
          <Route path="/admin/exercise-texts/:exerciseTextId" element={<ExerciseTextEditorRoute t={t} />} />
          <Route path="/admin/dashboard" element={<DashboardPage t={t} />} />
          <Route path="/admin/settings" element={<SettingsPage section="profile" t={t} user={currentUser} appVersion={version} onSettingsUpdate={applySettingsResult} onUserUpdate={updateUser} />} />
          <Route path="/admin/settings/analytics" element={<SettingsPage section="analytics" t={t} user={currentUser} appVersion={version} onSettingsUpdate={applySettingsResult} onUserUpdate={updateUser} />} />
          <Route path="/admin/settings/providers" element={<SettingsPage section="providers" t={t} user={currentUser} appVersion={version} onSettingsUpdate={applySettingsResult} onUserUpdate={updateUser} />} />
          <Route path="/admin/settings/import" element={<SettingsPage section="import" t={t} user={currentUser} appVersion={version} onSettingsUpdate={applySettingsResult} onUserUpdate={updateUser} />} />
          <Route path="/admin/settings/plans" element={<SettingsPage section="plans" t={t} user={currentUser} appVersion={version} onSettingsUpdate={applySettingsResult} onUserUpdate={updateUser} />} />
          <Route path="/admin/settings/password" element={<SettingsPage section="password" t={t} user={currentUser} appVersion={version} onSettingsUpdate={applySettingsResult} onUserUpdate={updateUser} />} />
          <Route path="/admin/users" element={<UsersPage t={t} user={currentUser} onOpenUser={openUserDetail} onOpenFullLoginHistory={(userId) => navigateTo("login_history", { userId })} />} />
          <Route path="/admin/users/:userId" element={<UserDetailRoute t={t} user={currentUser} onBack={() => navigateTo("users")} onOpenTaskLog={openTaskLogDetail} onOpenFullLoginHistory={(userId) => navigateTo("login_history", { userId })} />} />
          <Route path="/admin/users/:userId/login-history" element={<LoginHistoryRoute t={t} />} />
          <Route path="/admin/import-jobs" element={<ImportJobsPage t={t} onOpenImportJob={(jobId) => openImportJobDetail(jobId, "import_jobs")} onOpenUser={openUserDetail} onOpenTaskLog={openTaskLogDetail} />} />
          <Route path="/admin/import-items" element={<ImportItemsPage t={t} onOpenImportJob={(jobId) => openImportJobDetail(jobId, "import_items")} onOpenUser={openUserDetail} onOpenTaskLog={openTaskLogDetail} />} />
          <Route path="/admin/user-dictionary" element={<UserDictionaryPage t={t} onOpenEntry={openUserDictionaryEntry} />} />
          <Route path="/admin/user-dictionary/entries/:entryId" element={<UserDictionaryEntryDetailRoute t={t} onBack={() => navigateTo("user_dictionary")} onOpenErrorLogSearch={openErrorLogSearch} />} />
          <Route path="/admin/import-jobs/:importJobId" element={<ImportJobDetailRoute t={t} onBack={() => { const target = importJobBackTarget || "import_jobs"; navigateTo(target, { importJobId, taskLogId: taskLogDetailId, userId: userDetailId || loginHistoryUserId }); }} onOpenUser={openUserDetail} onOpenTaskLog={openTaskLogDetail} />} />
          <Route path="/admin/task-logs" element={<TaskLogsPage t={t} user={currentUser} onOpenImportJob={openImportJobDetail} onOpenUser={openUserDetail} onOpenTaskLog={openTaskLogDetail} />} />
          <Route path="/admin/task-logs/:taskLogId" element={<TaskLogDetailRoute t={t} user={currentUser} onBack={() => { if (taskLogBackTarget === "billing_task_logs") navigate(pathForAdminRoute("billing_task_logs")); else navigateTo("task_logs"); }} onOpenImportJob={(jobId) => openImportJobDetail(jobId, "task_logs")} onOpenUser={openUserDetail} onOpenTaskLog={openTaskLogDetail} />} />
          <Route path="/admin/ai-usage" element={<AIUsagePage t={t} user={currentUser} />} />
          <Route path="/admin/billing" element={<BillingLegacyRedirect />} />
          <Route path="/admin/billing/payments" element={<BillingPage section="payments" t={t} user={currentUser} onOpenUser={openUserDetail} onOpenTaskLog={(taskLogId) => openTaskLogDetail(taskLogId, "billing_task_logs")} onSettingsUpdate={applySettingsResult} />} />
          <Route path="/admin/billing/monobank-audit" element={<BillingPage section="monobank_audit" t={t} user={currentUser} onOpenUser={openUserDetail} onOpenTaskLog={(taskLogId) => openTaskLogDetail(taskLogId, "billing_task_logs")} onSettingsUpdate={applySettingsResult} />} />
          <Route path="/admin/billing/task-logs" element={<BillingPage section="task_logs" t={t} user={currentUser} onOpenUser={openUserDetail} onOpenTaskLog={(taskLogId) => openTaskLogDetail(taskLogId, "billing_task_logs")} onSettingsUpdate={applySettingsResult} />} />
          <Route path="/admin/billing/settings" element={<BillingPage section="settings" t={t} user={currentUser} onOpenUser={openUserDetail} onOpenTaskLog={(taskLogId) => openTaskLogDetail(taskLogId, "billing_task_logs")} onSettingsUpdate={applySettingsResult} />} />
          <Route path="/admin/error-log" element={<ErrorLogPage t={t} user={currentUser} onOpenImportJob={(jobId) => openImportJobDetail(jobId, "error_log")} onOpenUser={openUserDetail} onOpenTaskLog={openTaskLogDetail} />} />
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Routes>
      </Suspense>
    </AdminShell>
  );
}

function formatActiveTitle(active, t) {
  if (active === "dictionary") return t.dictionary;
  if (active === "dictionary_edit") return t.editEntry || t.dictionary;
  if (active === "exercise_texts") return t.exerciseTexts || "Texts for exercises";
  if (active === "users") return t.users;
  if (active === "user_detail") return t.userDetail;
  if (active === "import_jobs") return t.importJobs;
  if (active === "import_items") return t.importItems;
  if (active === "user_dictionary") return t.userDictionary || "User words";
  if (active === "user_dictionary_detail") return t.userDictionaryEntryDetail || "User word details";
  if (active === "import_job_detail") return t.importJobDetail;
  if (active === "login_history") return t.loginHistory;
  if (active === "task_logs") return t.taskLogs;
  if (active === "ai_usage") return t.aiUsage || "AI Usage";
  if (active === "billing" || active.startsWith("billing_")) return t.billing || "Billing";
  if (active === "task_log_detail") return t.taskLogDetail;
  if (active === "error_log") return t.errorLog;
  if (active === "dashboard") return t.dashboard;
  if (active === "settings" || active === "settings_profile") return t.profile;
  if (active === "settings_analytics") return t.analyticsSettings || "Analytics";
  if (active === "settings_providers") return t.providerSettings || "Providers";
  if (active === "settings_import") return t.importSettings || "Import";
  if (active === "settings_plans") return t.planLimitsSettings || "Plan limits";
  if (active === "settings_password") return t.password;
  return active;
}

function DictionaryEntryEditRoute({ t }) {
  const entryId = numericParam(useParams().entryId);
  const location = useLocation();
  const navigate = useNavigate();
  if (!entryId) return <Navigate to="/admin" replace />;

  const backTo = typeof location.state?.backTo === "string" ? location.state.backTo : "/admin";
  return <DictionaryEntryEditPage t={t} entryId={entryId} onBack={() => navigate(backTo)} />;
}

function ExerciseTextEditorRoute({ t }) {
  const rawId = useParams().exerciseTextId;
  const exerciseTextId = rawId === undefined ? null : numericParam(rawId);
  if (rawId !== undefined && !exerciseTextId) return <Navigate to="/admin/exercise-texts" replace />;
  return <ExerciseTextEditorPage t={t} exerciseTextId={exerciseTextId} />;
}

function UserDictionaryEntryDetailRoute({ t, onBack, onOpenErrorLogSearch }) {
  const entryId = numericParam(useParams().entryId);
  if (!entryId) return <Navigate to="/admin/user-dictionary" replace />;
  return <UserDictionaryEntryDetailPage t={t} entryId={entryId} onBack={onBack} onOpenErrorLogSearch={onOpenErrorLogSearch} />;
}

function UserDetailRoute({ t, user, onBack, onOpenTaskLog, onOpenFullLoginHistory }) {
  const userId = stringParam(useParams().userId);
  if (!userId) return <Navigate to="/admin/users" replace />;

  return <UserDetailPage t={t} user={user} userId={userId} onBack={onBack} onOpenTaskLog={onOpenTaskLog} onOpenFullLoginHistory={onOpenFullLoginHistory} />;
}

function LoginHistoryRoute({ t }) {
  const userId = stringParam(useParams().userId);
  if (!userId) return <Navigate to="/admin/users" replace />;

  return <LoginHistoryPage t={t} userId={userId} />;
}

function ImportJobDetailRoute({ t, onBack, onOpenUser, onOpenTaskLog }) {
  const importJobId = numericParam(useParams().importJobId);
  if (!importJobId) return <Navigate to="/admin/import-jobs" replace />;

  return (
    <ImportJobDetailPage
      t={t}
      importJobId={importJobId}
      onBack={onBack}
      onOpenUser={onOpenUser}
      onOpenTaskLog={onOpenTaskLog}
    />
  );
}

function TaskLogDetailRoute({ t, user, onBack, onOpenImportJob, onOpenUser, onOpenTaskLog }) {
  const taskLogId = numericParam(useParams().taskLogId);
  if (!taskLogId) return <Navigate to="/admin/task-logs" replace />;

  return (
    <TaskLogDetailPage
      t={t}
      user={user}
      taskLogId={taskLogId}
      onBack={onBack}
      onOpenImportJob={onOpenImportJob}
      onOpenUser={onOpenUser}
      onOpenTaskLog={onOpenTaskLog}
    />
  );
}

function BillingLegacyRedirect() {
  const [searchParams] = useSearchParams();
  return <Navigate to={billingPathFromLegacySearch(searchParams)} replace />;
}

function numericParam(value) {
  const result = Number(value);
  return Number.isInteger(result) && result > 0 ? result : null;
}

function stringParam(value) {
  return typeof value === "string" && value.trim() ? value : null;
}


createRoot(document.getElementById("root")).render(
  <AppProviders>
    <App />
  </AppProviders>
);
