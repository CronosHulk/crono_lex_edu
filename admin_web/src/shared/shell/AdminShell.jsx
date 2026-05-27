import { DashboardShell } from "@cronolex/shared";
import { BookOpen, BrainCircuit, CircleGauge, CreditCard, FileText, ListChecks, Settings, Users } from "lucide-react";
import { Link as RouterLink, useLocation } from "react-router-dom";

import { pathForAdminRoute } from "../../app/routes";
import { canAdminAccess } from "../acl/adminAcl";

export function AdminShell({
  user,
  active,
  title,
  version,
  locale,
  localePending,
  mode,
  t,
  onToggleMode,
  onLocaleChange,
  onLogout,
  children,
}) {
  const location = useLocation();

  return (
    <DashboardShell
      user={user}
      active={active}
      title={title}
      subtitle={`@${user.username || user.user_id} · ${user.acl_group_title}`}
      navItems={adminNavItems(user, t)}
      mode={mode}
      locale={locale}
      brandSubtitle="Admin"
      versionLabel={`v${version}`}
      accountLabel={user.acl_group_title}
      labels={{
        openMenu: t.openMenu,
        closeMenu: t.closeMenu,
        collapseMenu: t.collapseMenu,
        expandMenu: t.expandMenu,
        lightTheme: t.lightTheme,
        darkTheme: t.darkTheme,
        enableLightTheme: t.enableLightTheme,
        enableDarkTheme: t.enableDarkTheme,
        interfaceLanguage: t.interfaceLanguage,
        logout: t.logout,
      }}
      onToggleMode={onToggleMode}
      onLocaleChange={onLocaleChange}
      localePending={localePending}
      onLogout={onLogout}
      collapsible
      LinkComponent={RouterLink}
      locationKey={`${location.pathname}${location.search}${location.hash}`}
    >
      {children}
    </DashboardShell>
  );
}

function adminNavItems(user, t) {
  const items = [
    {
      key: "dashboard",
      label: t.dashboard,
      icon: <CircleGauge />,
      to: pathForAdminRoute("dashboard"),
      visible: canAdminAccess(user, "logs/list_task_logs") || canAdminAccess(user, "users/list"),
    },
    {
      key: "dictionary",
      label: t.dictionary,
      icon: <BookOpen />,
      to: pathForAdminRoute("dictionary"),
      visible: canAdminAccess(user, "dictionary/list_words") || canAdminAccess(user, "exercise_texts/list"),
      children: [
        { key: "dictionary", label: t.baseDictionary || "Base", to: pathForAdminRoute("dictionary") },
        { key: "user_dictionary", label: t.userDictionary || "User words", to: pathForAdminRoute("user_dictionary") },
        canAdminAccess(user, "exercise_texts/list") && { key: "exercise_texts", label: t.exerciseTexts || "Texts for exercises", to: pathForAdminRoute("exercise_texts"), icon: <FileText /> },
      ].filter(Boolean),
    },
    {
      key: "users",
      label: t.users,
      icon: <Users />,
      to: pathForAdminRoute("users"),
      visible: canAdminAccess(user, "users/list"),
    },
    {
      key: "billing",
      label: t.billing || "Billing",
      icon: <CreditCard />,
      to: pathForAdminRoute("billing"),
      visible: canAdminAccess(user, "settings/view"),
      children: [
        { key: "billing_payments", label: t.billingPayments || "Payments", to: pathForAdminRoute("billing_payments") },
        { key: "billing_monobank_audit", label: t.monobankAudit || "Monobank audit", to: pathForAdminRoute("billing_monobank_audit") },
        { key: "billing_task_logs", label: t.billingTaskLogs || "Billing tasks", to: pathForAdminRoute("billing_task_logs") },
        { key: "billing_settings", label: t.billingSettings || "Settings", to: pathForAdminRoute("billing_settings") },
      ],
    },
    {
      key: "logs",
      label: t.logs,
      icon: <ListChecks />,
      to: pathForAdminRoute("task_logs"),
      visible: logsVisible(user),
      children: [
        canAdminAccess(user, "logs/list_task_logs") && { key: "task_logs", label: t.taskLogs, to: pathForAdminRoute("task_logs") },
        canAdminAccess(user, "logs/list_task_logs") && { key: "ai_usage", label: t.aiUsage || "AI Usage", to: pathForAdminRoute("ai_usage"), icon: <BrainCircuit /> },
        canAdminAccess(user, "imports/list_jobs") && { key: "import_jobs", label: t.importJobs, to: pathForAdminRoute("import_jobs") },
        canAdminAccess(user, "imports/list_items") && { key: "import_items", label: t.importItems, to: pathForAdminRoute("import_items") },
        canAdminAccess(user, "logs/list_error_log") && { key: "error_log", label: t.errorLog, to: pathForAdminRoute("error_log") },
      ].filter(Boolean),
    },
    {
      key: "settings",
      label: t.settings,
      icon: <Settings />,
      to: pathForAdminRoute("settings"),
      visible: canAdminAccess(user, "settings/view"),
      children: [
        { key: "settings_profile", label: t.profile, to: pathForAdminRoute("settings_profile") },
        canAdminAccess(user, "acl/manage") && { key: "settings_analytics", label: t.analyticsSettings || "Analytics", to: pathForAdminRoute("settings_analytics") },
        canAdminAccess(user, "acl/manage") && { key: "settings_providers", label: t.providerSettings || "Providers", to: pathForAdminRoute("settings_providers") },
        canAdminAccess(user, "acl/manage") && { key: "settings_import", label: t.importSettings || "Import", to: pathForAdminRoute("settings_import") },
        canAdminAccess(user, "acl/manage") && { key: "settings_plans", label: t.planLimitsSettings || "Plan limits", to: pathForAdminRoute("settings_plans") },
        { key: "settings_password", label: t.password, to: pathForAdminRoute("settings_password") },
      ].filter(Boolean),
    },
  ];

  return items.filter((item) => item.visible);
}

function logsVisible(user) {
  return (
    canAdminAccess(user, "logs/list_task_logs") ||
    canAdminAccess(user, "imports/list_jobs") ||
    canAdminAccess(user, "imports/list_items") ||
    canAdminAccess(user, "logs/list_error_log")
  );
}
