import React, { Suspense, lazy, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { Box } from "@mui/material";
import { useQueryClient } from "@tanstack/react-query";
import "@fontsource/roboto/400.css";
import "@fontsource/roboto/500.css";
import "@fontsource/roboto-mono/400.css";
import "@fontsource/roboto-mono/500.css";
import { Bell, BookOpen, CreditCard, Gauge, Import, KeyRound, Settings, Users } from "lucide-react";

import { CLIENT_SESSION_INVALIDATED_EVENT, clientApi as api } from "./api/clientApi";
import { AppProviders, useThemeMode } from "./app/AppProviders";
import { installGoogleAnalytics } from "./shared/analytics/googleAnalytics";
import { ClientI18nProvider, useClientI18n } from "./shared/i18n/clientI18n";
import { ClientDashboard, ClientShell } from "./shared/shell";
import "./styles.css";

const LoginPage = lazyNamed(() => import("./features/auth/AuthPages"), "LoginPage");
const LandingPage = lazyNamed(() => import("./features/landing/LandingPage"), "LandingPage");
const LearningPage = lazyNamed(() => import("./features/learning/LearningPage"), "LearningPage");
const DictionarySearchPage = lazyNamed(() => import("./features/learning/DictionarySearchPage"), "DictionarySearchPage");
const ImportWordsPage = lazyNamed(() => import("./features/importWords/ImportWordsPage"), "ImportWordsPage");
const PlansPage = lazyNamed(() => import("./features/plans/PlansPage"), "PlansPage");
const SettingsLearningPage = lazyNamed(() => import("./features/settings/SettingsLearningPage"), "SettingsLearningPage");
const SettingsPasswordPage = lazyNamed(() => import("./features/settings/SettingsPasswordPage"), "SettingsPasswordPage");
const SettingsRemindersPage = lazyNamed(() => import("./features/settings/SettingsRemindersPage"), "SettingsRemindersPage");
const TeacherStudentsPage = lazyNamed(() => import("./features/students/TeacherStudentsPage"), "TeacherStudentsPage");
const TeacherStudentGroupsPage = lazyNamed(() => import("./features/students/TeacherStudentGroupsPage"), "TeacherStudentGroupsPage");

function lazyNamed(loader, exportName) {
  return lazy(() => loader().then((module) => ({ default: module[exportName] })));
}

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const { mode, toggleMode } = useThemeMode();
  const { t } = useClientI18n();
  const pageFallback = <Box className="loading">{t("loading")}</Box>;

  useEffect(() => {
    if (!import.meta.env.PROD) return;
    installGoogleAnalytics();
  }, []);

  useEffect(() => {
    function onSessionInvalidated() {
      setUser(null);
      queryClient.clear();
      setNotice(t("sessionExpired"));
      navigate("/login", { replace: true });
    }
    window.addEventListener(CLIENT_SESSION_INVALIDATED_EVENT, onSessionInvalidated);
    return () => window.removeEventListener(CLIENT_SESSION_INVALIDATED_EVENT, onSessionInvalidated);
  }, [navigate, queryClient, t]);

  useEffect(() => {
    const magic = readMagicRequest(location.search);
    if (magic) {
      api("/auth/magic", { method: "POST", body: JSON.stringify({ token: magic.token }) })
        .then((data) => {
          setUser(data.user);
          navigate(data.target_path || magic.next || "/settings", { replace: true });
        })
        .catch((error) => setNotice(error?.message || t("invalidLoginLink")))
        .finally(() => setLoading(false));
      return;
    }
    api("/auth/me").then((data) => setUser(data.user)).catch(() => {}).finally(() => setLoading(false));
  }, [location.search, navigate, t]);

  useEffect(() => {
    if (!user?.requires_password_setup || location.pathname === "/settings/password") return;
    navigate("/settings/password", { replace: true });
  }, [location.pathname, navigate, user?.requires_password_setup]);

  async function logout() {
    await api("/auth/logout", { method: "POST", body: "{}" });
    setUser(null);
    navigate("/login", { replace: true });
  }

  if (loading) return <Box className="boot">CronoLex</Box>;
  if (!user) {
    return (
      <Suspense fallback={pageFallback}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage notice={notice} onAuthed={(data) => setUser(data.user)} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    );
  }

  return (
    <ClientI18nProvider locale={user.interface_locale}>
      <AuthenticatedClientApp
        user={user}
        mode={mode}
        onToggleMode={toggleMode}
        onUserUpdate={setUser}
        onLogout={logout}
      />
    </ClientI18nProvider>
  );
}

function AuthenticatedClientApp({ user, mode, onToggleMode, onUserUpdate, onLogout }) {
  const location = useLocation();
  const active = activeFromPath(location.pathname);
  const { t } = useClientI18n();
  const pageTitle = titleFromActive(active, t);
  const pageFallback = <Box className="loading">{t("loading")}</Box>;
  const planNavItem = { key: "plans", label: t("updatePlan"), to: "/plans", icon: <CreditCard /> };
  const teacherNavItems = user?.learning_role === "teacher" ? [
    {
      key: "students",
      label: t("navStudents") || "Студенти",
      to: "/students",
      icon: <Users />,
      children: [
        { key: "students", label: t("navStudentList") || "Список студентів", to: "/students" },
        { key: "student_groups", label: t("navStudentGroups") || "Групи студентів", to: "/students/groups" },
      ],
    },
  ] : [];
  const navItems = [
    { key: "dashboard", label: t("navOverview"), to: "/", icon: <Gauge /> },
    ...teacherNavItems,
    {
      key: "learning",
      label: t("navLearning"),
      to: "/learning?tab=training",
      icon: <BookOpen />,
      children: [
        { key: "learning", label: t("navWordLearning"), to: "/learning?tab=training" },
        { key: "dictionary_search", label: t("navDictionarySearch"), to: "/learning/dictionary-search" },
      ],
    },
    { key: "import", label: t("navImportWords"), to: "/import-words", icon: <Import /> },
    {
      key: "settings",
      label: t("navSettings"),
      to: "/settings/learning",
      icon: <Settings />,
      children: [
        { key: "settings_learning", label: t("navLearningSettings"), to: "/settings/learning", icon: <BookOpen /> },
        { key: "settings_reminders", label: t("navReminderSettings"), to: "/settings/reminders", icon: <Bell /> },
        { key: "settings_password", label: t("navPasswordSettings"), to: "/settings/password", icon: <KeyRound /> },
      ],
    },
  ];

  return (
    <ClientShell
      user={user}
      active={active}
      title={pageTitle}
      navItems={navItems}
      footerNavItems={[planNavItem]}
      mode={mode}
      onToggleMode={onToggleMode}
      onUserUpdate={onUserUpdate}
      onLogout={onLogout}
    >
      <Suspense fallback={pageFallback}>
        <Routes>
          <Route path="/" element={<ClientDashboard />} />
          <Route path="/learning" element={<LearningPage />} />
          <Route path="/learning/dictionary-search" element={<DictionarySearchPage />} />
          <Route path="/homework" element={<Navigate to="/learning?tab=training" replace />} />
          <Route path="/import-words" element={<ImportWordsPage />} />
          {user?.learning_role === "teacher" ? <Route path="/students" element={<TeacherStudentsPage />} /> : null}
          {user?.learning_role === "teacher" ? <Route path="/students/groups" element={<TeacherStudentGroupsPage />} /> : null}
          <Route path="/plans" element={<PlansPage />} />
          <Route path="/settings" element={<SettingsIndexRedirect />} />
          <Route path="/settings/learning" element={<SettingsLearningPage />} />
          <Route path="/settings/reminders" element={<SettingsRemindersPage />} />
          <Route path="/settings/password" element={<SettingsPasswordPage user={user} onUserUpdate={onUserUpdate} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </ClientShell>
  );
}

function activeFromPath(path) {
  if (path === "/") return "dashboard";
  if (path.includes("/settings/password")) return "settings_password";
  if (path.includes("/settings/reminders")) return "settings_reminders";
  if (path.includes("/settings")) return "settings_learning";
  if (path.includes("/import-words")) return "import";
  if (path.includes("/students/groups")) return "student_groups";
  if (path.includes("/students")) return "students";
  if (path.includes("/plans")) return "plans";
  if (path.includes("/learning/dictionary-search")) return "dictionary_search";
  return "learning";
}

function titleFromActive(active, t) {
  if (active === "dashboard") return t("navOverview");
  if (active === "settings_password") return t("navPasswordSettings");
  if (active === "settings_reminders") return t("navReminderSettings");
  if (active === "settings_learning") return t("navLearningSettings");
  if (active === "import") return t("navImportWords");
  if (active === "students") return t("navStudentList") || "Список студентів";
  if (active === "student_groups") return t("navStudentGroups") || "Групи студентів";
  if (active === "plans") return t("updatePlan");
  if (active === "dictionary_search") return t("navDictionarySearch");
  return t("navLearning");
}

function SettingsIndexRedirect() {
  const location = useLocation();
  const params = new URLSearchParams(location.search || "");
  if (params.get("section") === "password") return <Navigate to="/settings/password" replace />;
  if (params.get("section") === "reminders") return <Navigate to="/settings/reminders" replace />;
  return <Navigate to="/settings/learning" replace />;
}

function readMagicRequest(search) {
  const params = new URLSearchParams(search || "");
  const token = params.get("token");
  if (!token) return null;
  return { token, next: params.get("next") || "/settings" };
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <AppProviders>
      <ClientI18nProvider locale="uk">
        <App />
      </ClientI18nProvider>
    </AppProviders>
  </React.StrictMode>
);
