import { Box, Stack, Typography } from "@mui/material";

export type LogFieldProps = {
  label: string;
  value?: string | number | null;
  layout?: "stacked" | "inline";
};

export function LogField({ label, value, layout = "stacked" }: LogFieldProps) {
  const displayValue = value === null || value === undefined || value === "" ? "-" : value;

  if (layout === "inline") {
    return (
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "max-content minmax(0, 1fr)",
          columnGap: 1,
          alignItems: "baseline",
        }}
      >
        <Typography className="history-field-label" variant="caption" color="text.secondary">
          {label}:
        </Typography>
        <Typography className="muted" variant="body2" color="text.secondary" sx={{ minWidth: 0, overflowWrap: "anywhere" }}>
          {displayValue}
        </Typography>
      </Box>
    );
  }

  return (
    <Stack spacing={0.25}>
      <Typography className="history-field-label" variant="caption" color="text.secondary">{label}</Typography>
      <Typography className="muted" variant="body2" color="text.secondary">{displayValue}</Typography>
    </Stack>
  );
}
