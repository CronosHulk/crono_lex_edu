import {
  Box,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material";
import { CheckCircle2, Clock3, XCircle } from "lucide-react";

import { RESULT_PAGE_SIZE_OPTIONS } from "../constants";

const RESULT_TABLE_COLUMN_SX = {
  word: { width: "40%", minWidth: 360 },
  aiForm: { width: 140 },
  partOfSpeech: { width: 170 },
  parsedTranslation: { width: "24%", minWidth: 240 },
  status: { width: 190 },
};
const REJECTED_WORD_PREVIEW_MAX_CHARS = 30;

export function ImportResultTable({
  t,
  rows,
  total,
  page,
  pageSize,
  loading,
  summary,
  statusCategory,
  showSummary,
  resolvingIds,
  newRowIds,
  onPageChange,
  onPageSizeChange,
  onStatusCategoryChange,
}) {
  return (
    <Paper variant="outlined" sx={{ p: 2, borderColor: "divider" }}>
      <Stack spacing={2}>
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", justifyContent: "space-between" }}>
          <Typography variant="h6" fontWeight={700}>{t("importWordsResult")}</Typography>
          {loading && <CircularProgress size={20} />}
        </Stack>
        {showSummary && (
          <ImportSummary
            t={t}
            summary={summary}
            activeFilter={statusCategory}
            onFilterChange={onStatusCategoryChange}
          />
        )}
        <TableContainer sx={{ border: 1, borderColor: "divider", borderRadius: 1, overflowX: "auto" }}>
          <Table size="small" sx={{ minWidth: 1120, tableLayout: "fixed" }}>
            <TableHead>
              <TableRow>
                <TableCell sx={RESULT_TABLE_COLUMN_SX.word}>{t("word")}</TableCell>
                <TableCell sx={RESULT_TABLE_COLUMN_SX.aiForm}>{t("importWordsAiForm")}</TableCell>
                <TableCell sx={RESULT_TABLE_COLUMN_SX.partOfSpeech}>{t("partOfSpeech")}</TableCell>
                <TableCell sx={RESULT_TABLE_COLUMN_SX.parsedTranslation}>{t("importWordsParsedTranslation")}</TableCell>
                <TableCell align="right" sx={RESULT_TABLE_COLUMN_SX.status}>{t("status")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5}>
                    <Box sx={{ py: 4, textAlign: "center", color: "text.secondary" }}>
                      {loading ? t("loading") : t("importWordsNoResults")}
                    </Box>
                  </TableCell>
                </TableRow>
              ) : rows.map((row) => (
                <ImportResultRow
                  key={row.id}
                  row={row}
                  isResolving={resolvingIds.has(row.id)}
                  isNew={newRowIds.has(row.id)}
                />
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div"
          count={total}
          page={Math.max(page - 1, 0)}
          rowsPerPage={pageSize}
          rowsPerPageOptions={RESULT_PAGE_SIZE_OPTIONS}
          labelRowsPerPage={t("wordsPerPage")}
          onPageChange={(_, nextPage) => onPageChange(nextPage + 1)}
          onRowsPerPageChange={(event) => onPageSizeChange(Number(event.target.value))}
        />
      </Stack>
    </Paper>
  );
}

function ImportResultRow({ row, isResolving, isNew }) {
  const parsedTranslation = row.validated_translation_uk || row.translation_hint || "";
  const isRejected = row.status_category === "rejected";
  return (
    <TableRow
      hover
      sx={{
        animation: isNew ? "importRowFade 480ms ease-out both" : "none",
        "@keyframes importRowFade": {
          from: { opacity: 0, transform: "translateY(-8px)" },
          to: { opacity: 1, transform: "translateY(0)" },
        },
      }}
    >
      <TableCell sx={{ verticalAlign: "middle", overflowWrap: "anywhere" }}>
        <RejectedWordText value={row.word} isRejected={isRejected} variant="body2" fontWeight={600} />
        {row.raw_value && row.raw_value !== row.word && (
          <RejectedWordText value={row.raw_value} isRejected={isRejected} variant="caption" color="text.secondary" />
        )}
      </TableCell>
      <TableCell sx={{ verticalAlign: "middle", overflowWrap: "anywhere" }}>{row.validated_word || "-"}</TableCell>
      <TableCell sx={{ verticalAlign: "middle", overflowWrap: "anywhere" }}>{row.validated_part_of_speech || "-"}</TableCell>
      <TableCell sx={{ verticalAlign: "middle", overflowWrap: "anywhere" }}>{parsedTranslation || "-"}</TableCell>
      <TableCell align="right" sx={{ verticalAlign: "middle" }}>
        <Box sx={{ minHeight: 26, display: "flex", alignItems: "center", justifyContent: "flex-end" }}>
          {isResolving ? <ProcessingStatus /> : <StatusChip row={row} />}
        </Box>
      </TableCell>
    </TableRow>
  );
}

function RejectedWordText({ value, isRejected, ...typographyProps }) {
  const text = String(value || "");
  const displayText = isRejected ? truncateRejectedWord(text) : text;
  const content = (
    <Typography {...typographyProps} sx={{ display: "block" }}>
      {displayText}
    </Typography>
  );
  if (!isRejected || displayText === text) {
    return content;
  }
  return (
    <Tooltip title={text} arrow>
      {content}
    </Tooltip>
  );
}

function truncateRejectedWord(value) {
  const text = String(value || "");
  if (text.length <= REJECTED_WORD_PREVIEW_MAX_CHARS) {
    return text;
  }
  return `${text.slice(0, REJECTED_WORD_PREVIEW_MAX_CHARS).trimEnd()}...`;
}

function ImportSummary({ t, summary, activeFilter, onFilterChange }) {
  const added = Number(summary?.added || 0);
  const queued = Number(summary?.queued || 0);
  const rejected = Number(summary?.rejected || 0);
  const processing = Number(summary?.processing || 0);
  const all = added + queued + rejected + processing;
  return (
    <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
      <SummaryFilterChip
        active={activeFilter === "all"}
        color="default"
        label={`${t("all")}: ${all}`}
        onClick={() => onFilterChange("all")}
      />
      <SummaryFilterChip
        active={activeFilter === "added"}
        color="success"
        label={`${t("importWordsSummaryAdded")}: ${added}`}
        onClick={() => onFilterChange("added")}
      />
      <SummaryFilterChip
        active={activeFilter === "queued"}
        color="warning"
        label={`${t("importWordsSummaryReview")}: ${queued}`}
        onClick={() => onFilterChange("queued")}
      />
      <SummaryFilterChip
        active={activeFilter === "rejected"}
        color="error"
        label={`${t("importWordsSummaryRejected")}: ${rejected}`}
        onClick={() => onFilterChange("rejected")}
      />
    </Stack>
  );
}

function SummaryFilterChip({ active, color, label, onClick }) {
  return (
    <Chip
      clickable
      color={color}
      label={label}
      onClick={onClick}
      size="small"
      variant={active ? "filled" : "outlined"}
    />
  );
}

function ProcessingStatus() {
  return (
    <Box
      aria-label="processing"
      sx={{
        width: 34,
        height: 24,
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        verticalAlign: "middle",
      }}
    >
      <CircularProgress size={18} thickness={5} />
    </Box>
  );
}

function StatusChip({ row }) {
  if (row.status_category === "added") {
    return <Chip color="success" icon={<CheckCircle2 size={16} />} label={row.status_label} size="small" />;
  }
  if (row.status_category === "rejected") {
    return <Chip color="error" icon={<XCircle size={16} />} label={row.status_label} size="small" />;
  }
  return <Chip color="warning" icon={<Clock3 size={16} />} label={row.status_label} size="small" />;
}
