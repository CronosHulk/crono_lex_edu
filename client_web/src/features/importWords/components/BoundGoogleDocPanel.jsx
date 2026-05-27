import { Alert, Button, CircularProgress, Stack, Typography } from "@mui/material";
import { Link as LinkIcon, Unlink } from "lucide-react";

export function BoundGoogleDocPanel({ t, docId, disabled, onUnbind }) {
  return (
    <Alert
      severity="info"
      icon={<LinkIcon size={18} />}
      action={
        <Button
          color="inherit"
          disabled={disabled}
          onClick={onUnbind}
          size="small"
          startIcon={disabled ? <CircularProgress color="inherit" size={14} /> : <Unlink size={16} />}
        >
          {t("importWordsUnbindGoogleDoc")}
        </Button>
      }
      sx={{
        alignItems: "center",
        "& .MuiAlert-message": { minWidth: 0 },
        "& .MuiAlert-action": { alignItems: "center", pl: 1 },
      }}
    >
      <Stack spacing={0.4}>
        <Typography variant="subtitle2" fontWeight={700}>{t("importWordsBoundGoogleDoc")}</Typography>
        <Typography variant="body2" sx={{ overflowWrap: "anywhere" }}>{maskGoogleDocId(docId)}</Typography>
      </Stack>
    </Alert>
  );
}

function maskGoogleDocId(value) {
  const docId = String(value || "").trim();
  if (!docId) return "";
  const masked = docId.length > 8 ? `${docId.slice(0, 4)}...${docId.slice(-4)}` : "***";
  return `https://docs.google.com/document/d/${masked}/...`;
}
