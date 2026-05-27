import { Alert, Box, Chip, CircularProgress, Paper, Stack, Typography } from "@mui/material";

export function LoginHistoryList({ t, records, loading, error, compact = false, horizontal = false }) {
  return (
    <Stack
      direction={horizontal ? "row" : "column"}
      spacing={compact ? 1 : 1.5}
      sx={horizontal ? { overflowX: "auto", pb: records.length > 0 ? 0.5 : 0 } : undefined}
    >
      {error && <Alert severity="error">{error}</Alert>}
      {!error && records.length === 0 && !loading && <Typography color="text.secondary">{t.noLoginHistory}</Typography>}
      {records.map((record, index) => (
        <Paper
          variant="outlined"
          key={record.id || `${record.created || record.created_at || index}-${index}`}
          sx={{
            p: compact ? 1.25 : 1.5,
            borderColor: "divider",
            ...(horizontal ? { flex: "0 0 min(420px, 88vw)" } : {}),
          }}
        >
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "minmax(0, 1fr) minmax(0, 1fr)" }, gap: 1.5 }}>
            <Box>
              <Typography variant="caption" color="text.secondary">{t.date}</Typography>
              <Typography variant="subtitle2">{record.created || record.created_at || record.logged_at || "-"}</Typography>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>{t.ipAddress}</Typography>
              <Typography variant="body2" color="text.secondary">{record.client_ip || record.ip_address || record.ip || "-"}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">{t.result}</Typography>
              <Box sx={{ mt: 0.25, mb: 1 }}>
                <Chip label={record.result || record.status || (record.is_success ? "success" : "unknown")} size="small" variant="outlined" />
              </Box>
              <Typography variant="caption" color="text.secondary">{t.userAgent}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ overflowWrap: "anywhere" }}>{record.user_agent || record.device || "-"}</Typography>
            </Box>
          </Box>
        </Paper>
      ))}
      {loading && (
        <Stack direction="row" spacing={1} alignItems="center" color="text.secondary">
          <CircularProgress size={18} />
          <Typography variant="body2">{t.loading}</Typography>
        </Stack>
      )}
    </Stack>
  );
}
