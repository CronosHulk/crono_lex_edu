import { Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Stack, Typography } from "@mui/material";
import { PartyPopper, ReceiptText, XCircle } from "lucide-react";

import {
  deliverableTaxUrlReceipts,
  formatPaymentDate,
  formatPaymentStatus,
  formatPaymentTitle,
  formatSubscriptionDate,
  hasPendingReceipt,
  hasStoredReceiptFile,
} from "../helpers/planPageHelpers";

export function SubscriptionSummary({ subscription, t, intlLocale }) {
  if (!subscription?.end || !subscription.remaining_seconds) return null;
  return (
    <Alert severity="info">
      {t("subscriptionValidUntil", { date: formatSubscriptionDate(subscription.end, intlLocale) })}{" "}
      {t("subscriptionRemainingDays", { days: subscription.remaining_days })}
    </Alert>
  );
}

export function PaymentStatusPanel({ query, t }) {
  const payload = query.data;
  const status = payload?.status;
  if (!payload && query.isLoading) {
    return <Alert icon={<CircularProgress size={18} />} severity="info">{t("paymentWaiting")}</Alert>;
  }
  if (query.isError) return <Alert severity="error">{query.error.message || t("loadError")}</Alert>;
  if (status?.is_success) {
    return <Alert icon={<PartyPopper size={28} />} severity="success">{t("paymentActivated")}</Alert>;
  }
  if (status?.is_failure) {
    return <Alert icon={<XCircle size={28} />} severity="error">{status.message || t("paymentFailed")}</Alert>;
  }
  return <Alert icon={<CircularProgress size={18} />} severity="info">{status?.message || t("paymentWaiting")}</Alert>;
}

export function PaymentHistoryPanel({ query, t, intlLocale }) {
  const items = query.data?.items || [];
  return (
    <Stack spacing={1.25}>
      <Typography variant="h6" sx={{ fontWeight: 800 }}>{t("paymentHistory")}</Typography>
      {query.isLoading ? <Alert icon={<CircularProgress size={18} />} severity="info">{t("loading")}</Alert> : null}
      {query.isError ? <Alert severity="error">{query.error.message || t("loadError")}</Alert> : null}
      {!query.isLoading && !items.length ? <Alert severity="info">{t("paymentHistoryEmpty")}</Alert> : null}
      {items.map((payment) => (
        <Card key={payment.id} variant="outlined">
          <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
            <Stack spacing={1}>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ justifyContent: "space-between", alignItems: { xs: "flex-start", sm: "center" } }}>
                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
                    {formatPaymentTitle(payment)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {formatPaymentDate(payment.paid_at || payment.created, intlLocale)}
                  </Typography>
                </Box>
                <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap", justifyContent: { xs: "flex-start", sm: "flex-end" } }}>
                  {deliverableTaxUrlReceipts(payment).map((receipt) => (
                    <Button
                      key={receipt.tax_url}
                      size="small"
                      variant="outlined"
                      href={receipt.tax_url}
                      target="_blank"
                      rel="noreferrer"
                      startIcon={<ReceiptText size={16} />}
                    >
                      {t("receipt")}
                    </Button>
                  ))}
                  {hasStoredReceiptFile(payment) && !deliverableTaxUrlReceipts(payment).length ? (
                    <Typography variant="caption" color="text.secondary">{t("receiptStored")}</Typography>
                  ) : null}
                  {hasPendingReceipt(payment) ? (
                    <Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
                      <CircularProgress size={14} />
                      <Typography variant="caption" color="text.secondary">{t("receiptPending")}</Typography>
                    </Stack>
                  ) : null}
                  <Chip size="small" label={formatPaymentStatus(payment.status, t)} color={payment.status === "success" ? "success" : payment.status === "failure" || payment.status === "reversed" || payment.status === "expired" ? "error" : "default"} />
                </Stack>
              </Stack>
              {payment.promotion_label ? (
                <Chip size="small" label={payment.promotion_label} color="primary" variant="outlined" sx={{ alignSelf: "flex-start" }} />
              ) : null}
              {payment.failure_message ? <Typography variant="body2" color="error.main">{payment.failure_message}</Typography> : null}
            </Stack>
          </CardContent>
        </Card>
      ))}
    </Stack>
  );
}
