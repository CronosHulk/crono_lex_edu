import { Backdrop, CircularProgress, Stack, Typography } from "@mui/material";
import { CheckCircle2, XCircle } from "lucide-react";

export function CheckPaymentOverlay({ open, phase, statusQuery, t }) {
  const status = statusQuery.data?.status;
  const isFailure = phase === "failure";
  const isSuccess = phase === "success";
  return (
    <Backdrop
      open={open}
      sx={{
        zIndex: (theme) => theme.zIndex.modal + 1,
        color: "common.white",
        bgcolor: "rgba(10, 16, 24, 0.82)",
        px: 2,
      }}
    >
      <Stack spacing={2.5} sx={{ alignItems: "center", textAlign: "center", maxWidth: 420 }}>
        {isSuccess ? (
          <CheckCircle2 size={72} />
        ) : isFailure ? (
          <XCircle size={72} />
        ) : (
          <CircularProgress color="inherit" size={72} thickness={4} />
        )}
        <Typography variant="h6" sx={{ fontWeight: 800 }}>
          {checkPaymentOverlayTitle(phase, status, t)}
        </Typography>
        <Typography variant="body2" sx={{ opacity: 0.82 }}>
          {checkPaymentOverlayMessage(phase, status, t)}
        </Typography>
      </Stack>
    </Backdrop>
  );
}

function checkPaymentOverlayTitle(phase, status, t) {
  if (phase === "redirecting") return t("paymentRedirectingTitle");
  if (phase === "success") return t("paymentSuccess");
  if (phase === "failure") return status?.message || t("paymentFailed");
  if (phase === "timeout") return t("paymentStillProcessingTitle");
  return t("paymentWaitingTitle");
}

function checkPaymentOverlayMessage(phase, status, t) {
  if (phase === "redirecting") return t("paymentRedirectingMessage");
  if (phase === "success") return t("paymentActivated");
  if (phase === "failure") return status?.failure_message || status?.message || t("paymentFailed");
  if (phase === "timeout") return t("paymentStillProcessingMessage");
  return t("paymentWaitingForInfo");
}
