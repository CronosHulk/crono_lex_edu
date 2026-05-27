import { useMemo, useState } from "react";
import {
  Box,
  Button,
  Checkbox,
  Chip,
  FormControl,
  InputLabel,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { ArrowUpToLine, RotateCcw } from "lucide-react";
import { useSearchParams } from "react-router-dom";

import { useClientI18n } from "../../../shared/i18n/clientI18n";
import { useLearningWordFilters, useLearningWords, usePrioritizeLearningWord } from "../api/learningApi";

const EMPTY_ROWS = [];
const DEFAULT_PAGE_SIZE = 20;
const PAGE_SIZE_OPTIONS = [20, 50];

export function LearningWordTable({ mode, title, allowReviewAction = false, rows = EMPTY_ROWS, topicFilter = "" }) {
  const { t } = useClientI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const page = readPageIndex(searchParams.get("page"));
  const pageSize = readAllowedPageSize(searchParams.get("page_size"));
  const [selectedIds, setSelectedIds] = useState([]);
  const filters = useMemo(() => ({
    word: searchParams.get("word") || "",
    topic: readTopicFilters(searchParams, topicFilter),
    level: searchParams.get("level") || "",
  }), [searchParams, topicFilter]);
  const shouldFetch = mode === "learning" || mode === "learned";
  const allowPriorityAction = mode === "learning";
  const filterOptions = useLearningWordFilters();
  const prioritizeWord = usePrioritizeLearningWord();
  const wordsQuery = useLearningWords({
    mode,
    page: page + 1,
    pageSize,
    word: filters.word,
    topic: filters.topic,
    level: filters.level,
    enabled: shouldFetch,
  });
  const localFilteredRows = useMemo(() => filterRows(rows, filters), [filters, rows]);
  const fetchedRows = useMemo(() => (shouldFetch ? (wordsQuery.data?.items || []) : rows), [rows, shouldFetch, wordsQuery.data?.items]);
  const topicOptions = useMemo(
    () => buildTopicOptions(filterOptions.data?.topics || [], shouldFetch ? fetchedRows : localFilteredRows),
    [filterOptions.data?.topics, fetchedRows, localFilteredRows, shouldFetch],
  );
  const totalRows = shouldFetch ? Number(wordsQuery.data?.total || 0) : localFilteredRows.length;
  const pageRows = shouldFetch ? fetchedRows : localFilteredRows.slice(page * pageSize, page * pageSize + pageSize);
  const allFilteredSelected = pageRows.length > 0 && pageRows.every((row) => selectedIds.includes(row.id));
  const heading = title || (mode === "learned" ? t("learnedWords") : t("learningWords"));
  const columnCount = 5 + (allowReviewAction ? 1 : 0) + (allowPriorityAction ? 1 : 0);

  function updateFilter(name, value) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.set("page", "1");
      if (name === "topic") {
        next.delete("topic");
        value.forEach((topic) => {
          if (topic) next.append("topic", topic);
        });
        return next;
      }
      if (value) next.set(name, value);
      else next.delete(name);
      return next;
    });
  }

  function updatePage(nextPage) {
    updateSearchParams(setSearchParams, { page: nextPage + 1 });
  }

  function updatePageSize(nextPageSize) {
    updateSearchParams(setSearchParams, {
      page: 1,
      page_size: PAGE_SIZE_OPTIONS.includes(nextPageSize) ? nextPageSize : DEFAULT_PAGE_SIZE,
    });
  }

  function toggleRow(rowId) {
    setSelectedIds((current) => current.includes(rowId) ? current.filter((id) => id !== rowId) : [...current, rowId]);
  }

  function toggleFilteredRows() {
    if (allFilteredSelected) {
      setSelectedIds((current) => current.filter((id) => !pageRows.some((row) => row.id === id)));
      return;
    }
    setSelectedIds((current) => Array.from(new Set([...current, ...pageRows.map((row) => row.id)])));
  }

  function prioritizeRow(row) {
    prioritizeWord.mutate({
      word_source: row.word_source || "core",
      word_id: Number(row.word_id || row.id),
    });
  }

  return (
    <Paper variant="outlined" sx={{ p: 2, borderColor: "divider" }}>
      <Stack spacing={2}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={1.5}
          sx={{
            alignItems: { xs: "stretch", md: "center" },
            justifyContent: "space-between",
          }}
        >
          <Typography variant="h6" fontWeight={700}>{heading}</Typography>
          {allowReviewAction && (
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
              <Button variant="outlined" onClick={toggleFilteredRows} disabled={pageRows.length === 0}>
                {allFilteredSelected ? t("clearPageSelection") : t("selectOnPage")}
              </Button>
              <Button variant="contained" startIcon={<RotateCcw size={18} />} disabled={selectedIds.length === 0}>
                {t("sendToReview")}
              </Button>
            </Stack>
          )}
        </Stack>
        <LearningWordFilters
          filters={filters}
          topicOptions={topicOptions}
          topicOptionsError={filterOptions.isError}
          topicOptionsLoading={filterOptions.isLoading}
          onChange={updateFilter}
        />
        <TableContainer sx={{ border: 1, borderColor: "divider", borderRadius: 1 }}>
          <Table size="small" sx={{ minWidth: allowReviewAction || allowPriorityAction ? 980 : 820 }}>
            <TableHead>
              <TableRow>
                {allowReviewAction && <TableCell padding="checkbox" />}
                <TableCell>{t("word")}</TableCell>
                <TableCell>{t("topic")}</TableCell>
                <TableCell>{t("level")}</TableCell>
                <TableCell>{t("translation")}</TableCell>
                <TableCell>{t("status")}</TableCell>
                {allowPriorityAction && <TableCell align="right">{t("actions")}</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {wordsQuery.isLoading ? (
                <TableRow>
                  <TableCell colSpan={columnCount}>
                    <Box sx={{ py: 4, textAlign: "center", color: "text.secondary" }}>{t("loading")}</Box>
                  </TableCell>
                </TableRow>
              ) : pageRows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={columnCount}>
                    <Box sx={{ py: 4, textAlign: "center", color: "text.secondary" }}>{t("noWordsYet")}</Box>
                  </TableCell>
                </TableRow>
              ) : pageRows.map((row, rowIndex) => {
                const showPriorityAction = allowPriorityAction && page * pageSize + rowIndex >= 10;
                return (
                  <TableRow key={rowKey(row)} hover selected={selectedIds.includes(row.id)}>
                    {allowReviewAction && (
                      <TableCell padding="checkbox">
                        <Checkbox checked={selectedIds.includes(row.id)} onChange={() => toggleRow(row.id)} />
                      </TableCell>
                    )}
                    <TableCell>{row.word}</TableCell>
                    <TableCell>{row.topic}</TableCell>
                    <TableCell>{row.level}</TableCell>
                    <TableCell>{row.translation}</TableCell>
                    <TableCell>{row.status}</TableCell>
                    {allowPriorityAction && (
                      <TableCell align="right">
                        {showPriorityAction && (
                          <Tooltip title={t("firstPriorityHint")}>
                            <span>
                              <Button
                                size="small"
                                variant="text"
                                color="inherit"
                                startIcon={<ArrowUpToLine size={14} />}
                                disabled={prioritizeWord.isPending}
                                onClick={() => prioritizeRow(row)}
                                sx={{
                                  minWidth: 0,
                                  px: 1,
                                  py: 0.25,
                                  fontSize: "0.75rem",
                                  color: row.is_priority ? "primary.main" : "text.secondary",
                                  "& .MuiButton-startIcon": { mr: 0.5 },
                                }}
                              >
                                {t("firstPriority")}
                              </Button>
                            </span>
                          </Tooltip>
                        )}
                      </TableCell>
                    )}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div"
          count={totalRows}
          page={page}
          rowsPerPage={pageSize}
          rowsPerPageOptions={PAGE_SIZE_OPTIONS}
          labelRowsPerPage={t("wordsPerPage")}
          onPageChange={(_, nextPage) => updatePage(nextPage)}
          onRowsPerPageChange={(event) => {
            updatePageSize(Number(event.target.value));
          }}
        />
      </Stack>
    </Paper>
  );
}

function updateSearchParams(setSearchParams, updates) {
  setSearchParams((current) => {
    const next = new URLSearchParams(current);
    Object.entries(updates).forEach(([key, value]) => {
      if (value === "" || value === null || value === undefined) next.delete(key);
      else next.set(key, String(value));
    });
    return next;
  });
}

function rowKey(row) {
  return `${row.word_source || "core"}:${row.word_id || row.id}`;
}

function readPageIndex(value) {
  const parsed = Number(value || "");
  return Number.isInteger(parsed) && parsed > 0 ? parsed - 1 : 0;
}

function readAllowedPageSize(value) {
  const parsed = Number(value || "");
  return Number.isInteger(parsed) && PAGE_SIZE_OPTIONS.includes(parsed) ? parsed : DEFAULT_PAGE_SIZE;
}

function readTopicFilters(searchParams, topicFilter) {
  const topics = searchParams.getAll("topic").filter(Boolean);
  if (topics.length > 0) return topics;
  return topicFilter ? [topicFilter] : [];
}

function LearningWordFilters({ filters, topicOptions, topicOptionsError, topicOptionsLoading, onChange }) {
  const { t } = useClientI18n();
  return (
    <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
      <TextField label={t("word")} value={filters.word} onChange={(event) => onChange("word", event.target.value)} size="small" fullWidth />
      <TopicMultiSelect
        value={filters.topic}
        options={topicOptions}
        isError={topicOptionsError}
        isLoading={topicOptionsLoading}
        onChange={(value) => onChange("topic", value)}
      />
      <FormControl size="small" fullWidth>
        <InputLabel id="learning-level-filter-label">{t("level")}</InputLabel>
        <Select
          labelId="learning-level-filter-label"
          label={t("level")}
          value={filters.level}
          onChange={(event) => onChange("level", event.target.value)}
        >
          <MenuItem value="">{t("all")}</MenuItem>
          <MenuItem value="A1">A1</MenuItem>
          <MenuItem value="A2">A2</MenuItem>
          <MenuItem value="B1">B1</MenuItem>
          <MenuItem value="B2">B2</MenuItem>
          <MenuItem value="C1">C1</MenuItem>
          <MenuItem value="C2">C2</MenuItem>
        </Select>
      </FormControl>
    </Stack>
  );
}

function TopicMultiSelect({ value, options, isError, isLoading, onChange }) {
  const { t } = useClientI18n();
  const selectedLabels = value.map((item) => options.find((option) => option.value === item)?.label || item);
  const emptyLabel = isLoading ? t("topicsLoading") : isError ? t("topicsLoadFailed") : t("noTopics");
  return (
    <FormControl size="small" fullWidth>
      <InputLabel id="learning-topic-filter-label">{t("topic")}</InputLabel>
      <Select
        labelId="learning-topic-filter-label"
        label={t("topic")}
        multiple
        value={value}
        onChange={(event) => onChange(typeof event.target.value === "string" ? event.target.value.split(",") : event.target.value)}
        renderValue={() => (
          <Stack direction="row" spacing={0.5} useFlexGap sx={{ flexWrap: "wrap" }}>
            {selectedLabels.map((label) => <Chip key={label} label={label} size="small" />)}
          </Stack>
        )}
      >
        {options.length === 0 && <MenuItem disabled>{emptyLabel}</MenuItem>}
        {options.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            <Checkbox checked={value.includes(option.value)} size="small" />
            <ListItemText primary={option.label} />
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}

function buildTopicOptions(apiOptions, rows) {
  if (apiOptions.length > 0) return apiOptions;
  const byValue = new Map();
  rows.forEach((row) => {
    const codes = Array.isArray(row.topic_codes) ? row.topic_codes : [];
    const labels = String(row.topic || "").split(",").map((item) => item.trim());
    codes.forEach((code, index) => {
      if (!code || byValue.has(code)) return;
      byValue.set(code, { value: code, label: labels[index] || code });
    });
  });
  return Array.from(byValue.values());
}

function filterRows(rows, filters) {
  const word = filters.word.trim().toLowerCase();
  const topics = filters.topic;
  return rows.filter((row) => {
    if (word && !row.word.toLowerCase().includes(word)) return false;
    if (topics.length > 0 && !topics.some((topic) => row.topic.split(",").map((item) => item.trim()).includes(topic))) return false;
    if (filters.level && row.level !== filters.level) return false;
    return true;
  });
}
