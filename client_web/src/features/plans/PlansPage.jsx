import {
  Alert,
  Box,
  CircularProgress,
  Stack,
  Typography,
} from "@mui/material";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useClientI18n } from "../../shared/i18n/clientI18n";
import {
  useBillingOffer,
  useBillingPaymentHistory,
  useBillingPaymentStatus,
  useCreateBillingCheckout,
  usePlans,
  useSelectPlan,
} from "./api/plansApi";
import { CheckPaymentOverlay } from "./components/CheckPaymentOverlay";
import { CheckoutDialog } from "./components/CheckoutDialog";
import { OfferDialog } from "./components/OfferDialog";
import { PaymentHistoryPanel, PaymentStatusPanel, SubscriptionSummary } from "./components/PaymentPanels";
import { PlanCard } from "./components/PlanCard";
import {
  bestPlanPeriod,
  formatCheckoutError,
  isPaymentTerminalMaintenanceTime,
  normalizePlanReturnTo,
} from "./helpers/planPageHelpers";
import { useCheckPaymentReturn } from "./hooks/useCheckPaymentReturn";

export function PlansPage() {
  const { t, intlLocale } = useClientI18n();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const plans = usePlans();
  const selectPlan = useSelectPlan();
  const checkout = useCreateBillingCheckout();
  const [selectedPeriods, setSelectedPeriods] = useState({});
  const [checkoutPlan, setCheckoutPlan] = useState(null);
  const [offerAccepted, setOfferAccepted] = useState(false);
  const [isOfferOpen, setOfferOpen] = useState(false);
  const [isCheckoutRedirecting, setCheckoutRedirecting] = useState(false);
  const [checkoutClock, setCheckoutClock] = useState(() => new Date());
  const returnTo = normalizePlanReturnTo(searchParams.get("return_to"));
  const isCheckPaymentReturn = searchParams.get("check_payment") === "true";
  const initialPaymentId = isCheckPaymentReturn ? Number(searchParams.get("payment_id") || 0) || null : null;
  const [paymentId, setPaymentId] = useState(initialPaymentId);
  const rows = useMemo(() => plans.data?.plans || [], [plans.data]);
  const planColumnCount = Math.min(Math.max(rows.length, 1), 3);
  const billing = useMemo(() => plans.data?.billing || {}, [plans.data]);
  const subscription = plans.data?.subscription || null;
  const periodOptions = useMemo(() => billing.enabled_period_months || [1, 3, 6, 12], [billing]);
  const pollInterval = Number(billing.frontend_poll_interval_seconds || 10);
  const statusQuery = useBillingPaymentStatus(
    paymentId,
    pollInterval,
    Boolean(paymentId),
    !isCheckPaymentReturn,
  );
  const paymentHistory = useBillingPaymentHistory();
  const refetchPlans = plans.refetch;
  const refetchPaymentHistory = paymentHistory.refetch;
  const checkPaymentReturn = useCheckPaymentReturn({
    initialPaymentId,
    isCheckPaymentReturn,
    navigate,
    normalizeReturnTo: normalizePlanReturnTo,
    refetchPaymentHistory,
    refetchPlans,
    returnTo,
    setPaymentId,
    statusQuery,
  });
  const offer = useBillingOffer(Boolean(checkoutPlan));
  const isPaymentMaintenance = isPaymentTerminalMaintenanceTime(
    checkoutClock,
    billing.billing_provider,
  );

  useEffect(() => {
    if (!plans.data) return;
    setSelectedPeriods((current) => {
      const next = { ...current };
      for (const plan of rows) {
        if (plan.key !== "free" && !next[plan.key]) {
          next[plan.key] = bestPlanPeriod(billing, plan, periodOptions);
        }
      }
      return next;
    });
  }, [billing, plans.data, rows, periodOptions]);

  useEffect(() => {
    const payload = statusQuery.data;
    if (!payload?.status?.is_terminal) return;
    if (checkPaymentReturn.overlayOpen) return;
    refetchPlans?.();
    refetchPaymentHistory?.();
    if (!payload.status.is_success) return;
    setCheckoutPlan(null);
    const target = normalizePlanReturnTo(payload.payment?.source_path) || returnTo;
    if (!target) return;
    const timer = window.setTimeout(() => navigate(target, { replace: true }), 1400);
    return () => window.clearTimeout(timer);
  }, [checkPaymentReturn.overlayOpen, navigate, refetchPaymentHistory, refetchPlans, returnTo, statusQuery.data]);

  useEffect(() => {
    if (!checkoutPlan) return undefined;
    setCheckoutClock(new Date());
    const timer = window.setInterval(() => setCheckoutClock(new Date()), 30_000);
    return () => window.clearInterval(timer);
  }, [checkoutPlan]);

  function selectAndReturn(planKey) {
    selectPlan.mutate(planKey, {
      onSuccess: () => {
        if (returnTo) navigate(returnTo, { replace: true });
      },
    });
  }

  function beginCheckout(plan) {
    const defaultPeriod = bestPlanPeriod(billing, plan, periodOptions);
    setSelectedPeriods((current) => ({ ...current, [plan.key]: current[plan.key] || defaultPeriod }));
    setCheckoutPlan(plan);
    setOfferAccepted(false);
  }

  function submitCheckout() {
    const offerTextHash = offer.data?.offer_text_hash;
    if (!checkoutPlan || isPaymentMaintenance || !offerAccepted || !offerTextHash) return;
    setCheckoutRedirecting(true);
    checkout.mutate(
      {
        plan_key: checkoutPlan.key,
        period_months: Number(selectedPeriods[checkoutPlan.key] || periodOptions[0] || 1),
        offer_accepted: true,
        offer_text_hash: offerTextHash,
        source_path: returnTo || null,
      },
      {
        onSuccess: (payload) => {
          const createdPaymentId = Number(payload?.payment?.id || 0);
          if (createdPaymentId) {
            setPaymentId(createdPaymentId);
          }
          if (payload?.checkout?.page_url) {
            window.location.assign(payload.checkout.page_url);
          } else {
            setCheckoutRedirecting(false);
          }
        },
        onError: () => setCheckoutRedirecting(false),
      },
    );
  }

  return (
    <Stack spacing={2.5}>
      <Box>
        <Typography variant="h5" component="h1" fontWeight={800}>{t("updatePlan")}</Typography>
        <Typography variant="body2" color="text.secondary">{t("updatePlanSubtitle")}</Typography>
      </Box>
      <SubscriptionSummary subscription={subscription} t={t} intlLocale={intlLocale} />
      {paymentId ? <PaymentStatusPanel query={statusQuery} t={t} /> : null}
      {plans.isLoading ? (
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", color: "text.secondary" }}>
          <CircularProgress size={18} />
          <Typography variant="body2">{t("loading")}</Typography>
        </Stack>
      ) : null}
      {plans.isError ? <Alert severity="error">{plans.error.message || t("loadError")}</Alert> : null}
      {selectPlan.isError ? <Alert severity="error">{selectPlan.error.message || t("saveError")}</Alert> : null}
      {checkout.isError && !checkoutPlan ? <Alert severity="error">{formatCheckoutError(checkout.error, t)}</Alert> : null}
      {selectPlan.isSuccess ? <Alert severity="success">{t("planUpdated")}</Alert> : null}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: `repeat(${planColumnCount}, minmax(0, 1fr))` },
          gap: 2,
          alignItems: "stretch",
        }}
      >
        {rows.map((plan) => (
          <PlanCard
            key={plan.key}
            plan={plan}
            t={t}
            billing={billing}
            subscription={subscription}
            periodOptions={periodOptions}
            pending={selectPlan.isPending || checkout.isPending}
            onSelect={() => (plan.key === "free" ? selectAndReturn(plan.key) : beginCheckout(plan))}
          />
        ))}
      </Box>
      <PaymentHistoryPanel query={paymentHistory} t={t} intlLocale={intlLocale} />
      <CheckoutDialog
        billing={billing}
        checkout={checkout}
        checkoutPlan={checkoutPlan}
        isPaymentMaintenance={isPaymentMaintenance}
        offer={offer}
        offerAccepted={offerAccepted}
        periodOptions={periodOptions}
        selectedPeriods={selectedPeriods}
        setCheckoutPlan={setCheckoutPlan}
        setOfferAccepted={setOfferAccepted}
        setOfferOpen={setOfferOpen}
        setSelectedPeriods={setSelectedPeriods}
        submitCheckout={submitCheckout}
        t={t}
      />
      <OfferDialog
        open={isOfferOpen}
        offerText={offer.data?.offer_text || ""}
        loading={offer.isLoading}
        t={t}
        onClose={() => setOfferOpen(false)}
        onAccept={() => {
          setOfferAccepted(true);
          setOfferOpen(false);
        }}
      />
      <CheckPaymentOverlay
        open={isCheckoutRedirecting || checkPaymentReturn.overlayOpen}
        phase={isCheckoutRedirecting ? "redirecting" : checkPaymentReturn.phase}
        statusQuery={statusQuery}
        t={t}
      />
    </Stack>
  );
}

export { normalizePlanReturnTo };
