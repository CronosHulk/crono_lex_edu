import { Accordion, AccordionDetails, AccordionSummary, Box, Typography } from "@mui/material";

export type JsonPreviewProps = {
  title: string;
  value: unknown;
};

export function JsonPreview({ title, value }: JsonPreviewProps) {
  if (!hasPreviewValue(value)) return null;

  return (
    <Accordion className="json-preview" variant="outlined" disableGutters sx={{ bgcolor: "transparent" }}>
      <AccordionSummary>
        <Typography variant="body2">{title}</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Box component="pre" sx={{ m: 0, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
          {formatJsonPreviewValue(value)}
        </Box>
      </AccordionDetails>
    </Accordion>
  );
}

export function hasPreviewValue(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (typeof value !== "object") return false;
  return Object.keys(value).length > 0;
}

export function formatJsonPreviewValue(value: unknown): string {
  return JSON.stringify(value, null, 2) ?? "";
}
