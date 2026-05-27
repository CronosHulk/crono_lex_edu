import { Box, Button, Card, CardContent, Chip, Divider, Stack, Typography } from "@mui/material";
import { Check, Crown, Sparkles } from "lucide-react";

import {
  bestPlanPeriod,
  buildOrderPreview,
  formatAmount,
  hasActivePaidSubscription,
} from "../helpers/planPageHelpers";

const PLAN_ICONS = {
  premium: <Crown size={24} />,
  premium_plus: (
    <Box sx={{ position: "relative", display: "inline-flex" }}>
      <Crown size={24} />
      <Sparkles size={12} style={{ position: "absolute", right: -8, top: -6 }} />
    </Box>
  ),
};

export function PlanCard({ plan, t, billing, subscription, periodOptions, pending, onSelect }) {
  const order = buildOrderPreview(billing, plan, bestPlanPeriod(billing, plan, periodOptions));
  const freeDowngradeBlocked = plan.key === "free" && hasActivePaidSubscription(subscription);
  const isPaidCurrentPlan = plan.is_current && plan.key !== "free";
  const isUnavailable = plan.availability?.can_checkout === false || freeDowngradeBlocked;
  const unavailableReason = freeDowngradeBlocked ? "free_after_current_period" : plan.availability?.reason;
  const isDisabled = (!isPaidCurrentPlan && plan.is_current) || isUnavailable || pending;
  return (
    <Card
      variant="outlined"
      sx={{
        minWidth: 0,
        height: "100%",
        borderColor: plan.key === "premium_plus" ? "primary.main" : "divider",
      }}
    >
      <CardContent sx={{ height: "100%", p: { xs: 2, sm: 2.5 } }}>
        <Stack spacing={2.25} sx={{ height: "100%" }}>
          <Stack direction="row" spacing={1.25} sx={{ alignItems: "flex-start", minHeight: 64 }}>
            <Box sx={{ color: plan.key === "free" ? "text.secondary" : "warning.main", display: "grid", placeItems: "center", pt: 0.5 }}>
              {PLAN_ICONS[plan.key] || <Check size={22} />}
            </Box>
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Typography variant="h6" sx={{ fontWeight: 800 }}>{plan.title}</Typography>
              {plan.is_current ? <Chip sx={{ mt: 1 }} size="small" color="primary" label={t("currentPlan")} /> : null}
            </Box>
          </Stack>
          <Stack
            component="ul"
            divider={<Divider flexItem sx={{ borderColor: "divider", opacity: 0.65 }} />}
            sx={{ pl: 0, m: 0, listStyle: "none", flex: 1 }}
          >
            {(plan.feature_keys || []).map((featureKey) => (
              <Stack key={featureKey} component="li" direction="row" spacing={1.25} sx={{ alignItems: "flex-start", py: 1.35 }}>
                <Check size={17} style={{ marginTop: 2, flex: "0 0 auto" }} />
                <Typography variant="body2">{t(`planFeature_${featureKey}`)}</Typography>
              </Stack>
            ))}
          </Stack>
          {isUnavailable && unavailableReason === "downgrade_after_current_period" ? (
            <Typography variant="caption" color="text.secondary">
              {t("downgradeAfterCurrentPeriod")}
            </Typography>
          ) : null}
          {isUnavailable && unavailableReason === "free_after_current_period" ? (
            <Typography variant="caption" color="text.secondary">
              {t("freeAfterCurrentPeriod")}
            </Typography>
          ) : null}
          <Box sx={{ minHeight: 76, display: "flex", alignItems: "center", justifyContent: "center" }}>
            {order ? <PlanPrice order={order} plan={plan} billing={billing} t={t} /> : null}
          </Box>
          <Button variant={plan.is_current || isUnavailable ? "outlined" : "contained"} disabled={isDisabled} onClick={onSelect} fullWidth>
            {isPaidCurrentPlan ? t("renewPlan") : plan.is_current ? t("currentPlan") : isUnavailable ? t("notAvailable") : t("selectPlan")}
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}

function PlanPrice({ order, plan, billing, t }) {
  if (order.quoteKind === "upgrade") {
    return (
      <Stack spacing={0.25} sx={{ alignItems: "center", textAlign: "center" }}>
        <Typography variant="subtitle1" color="primary.main" sx={{ fontWeight: 800 }}>{t("upgradePayment", { amount: formatAmount(order.amountUah) })}</Typography>
      </Stack>
    );
  }
  const monthlyAmount = order.periodMonths > 0 ? order.amountUah / order.periodMonths : order.amountUah;
  const baseMonthlyAmount = Number(billing?.plan_prices_uah?.[plan.key]?.["1"] || 0);
  const hasDiscount = order.periodMonths > 1 && baseMonthlyAmount > monthlyAmount;
  return (
    <Stack spacing={0.25} sx={{ alignItems: "center", textAlign: "center" }}>
      <Typography variant="subtitle1" color="primary.main" sx={{ fontWeight: 800 }}>
        {t("fromMonthlyPrice", { amount: formatAmount(monthlyAmount) })}
      </Typography>
      {hasDiscount ? (
        <Typography variant="caption" color="text.secondary" sx={{ textDecoration: "line-through" }}>
          {t("monthlyPrice", { amount: formatAmount(baseMonthlyAmount) })}
        </Typography>
      ) : null}
    </Stack>
  );
}
