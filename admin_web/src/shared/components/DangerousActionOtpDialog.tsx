import { Alert, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Stack, TextField } from "@mui/material";

type DangerousActionOtpDialogLabels = {
  cancel?: string;
  loading?: string;
  otp: string;
  verify: string;
};

export type DangerousActionOtpDialogProps = {
  t: DangerousActionOtpDialogLabels;
  open: boolean;
  title: string;
  text: string;
  otp: string;
  devOtpHint?: string | null;
  error?: string;
  pending: boolean;
  onOtpChange: (value: string) => void;
  onCancel: () => void;
  onConfirm: () => void;
};

export function DangerousActionOtpDialog({
  t,
  open,
  title,
  text,
  otp,
  devOtpHint,
  error,
  pending,
  onOtpChange,
  onCancel,
  onConfirm,
}: DangerousActionOtpDialogProps) {
  return (
    <Dialog open={open} onClose={pending ? undefined : onCancel} maxWidth="sm" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <DialogContentText>{text}</DialogContentText>
          {devOtpHint && <Alert severity="info">Dev OTP: {devOtpHint}</Alert>}
          {error && <Alert severity="error">{error}</Alert>}
          <TextField
            label={t.otp}
            value={otp}
            onChange={(event) => onOtpChange(event.target.value)}
            slotProps={{ htmlInput: { inputMode: "numeric", maxLength: 16 } }}
            autoFocus
            fullWidth
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel} disabled={pending}>{t.cancel || "Cancel"}</Button>
        <Button color="error" variant="contained" onClick={onConfirm} disabled={pending || otp.trim().length < 6}>
          {pending ? t.loading : t.verify}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
