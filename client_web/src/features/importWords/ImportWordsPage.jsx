import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  InputAdornment,
  Link,
  List,
  ListItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { Link as LinkIcon, Upload } from "lucide-react";
import { Link as RouterLink, useLocation, useSearchParams } from "react-router-dom";

import { useImportItems, useImportJobEvents, useImportJobItems, useSubmitImportWords, useUnbindImportGoogleDoc } from "./api/importWordsApi";
import { BoundGoogleDocPanel } from "./components/BoundGoogleDocPanel";
import { ImportResultTable } from "./components/ImportResultTable";
import {
  RESULT_PAGE_SIZE,
  RESULT_PAGE_SIZE_OPTIONS,
  RESULT_STATUS_FILTERS,
} from "./constants";
import {
  buildUpgradePlanPath,
  extractGoogleDocId,
  formatGoogleDocRescanSchedule,
  isSupportedGoogleDocUrl,
  readAllowedInt,
  readAllowedValue,
  readPositiveInt,
} from "./helpers/importWordsPageHelpers";
import { useLiveImportRows } from "./hooks/useLiveImportRows";
import { useSettings } from "../settings/api/settingsApi";
import { useClientI18n } from "../../shared/i18n/clientI18n";

const IMPORT_PAGE_MAX_WIDTH = 1280;
const IMPORT_SOURCE_MAX_WIDTH = 980;

export function ImportWordsPage() {
  const { locale, t } = useClientI18n();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [sourceUrl, setSourceUrl] = useState("");
  const [clientError, setClientError] = useState("");
  const [importRunId, setImportRunId] = useState(0);
  const [isUnbindConfirmOpen, setUnbindConfirmOpen] = useState(false);
  const [isShareHelpOpen, setShareHelpOpen] = useState(false);
  const [isFormatHelpOpen, setFormatHelpOpen] = useState(false);
  const submitImport = useSubmitImportWords();
  const unbindGoogleDoc = useUnbindImportGoogleDoc();
  const settingsQuery = useSettings();
  const profile = settingsQuery.data?.profile || {};
  const importMode = settingsQuery.data?.subscription?.import_mode || "";
  const showsLookupOnlyNotice = importMode === "lookup_only";
  const showsPaidRescanNotice = importMode === "ai_new_words" && Boolean(settingsQuery.data?.google_doc_post_upgrade_rescan_pending);
  const rescanScheduleText = formatGoogleDocRescanSchedule(settingsQuery.data?.google_doc_rescan_schedule, t);
  const profileGoogleDocId = profile.import_google_doc_id ? String(profile.import_google_doc_id) : "";
  const [optimisticGoogleDocId, setOptimisticGoogleDocId] = useState("");
  const boundGoogleDocId = profileGoogleDocId || optimisticGoogleDocId;
  const page = readPositiveInt(searchParams.get("page")) || 1;
  const pageSize = readAllowedInt(searchParams.get("page_size"), RESULT_PAGE_SIZE_OPTIONS) || RESULT_PAGE_SIZE;
  const statusCategory = readAllowedValue(searchParams.get("status_category"), RESULT_STATUS_FILTERS) || "all";
  const activeJobId = readPositiveInt(searchParams.get("job_id"));
  const itemsQuery = useImportItems(page, pageSize, statusCategory, !activeJobId);
  const jobItemsQuery = useImportJobItems(activeJobId, page, pageSize, statusCategory);
  useImportJobEvents(activeJobId);
  const activeItemsQuery = activeJobId ? jobItemsQuery : itemsQuery;
  const currentResults = activeItemsQuery.data || null;
  const sourceRows = useMemo(
    () => currentResults?.items || [],
    [currentResults?.items],
  );
  const totalRows = Number(currentResults?.total ?? 0);
  const liveRows = useLiveImportRows({
    sourceRows,
    jobKey: `imports:${importRunId}`,
    viewKey: `imports:${page}:${pageSize}:${statusCategory}`,
    pageSize,
    isPlaceholderData: activeItemsQuery.isPlaceholderData,
  });
  const resultSummary = submitImport.isPending ? null : currentResults?.summary || null;
  const activeQueryError = activeJobId ? jobItemsQuery.error?.message : itemsQuery.error?.message;
  const activeError = clientError || submitImport.error?.message || activeQueryError || "";
  const hasSource = Boolean(sourceUrl.trim());
  const canSubmit = !boundGoogleDocId && hasSource && !submitImport.isPending;
  const upgradePlanPath = buildUpgradePlanPath(location);

  useEffect(() => {
    if (profileGoogleDocId) {
      setOptimisticGoogleDocId("");
      setSourceUrl("");
    }
  }, [profileGoogleDocId]);

  useEffect(() => {
    if (!activeJobId || jobItemsQuery.error?.message !== "Import job not found") return;
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.delete("job_id");
      return next;
    });
  }, [activeJobId, jobItemsQuery.error?.message, setSearchParams]);

  function updateResultParams(updates) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      if (activeJobId) next.set("job_id", String(activeJobId));
      else next.delete("job_id");
      next.set("page", String(updates.page ?? page));
      next.set("page_size", String(updates.pageSize ?? pageSize));
      next.set("status_category", updates.statusCategory ?? statusCategory);
      return next;
    });
  }

  function unbindBoundGoogleDoc() {
    setClientError("");
    setOptimisticGoogleDocId("");
    setUnbindConfirmOpen(false);
    unbindGoogleDoc.mutate();
  }

  function submit() {
    setClientError("");
    const hasUrl = Boolean(sourceUrl.trim());
    if (!hasUrl) {
      setClientError(t("importWordsGoogleDocOnly"));
      return;
    }
    if (hasUrl && !isSupportedGoogleDocUrl(sourceUrl)) {
      setClientError(t("importWordsGoogleDocOnly"));
      return;
    }
    const submittedSourceUrl = sourceUrl.trim();
    setOptimisticGoogleDocId(extractGoogleDocId(submittedSourceUrl));
    submitImport.reset();
    setSearchParams({});
    setImportRunId((current) => current + 1);
    submitImport.mutate(
      {
        source_url: hasUrl ? submittedSourceUrl : null,
        text_content: null,
        file_name: null,
      },
      {
        onSuccess: (data) => {
          setSearchParams({
            job_id: String(data.job.id),
            page: "1",
            page_size: String(pageSize),
            status_category: "all",
          });
        },
        onError: () => {
          setOptimisticGoogleDocId("");
        },
      },
    );
  }

  return (
    <Box
      sx={{
        width: "100%",
        maxWidth: IMPORT_PAGE_MAX_WIDTH,
        mx: "auto",
      }}
    >
      <Stack spacing={2.5}>
        <Typography variant="h5" component="h1" fontWeight={700}>{t("importWordsTitle")}</Typography>
        <Stack spacing={2}>
          <Paper variant="outlined" sx={{ p: { xs: 2, sm: 3 }, borderColor: "divider" }}>
            <Box sx={{ width: "100%", maxWidth: IMPORT_SOURCE_MAX_WIDTH, mx: "auto" }}>
              <Stack spacing={2}>
                <GoogleDocBindingGuide
                  t={t}
                  scheduleText={rescanScheduleText}
                  onOpenShareHelp={() => setShareHelpOpen(true)}
                  onOpenFormatHelp={() => setFormatHelpOpen(true)}
                />
                {boundGoogleDocId ? (
                  <BoundGoogleDocPanel
                    t={t}
                    docId={boundGoogleDocId}
                    disabled={submitImport.isPending || unbindGoogleDoc.isPending}
                    onUnbind={() => setUnbindConfirmOpen(true)}
                  />
                ) : (
                  <TextField
                    label={t("importWordsGoogleDocUrl")}
                    value={sourceUrl}
                    onChange={(event) => setSourceUrl(event.target.value)}
                    disabled={submitImport.isPending}
                    slotProps={{
                      input: {
                        startAdornment: (
                          <InputAdornment position="start">
                            <LinkIcon size={18} />
                          </InputAdornment>
                        ),
                      },
                    }}
                    fullWidth
                  />
                )}
                {activeError && <Alert severity="error">{activeError}</Alert>}
                {unbindGoogleDoc.error?.message && <Alert severity="error">{unbindGoogleDoc.error.message}</Alert>}
                <Button
                  variant="contained"
                  size="large"
                  startIcon={submitImport.isPending ? <CircularProgress color="inherit" size={18} /> : <Upload size={18} />}
                  disabled={!canSubmit}
                  onClick={submit}
                >
                  {submitImport.isPending ? t("importWordsImporting") : t("importWordsSubmit")}
                </Button>
                {showsLookupOnlyNotice && (
                  <Alert
                    severity="info"
                    sx={{ alignItems: "flex-start" }}
                  >
                    {t("importWordsLookupOnlyNoticeBefore", { schedule: rescanScheduleText })}{" "}
                    <Button
                      component={RouterLink}
                      to={upgradePlanPath}
                      variant="contained"
                      size="small"
                      sx={{ minHeight: 0, px: 1, py: 0.25, mx: 0.25, verticalAlign: "baseline" }}
                    >
                      {t("importWordsUpgradePlanLink")}
                    </Button>
                    {t("importWordsLookupOnlyNoticeAfter")}
                  </Alert>
                )}
                {showsPaidRescanNotice && (
                  <Alert severity="info" sx={{ alignItems: "flex-start" }}>
                    {t("importWordsPaidRescanPendingNotice")}
                  </Alert>
                )}
              </Stack>
            </Box>
          </Paper>

        <ImportResultTable
          t={t}
          rows={liveRows.rows}
          total={totalRows}
          page={page}
          pageSize={pageSize}
          loading={submitImport.isPending || activeItemsQuery.isPending || activeItemsQuery.isPlaceholderData}
          summary={resultSummary}
          statusCategory={statusCategory}
          showSummary={!submitImport.isPending && totalRows > 0}
          resolvingIds={liveRows.resolvingIds}
          newRowIds={liveRows.newRowIds}
          onPageChange={(nextPage) => updateResultParams({ page: nextPage })}
          onPageSizeChange={(nextPageSize) => updateResultParams({ page: 1, pageSize: nextPageSize })}
          onStatusCategoryChange={(nextStatusCategory) => updateResultParams({ page: 1, statusCategory: nextStatusCategory })}
        />
        </Stack>
      </Stack>
      <Dialog
        open={isUnbindConfirmOpen}
        onClose={() => {
          if (!unbindGoogleDoc.isPending) setUnbindConfirmOpen(false);
        }}
      >
        <DialogTitle>{t("importWordsUnbindConfirmTitle")}</DialogTitle>
        <DialogContent>
          <DialogContentText>{t("importWordsUnbindConfirmMessage")}</DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            disabled={unbindGoogleDoc.isPending}
            onClick={() => setUnbindConfirmOpen(false)}
          >
            {t("cancel")}
          </Button>
          <Button
            color="error"
            disabled={unbindGoogleDoc.isPending}
            onClick={unbindBoundGoogleDoc}
            variant="contained"
          >
            {t("importWordsUnbindConfirmAction")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={isShareHelpOpen}
        onClose={() => setShareHelpOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>{t("importWordsShareHelpTitle")}</DialogTitle>
        <DialogContent>
          <List dense disablePadding>
            {[
              t("importWordsShareHelpStepOpen"),
              t("importWordsShareHelpStepGeneralAccess"),
              t("importWordsShareHelpStepRole"),
              t("importWordsShareHelpStepCopy"),
            ].map((step, index) => (
              <ListItem key={step} disableGutters sx={{ alignItems: "flex-start" }}>
                <Typography variant="body2">
                  {`${index + 1}. `}
                  <HighlightedInstructionText text={step} highlights={shareHelpHighlights(locale)} />
                </Typography>
              </ListItem>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShareHelpOpen(false)}>{t("close")}</Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={isFormatHelpOpen}
        onClose={() => setFormatHelpOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>{t("importWordsFormatHelpTitle")}</DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            <Typography variant="body2" color="text.secondary">
              {t("importWordsFormatHelpDescription")}
            </Typography>
            <Stack spacing={1.25}>
              {[
                ["importWordsFormatSingleLineTitle", "importWordsFormatSingleLineExamples"],
                ["importWordsFormatCommaTitle", "importWordsFormatCommaExamples"],
                ["importWordsFormatTranslationTitle", "importWordsFormatTranslationExamples"],
                ["importWordsFormatNumberedTitle", "importWordsFormatNumberedExamples"],
              ].map(([titleKey, examplesKey]) => (
                <Box key={titleKey}>
                  <Typography variant="subtitle2" fontWeight={700} gutterBottom>
                    {t(titleKey)}
                  </Typography>
                  <Box component="pre" sx={{ m: 0, p: 1.5, borderRadius: 1, bgcolor: "background.default", overflowX: "auto", fontFamily: "monospace", fontSize: "0.875rem" }}>
                    {t(examplesKey)}
                  </Box>
                </Box>
              ))}
            </Stack>
            <Typography variant="body2" color="text.secondary">
              {t("importWordsFormatHelpTranslationNote")}
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFormatHelpOpen(false)}>{t("close")}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

function GoogleDocBindingGuide({ t, scheduleText, onOpenShareHelp, onOpenFormatHelp }) {
  const steps = [
    t("importWordsGuideStepCreate"),
    t("importWordsGuideStepShare"),
    t("importWordsGuideStepCopy"),
    t("importWordsGuideStepPaste"),
  ];
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 1.5,
        borderColor: "divider",
        bgcolor: "background.default",
      }}
    >
      <Stack spacing={1.25}>
        <Typography variant="subtitle2" fontWeight={700}>
          {t("importWordsGuideTitle")}
        </Typography>
        <List dense disablePadding>
          {steps.map((step, index) => (
            <ListItem key={step} disableGutters sx={{ alignItems: "flex-start", py: 0.25 }}>
              <Typography variant="body2">
                {index === 1 ? (
                  <>
                    {`${index + 1}. ${step} `}
                    <HelpLink onClick={onOpenShareHelp}>
                      {t("importWordsShareHelpLink")}
                    </HelpLink>
                  </>
                ) : (
                  `${index + 1}. ${step}`
                )}
              </Typography>
            </ListItem>
          ))}
        </List>
        <Typography variant="body2" color="text.secondary">
          {t("importWordsGuideSchedule", { schedule: scheduleText })}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {t("importWordsGuideFormat")}{" "}
          <HelpLink onClick={onOpenFormatHelp}>
            {t("importWordsFormatHelpLink")}
          </HelpLink>
        </Typography>
      </Stack>
    </Paper>
  );
}

function HelpLink({ children, onClick }) {
  const handleClick = (event) => {
    event.preventDefault();
    onClick();
  };

  return (
    <Link
      component="a"
      href="#"
      variant="body2"
      underline="hover"
      onClick={handleClick}
      sx={{
        display: "inline",
        color: "primary.main",
        font: "inherit",
        fontWeight: 600,
        lineHeight: "inherit",
        verticalAlign: "baseline",
      }}
    >
      {children}
    </Link>
  );
}

function HighlightedInstructionText({ text, highlights }) {
  const parts = splitHighlightedText(text, highlights);
  return parts.map((part, index) => (
    part.highlighted ? (
      <Box key={`${part.text}-${index}`} component="strong" sx={{ fontWeight: 700 }}>
        {part.text}
      </Box>
    ) : (
      part.text
    )
  ));
}

function splitHighlightedText(text, highlights) {
  const source = String(text || "");
  const matches = highlights
    .map((highlight) => {
      const index = source.indexOf(highlight);
      return index >= 0 ? { index, end: index + highlight.length, text: highlight } : null;
    })
    .filter(Boolean)
    .sort((left, right) => left.index - right.index);
  if (matches.length === 0) {
    return [{ text: source, highlighted: false }];
  }
  const parts = [];
  let cursor = 0;
  matches.forEach((match) => {
    if (match.index < cursor) return;
    if (match.index > cursor) {
      parts.push({ text: source.slice(cursor, match.index), highlighted: false });
    }
    parts.push({ text: source.slice(match.index, match.end), highlighted: true });
    cursor = match.end;
  });
  if (cursor < source.length) {
    parts.push({ text: source.slice(cursor), highlighted: false });
  }
  return parts;
}

function shareHelpHighlights(locale) {
  const byLocale = {
    uk: ['"Поділитися"', '"Усі, хто має посилання"', '"Читач"'],
    ru: ['"Поделиться"', '"Все, у кого есть ссылка"', '"Читатель"'],
    pl: ['"Udostepnij"', '"Wszyscy majacy link"', '"Czytelnik"'],
  };
  return byLocale[locale] || byLocale.uk;
}

export { buildUpgradePlanPath };
