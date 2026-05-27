import { useState } from "react";
import { Box, Button, Chip, Stack, Typography } from "@mui/material";
import { FileText, Upload } from "lucide-react";

export function DropZone({ t, fileState, disabled, inputRef, onFile, onReset }) {
  const [isDragging, setIsDragging] = useState(false);
  return (
    <Box
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled) setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragging(false);
        if (!disabled) onFile(event.dataTransfer.files?.[0]);
      }}
      sx={{
        p: 2,
        minHeight: 156,
        border: 1,
        borderStyle: "dashed",
        borderColor: isDragging ? "primary.main" : "divider",
        borderRadius: 1,
        bgcolor: isDragging ? "action.hover" : "transparent",
        display: "grid",
        placeItems: "center",
        textAlign: "center",
      }}
    >
      <Stack spacing={1.25} alignItems="center">
        <Box sx={{ color: "primary.main", display: "grid", placeItems: "center" }}>
          <FileText />
        </Box>
        <Typography variant="subtitle2" fontWeight={700}>
          {fileState.name || t("importWordsDropTxt")}
        </Typography>
        {fileState.name && (
          <Chip
            label={`${fileState.name} · ${formatBytes(fileState.size)}`}
            onDelete={disabled ? undefined : onReset}
            size="small"
          />
        )}
        <Button component="label" variant="outlined" disabled={disabled} startIcon={<Upload size={18} />}>
          {t("importWordsChooseTxt")}
          <input
            ref={inputRef}
            type="file"
            accept=".txt,text/plain"
            hidden
            onChange={(event) => onFile(event.target.files?.[0])}
          />
        </Button>
      </Stack>
    </Box>
  );
}

function formatBytes(value) {
  if (!value) return "0 KB";
  return `${Math.ceil(value / 1024)} KB`;
}
