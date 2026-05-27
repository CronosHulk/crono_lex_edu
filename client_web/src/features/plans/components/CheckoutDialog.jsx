import {
  Alert,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Typography,
} from "@mui/material";

import {
  bestPlanPeriod,
  buildOrderPreview,
  formatCheckoutError,
  formatOrderSummary,
  formatPeriod,
} from "../helpers/planPageHelpers";

export function CheckoutDialog({
  billing,
  checkout,
  checkoutPlan,
  isPaymentMaintenance,
  offer,
  offerAccepted,
  periodOptions,
  selectedPeriods,
  setCheckoutPlan,
  setOfferAccepted,
  setOfferOpen,
  setSelectedPeriods,
  submitCheckout,
  t,
}) {
  const checkoutOrder = checkoutPlan
    ? buildOrderPreview(billing, checkoutPlan, selectedPeriods[checkoutPlan.key] || bestPlanPeriod(billing, checkoutPlan, periodOptions))
    : null;

  return (
    <Dialog open={Boolean(checkoutPlan)} onClose={() => setCheckoutPlan(null)} maxWidth="sm" fullWidth>
      <DialogTitle>{checkoutPlan?.title || t("selectPlan")}</DialogTitle>
      <DialogContent sx={{ pt: 2.5 }}>
        <Stack spacing={2}>
          {checkoutPlan && checkoutPlan.key !== "free" ? (
            isPaymentMaintenance ? (
              <Alert severity="warning" sx={{ mt: 2 }}>
                {t("paymentTerminalMaintenance")}
              </Alert>
            ) : (
              <>
                {billing?.double_time_for_project_support_enabled ? (
                  <Alert severity="info" sx={{ mt: 0.5 }}>
                    {billing.double_time_for_project_support_text || t("doubleTimeForProjectSupportText")}
                  </Alert>
                ) : null}
                <FormControl size="small" fullWidth sx={{ mt: 0.5 }}>
                  <InputLabel id={`${checkoutPlan.key}-checkout-period-label`}>{t("billingPeriod")}</InputLabel>
                  <Select
                    labelId={`${checkoutPlan.key}-checkout-period-label`}
                    label={t("billingPeriod")}
                    value={selectedPeriods[checkoutPlan.key] || bestPlanPeriod(billing, checkoutPlan, periodOptions)}
                    onChange={(event) => setSelectedPeriods((current) => ({ ...current, [checkoutPlan.key]: Number(event.target.value) }))}
                  >
                    {periodOptions.map((option) => (
                      <MenuItem key={option} value={option}>{formatPeriod(option)}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </>
            )
          ) : null}
          {!isPaymentMaintenance && checkoutOrder ? (
            <Alert severity="info">
              {formatOrderSummary(checkoutOrder)}
            </Alert>
          ) : null}
          {checkout.isError ? (
            <Alert severity="error">
              {formatCheckoutError(checkout.error, t)}
            </Alert>
          ) : null}
          {!isPaymentMaintenance ? (
            <FormControlLabel
              control={<Checkbox checked={offerAccepted} onChange={(event) => setOfferAccepted(event.target.checked)} />}
              label={
                <Typography variant="body2">
                  {t("billingOfferAccept")}{" "}
                  <Button
                    variant="text"
                    size="small"
                    onClick={(event) => {
                      event.currentTarget.blur();
                      setOfferOpen(true);
                    }}
                    sx={{ px: 0.5, minWidth: 0 }}
                  >
                    {t("billingOfferRead")}
                  </Button>
                </Typography>
              }
            />
          ) : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setCheckoutPlan(null)}>{isPaymentMaintenance ? t("close") : t("cancel")}</Button>
        {!isPaymentMaintenance ? (
          <Button variant="contained" disabled={!offerAccepted || !offer.data?.offer_text_hash || checkout.isPending} onClick={submitCheckout}>
            {checkout.isPending ? t("loading") : t("pay")}
          </Button>
        ) : null}
      </DialogActions>
    </Dialog>
  );
}
