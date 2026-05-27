import { CRONOLEX_CLIENT_WEB_VERSION, DashboardShell } from "@cronolex/shared";
import { Box, Button, IconButton, Tooltip } from "@mui/material";
import { useQueryClient } from "@tanstack/react-query";
import { Copy, Crown, InfinityIcon, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link as RouterLink, useLocation } from "react-router-dom";

import { usePlans } from "../../features/plans/api/plansApi";
import { useSaveSettings, useSettings } from "../../features/settings/api/settingsApi";
import { normalizeLocale, useClientI18n } from "../i18n/clientI18n";
import { ClientFooter } from "./ClientFooter";

export function ClientShell({
  user,
  active,
  title,
  subtitle,
  navItems,
  footerNavItems,
  mode,
  onToggleMode,
  onUserUpdate,
  onLogout,
  children,
}) {
  const queryClient = useQueryClient();
  const plans = usePlans();
  const settings = useSettings();
  const saveSettings = useSaveSettings();
  const activeLocale = normalizeLocale(user?.interface_locale);
  const { t } = useClientI18n();
  const location = useLocation();
  const [referralCopied, setReferralCopied] = useState(false);
  const referralCopiedTimer = useRef(null);
  const teacherReferralUrl = user?.learning_role === "teacher" ? user?.teacher_referral_url : null;
  const referralLabel = referralCopied ? t("teacherReferralCopied") : t("teacherReferralLink");
  const accountBadge = renderPlanBadge(plans.data, t);

  useEffect(() => {
    return () => {
      if (referralCopiedTimer.current) window.clearTimeout(referralCopiedTimer.current);
    };
  }, []);

  const copyTeacherReferral = async () => {
    if (!teacherReferralUrl) return;
    if (!navigator.clipboard?.writeText) return;
    await navigator.clipboard.writeText(teacherReferralUrl);
    setReferralCopied(true);
    if (referralCopiedTimer.current) window.clearTimeout(referralCopiedTimer.current);
    referralCopiedTimer.current = window.setTimeout(() => setReferralCopied(false), 2000);
  };

  const referralAction = teacherReferralUrl ? (
    <>
      <Tooltip title={referralLabel}>
        <IconButton
          type="button"
          onClick={copyTeacherReferral}
          aria-label={referralLabel}
          sx={{ display: { xs: "inline-flex", sm: "none" } }}
        >
          <Copy />
        </IconButton>
      </Tooltip>
      <Button
        type="button"
        onClick={copyTeacherReferral}
        variant="outlined"
        size="small"
        startIcon={<Copy size={17} />}
        sx={{ display: { xs: "none", sm: "inline-flex" }, whiteSpace: "nowrap" }}
      >
        {referralLabel}
      </Button>
    </>
  ) : null;

  return (
    <DashboardShell
      user={user}
      active={active}
      title={title}
      subtitle={subtitle}
      navItems={navItems}
      footerNavItems={footerNavItems}
      mode={mode}
      locale={activeLocale}
      brandSubtitle={t("appSubtitle")}
      versionLabel={`v${settings.data?.app_version || CRONOLEX_CLIENT_WEB_VERSION}`}
      accountLabel={t("personalCabinet")}
      accountBadge={accountBadge}
      labels={{
        openMenu: t("openMenu"),
        closeMenu: t("closeMenu"),
        lightTheme: t("lightTheme"),
        darkTheme: t("darkTheme"),
        enableLightTheme: t("enableLightTheme"),
        enableDarkTheme: t("enableDarkTheme"),
        interfaceLanguage: t("interfaceLanguage"),
        logout: t("logout"),
      }}
      onToggleMode={onToggleMode}
      onLocaleChange={(nextLocale) => {
        saveSettings.mutate(
          { interface_locale: nextLocale },
          {
            onSuccess: (data) => {
              if (data?.user) onUserUpdate?.(data.user);
              queryClient.invalidateQueries({ queryKey: ["learning"] });
            },
          },
        );
      }}
      localePending={saveSettings.isPending}
      onLogout={onLogout}
      headerActions={referralAction}
      footer={<ClientFooter />}
      LinkComponent={RouterLink}
      locationKey={`${location.pathname}${location.search}${location.hash}`}
    >
      {children}
    </DashboardShell>
  );
}

function renderPlanBadge(plansData, t) {
  const currentPlanKey = plansData?.current_plan_key;
  if (currentPlanKey !== "premium" && currentPlanKey !== "premium_plus" && currentPlanKey !== "permanent_premium") return null;
  const planTitle = plansData?.plans?.find((plan) => plan.key === currentPlanKey)?.title || planBadgeTitle(currentPlanKey, t);

  return (
    <Tooltip title={planTitle}>
      <Box
        component="span"
        aria-label={planTitle}
        sx={{
          position: "relative",
          display: "inline-flex",
          alignItems: "center",
          color: "warning.main",
          lineHeight: 0,
        }}
      >
        {currentPlanKey === "permanent_premium" ? <InfinityIcon size={17} /> : <Crown size={16} />}
        {currentPlanKey === "premium_plus" ? (
          <Sparkles size={9} style={{ position: "absolute", right: -6, top: -5 }} />
        ) : null}
      </Box>
    </Tooltip>
  );
}

function planBadgeTitle(planKey, t) {
  if (planKey === "permanent_premium") return "Permanent premium";
  return t("currentPlan");
}
