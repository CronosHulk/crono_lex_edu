import {
  Alert,
  Box,
  Button,
  FormControl,
  IconButton,
  InputLabel,
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
import { GraduationCap, Volume2 } from "lucide-react";
import { useSearchParams } from "react-router-dom";

import { usePlans } from "../plans/api/plansApi";
import { useClientI18n } from "../../shared/i18n/clientI18n";
import { playAudio } from "../../shared/helpers/audio";
import { useDictionarySearch, useLearnDictionaryWord, useLearningWordFilters } from "./api/learningApi";

const DEFAULT_PAGE_SIZE = 20;

export function DictionarySearchPage() {
  const { t } = useClientI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("q") || "";
  const level = searchParams.get("level") || "";
  const page = Math.max(Number(searchParams.get("page") || "1"), 1) - 1;
  const pageSize = Number(searchParams.get("page_size") || DEFAULT_PAGE_SIZE);
  const filters = useLearningWordFilters();
  const plans = usePlans();
  const learn = useLearnDictionaryWord();
  const enabled = query.trim().length >= 3;
  const search = useDictionarySearch({
    query,
    level,
    page: page + 1,
    pageSize,
    enabled,
  });
  const levelOptions = filterLevelOptions(filters.data?.levels || [], plans.data);
  const rows = enabled ? (search.data?.items || []) : [];
  const total = enabled ? Number(search.data?.total || 0) : 0;

  function updateParam(name, value) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      if (value) next.set(name, value);
      else next.delete(name);
      next.set("page", "1");
      return next;
    });
  }

  function updatePage(nextPage) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.set("page", String(nextPage + 1));
      return next;
    });
  }

  function updatePageSize(nextPageSize) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.set("page", "1");
      next.set("page_size", String(nextPageSize));
      return next;
    });
  }

  function learnWord(row) {
    learn.mutate({ word_source: row.word_source || "core", word_id: Number(row.word_id) });
  }

  return (
    <Paper variant="outlined" sx={{ p: 2, borderColor: "divider" }}>
      <Stack spacing={2}>
        <Typography variant="h6" fontWeight={700}>{t("dictionarySearchTitle")}</Typography>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
          <TextField
            label={t("dictionarySearchWord")}
            value={query}
            onChange={(event) => updateParam("q", event.target.value)}
            size="small"
            fullWidth
          />
          <FormControl size="small" fullWidth>
            <InputLabel id="dictionary-search-level-label">{t("level")}</InputLabel>
            <Select
              labelId="dictionary-search-level-label"
              label={t("level")}
              value={level}
              onChange={(event) => updateParam("level", event.target.value)}
            >
              <MenuItem value="">{t("all")}</MenuItem>
              {levelOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Stack>
        {query && !enabled ? <Alert severity="info">{t("dictionarySearchMinQuery")}</Alert> : null}
        {search.isError ? <Alert severity="error">{search.error.message || t("loadError")}</Alert> : null}
        {learn.isError ? <Alert severity="error">{learn.error.message || t("saveError")}</Alert> : null}
        {learn.isSuccess ? <Alert severity="success">{t("dictionarySearchLearned")}</Alert> : null}
        <TableContainer sx={{ border: 1, borderColor: "divider", borderRadius: 1 }}>
          <Table size="small" sx={{ minWidth: 860 }}>
            <TableHead>
              <TableRow>
                <TableCell>{t("word")}</TableCell>
                <TableCell>{t("transcription")}</TableCell>
                <TableCell>{t("level")}</TableCell>
                <TableCell>{t("translation")}</TableCell>
                <TableCell align="right">{t("actions")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {search.isLoading ? (
                <TableRow>
                  <TableCell colSpan={5}>
                    <Box sx={{ py: 4, textAlign: "center", color: "text.secondary" }}>{t("loading")}</Box>
                  </TableCell>
                </TableRow>
              ) : rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5}>
                    <Box sx={{ py: 4, textAlign: "center", color: "text.secondary" }}>
                      {enabled ? t("dictionarySearchNoResults") : t("dictionarySearchPrompt")}
                    </Box>
                  </TableCell>
                </TableRow>
              ) : rows.map((row) => (
                <TableRow key={row.id} hover>
                  <TableCell>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 0 }}>
                      {row.audio_url ? (
                        <Tooltip title={t("listenPronunciation")}>
                          <IconButton
                            size="small"
                            color="primary"
                            aria-label={t("listenWordPronunciation", { word: row.word })}
                            onClick={() => playAudio(row.audio_url)}
                            sx={{ flex: "0 0 auto" }}
                          >
                            <Volume2 size={18} />
                          </IconButton>
                        </Tooltip>
                      ) : null}
                      <Box component="span" sx={{ minWidth: 0 }}>{row.word}</Box>
                    </Box>
                  </TableCell>
                  <TableCell>{row.transcription || ""}</TableCell>
                  <TableCell>{row.level}</TableCell>
                  <TableCell>{row.translation}</TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      variant="contained"
                      startIcon={<GraduationCap size={16} />}
                      disabled={learn.isPending}
                      onClick={() => learnWord(row)}
                    >
                      {t("learnWord")}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div"
          count={total}
          page={page}
          rowsPerPage={pageSize}
          rowsPerPageOptions={[20, 50]}
          labelRowsPerPage={t("wordsPerPage")}
          onPageChange={(_, nextPage) => updatePage(nextPage)}
          onRowsPerPageChange={(event) => updatePageSize(Number(event.target.value))}
        />
      </Stack>
    </Paper>
  );
}

function filterLevelOptions(levels, plansData) {
  const entitlements = plansData?.plans?.find((plan) => plan.key === plansData.current_plan_key)?.entitlements;
  const allowedLevels = entitlements?.level_titles;
  if (!Array.isArray(allowedLevels)) return levels;
  return levels.filter((level) => allowedLevels.includes(level.value));
}
