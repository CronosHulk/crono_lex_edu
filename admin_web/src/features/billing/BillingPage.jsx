import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Typography } from "@mui/material";

import {
  ActionRow,
  CrudPage,
  DetailGrid,
  DetailPanel,
  EmptyState,
  EntityLinksFromJson,
  FilterBar,
  InlineDetailBlock,
  InlineDetailGrid,
  JsonPreview,
  LinkButton,
  ListCard,
  LoadingLine,
  LogField,
  LogToolbar,
  MultiSelect,
  Pager,
  PreLine,
  SideMeta,
  TitleRow,
} from "../../shared/components";
import {
  fetchTaskLogFilters,
  fetchTaskLogs,
  logsQueryKeys,
} from "../logs/api/logsApi";
import {
  billingQueryKeys,
  fetchBillingPaymentDetail,
  fetchBillingPayments,
  fetchMonobankAuditDetail,
  fetchMonobankAuditLogs,
} from "./api/billingApi";
import { BillingSettingsPanel } from "./components/BillingSettingsPanel";
import {
  applyBillingPaymentsParamUpdates,
  applyBillingTaskLogsParamUpdates,
  applyMonobankAuditParamUpdates,
  billingPaymentsParamsFromSearch,
  billingTaskLogsParamsFromSearch,
  monobankAuditParamsFromSearch,
} from "./helpers/listParams";

const PAYMENT_STATUS_OPTIONS = ["created", "invoice_created", "processing", "success", "failure", "expired", "reversed"].map(
  option,
);
const PAYMENT_MODE_OPTIONS = ["test", "production"].map(option);
const AUDIT_MODE_OPTIONS = ["test", "production", "unknown"].map(option);
const AUDIT_DIRECTION_OPTIONS = ["outgoing", "incoming"].map(option);

export function BillingPage({ t, user, section = "payments", onOpenUser, onOpenTaskLog, onSettingsUpdate }) {
  const [searchParams, setSearchParams] = useSearchParams();

  return (
    <CrudPage
      title={t.billing || "Биллинг"}
      breadcrumbs={[{ title: "CronoLex", path: "/admin" }, { title: t.billing || "Биллинг" }]}
    >
      {section === "settings" ? (
        <BillingSettingsPanel t={t} user={user} onSettingsUpdate={onSettingsUpdate} />
      ) : section === "payments" ? (
        <BillingPaymentsTab t={t} searchParams={searchParams} setSearchParams={setSearchParams} onOpenUser={onOpenUser} />
      ) : section === "monobank_audit" ? (
        <MonobankAuditTab t={t} searchParams={searchParams} setSearchParams={setSearchParams} onOpenUser={onOpenUser} />
      ) : (
        <BillingTaskLogsTab t={t} user={user} searchParams={searchParams} setSearchParams={setSearchParams} onOpenUser={onOpenUser} onOpenTaskLog={onOpenTaskLog} />
      )}
    </CrudPage>
  );
}

function BillingPaymentsTab({ t, searchParams, setSearchParams, onOpenUser }) {
  const params = useMemo(() => billingPaymentsParamsFromSearch(searchParams), [searchParams]);
  const [paymentId, setPaymentId] = useState(null);
  const query = useQuery({
    queryKey: billingQueryKeys.paymentList(params),
    queryFn: () => fetchBillingPayments(params),
  });
  const items = query.data?.items || [];
  const error = query.error?.message || "";

  function updateParams(updates) {
    setSearchParams((current) => applyBillingPaymentsParamUpdates(current, updates));
  }

  return (
    <>
      <FilterBar>
        <LogToolbar t={t} search={params.search} onSearch={(search) => updateParams({ search, page: 1 })} />
        <MultiSelect label={t.status} options={PAYMENT_STATUS_OPTIONS} value={params.statuses} onChange={(statuses) => updateParams({ statuses, page: 1 })} />
        <MultiSelect label={t.monobankMode || "Mono mode"} options={PAYMENT_MODE_OPTIONS} value={params.providerModes} onChange={(providerModes) => updateParams({ providerModes, page: 1 })} />
      </FilterBar>
      {error && <Alert severity="error">{error}</Alert>}
      <Stack spacing={1.5}>
        {!error && items.length === 0 && !query.isFetching && <EmptyState text={t.emptyLogs} />}
        {items.map((item) => (
          <ListCard key={item.id}>
            <Box sx={{ minWidth: 0 }}>
              <TitleRow label={item.status} title={`${item.plan_key} · ${item.period_months} ${t.monthsShort || "мес."}`} trailing={formatAmount(item.amount_minor, item.currency)} />
              <Typography variant="body2" color="text.secondary">
                ID: {item.id} · {item.provider_mode} · {item.provider_reference}
              </Typography>
              <ActionRow>
                <LinkButton onClick={() => setPaymentId(item.id)}>{t.showDetails || "Детали"}</LinkButton>
                {item.user_uuid && <LinkButton onClick={() => onOpenUser?.(item.user_uuid)}>{t.openUser}</LinkButton>}
              </ActionRow>
              {item.provider_invoice_id && <PreLine>{item.provider_invoice_id}</PreLine>}
              {item.failure_reason && <Alert severity="error" sx={{ mt: 1 }}>{item.failure_reason}</Alert>}
            </Box>
            <SideMeta>
              <LogField layout="inline" label={t.user || "User"} value={item.telegram_user_id || item.user_uuid} />
              <LogField layout="inline" label={t.created || t.date} value={item.created} />
              <LogField layout="inline" label={t.updated || "Updated"} value={item.updated} />
              <LogField layout="inline" label={t.paidAt || "Paid"} value={item.paid_at} />
            </SideMeta>
          </ListCard>
        ))}
        {query.isFetching && <LoadingLine text={t.loading} />}
      </Stack>
      <Pager page={params.page} pageSize={params.pageSize} total={query.data?.total || 0} onPageChange={(page) => updateParams({ page })} onPageSizeChange={(pageSize) => updateParams({ pageSize, page: 1 })} />
      <PaymentDetailDialog paymentId={paymentId} t={t} onClose={() => setPaymentId(null)} onOpenUser={onOpenUser} />
    </>
  );
}

function MonobankAuditTab({ t, searchParams, setSearchParams, onOpenUser }) {
  const params = useMemo(() => monobankAuditParamsFromSearch(searchParams), [searchParams]);
  const [auditLogId, setAuditLogId] = useState(null);
  const query = useQuery({
    queryKey: billingQueryKeys.monobankAuditList(params),
    queryFn: () => fetchMonobankAuditLogs(params),
  });
  const items = query.data?.items || [];
  const error = query.error?.message || "";

  function updateParams(updates) {
    setSearchParams((current) => applyMonobankAuditParamUpdates(current, updates));
  }

  return (
    <>
      <FilterBar>
        <LogToolbar t={t} search={params.search} onSearch={(search) => updateParams({ search, page: 1 })} />
        <MultiSelect label={t.direction || "Direction"} options={AUDIT_DIRECTION_OPTIONS} value={params.directions} onChange={(directions) => updateParams({ directions, page: 1 })} />
        <MultiSelect label={t.monobankMode || "Mono mode"} options={AUDIT_MODE_OPTIONS} value={params.providerModes} onChange={(providerModes) => updateParams({ providerModes, page: 1 })} />
      </FilterBar>
      {error && <Alert severity="error">{error}</Alert>}
      <Stack spacing={1.5}>
        {!error && items.length === 0 && !query.isFetching && <EmptyState text={t.emptyLogs} />}
        {items.map((item) => (
          <ListCard key={item.id}>
            <Box sx={{ minWidth: 0 }}>
              <TitleRow label={item.direction} title={`${item.request_method || "-"} ${item.source_place}`} trailing={item.processing_result || item.response_status_code || "-"} />
              <Typography variant="body2" color="text.secondary">
                ID: {item.id} · {item.provider_mode}{item.payment_id ? ` · payment #${item.payment_id}` : ""}{item.invoice_id ? ` · ${item.invoice_id}` : ""}
              </Typography>
              <ActionRow>
                <LinkButton onClick={() => setAuditLogId(item.id)}>{t.showDetails || "Детали"}</LinkButton>
                {item.actor_user_uuid && <LinkButton onClick={() => onOpenUser?.(item.actor_user_uuid)}>{t.openUser}</LinkButton>}
              </ActionRow>
              {item.error_text && <Alert severity="error" sx={{ mt: 1 }}>{item.error_text}</Alert>}
            </Box>
            <SideMeta>
              <LogField layout="inline" label={t.status} value={item.response_status_code} />
              <LogField layout="inline" label="IP" value={item.request_ip} />
              <LogField layout="inline" label={t.started} value={item.started} />
              <LogField layout="inline" label={t.finished} value={item.finished} />
            </SideMeta>
          </ListCard>
        ))}
        {query.isFetching && <LoadingLine text={t.loading} />}
      </Stack>
      <Pager page={params.page} pageSize={params.pageSize} total={query.data?.total || 0} onPageChange={(page) => updateParams({ page })} onPageSizeChange={(pageSize) => updateParams({ pageSize, page: 1 })} />
      <AuditDetailDialog auditLogId={auditLogId} t={t} onClose={() => setAuditLogId(null)} />
    </>
  );
}

function BillingTaskLogsTab({ t, user, searchParams, setSearchParams, onOpenUser, onOpenTaskLog }) {
  const params = useMemo(() => ({ ...billingTaskLogsParamsFromSearch(searchParams), scope: "billing" }), [searchParams]);
  const filtersQuery = useQuery({
    queryKey: logsQueryKeys.taskLogFilters("billing"),
    queryFn: () => fetchTaskLogFilters("billing"),
  });
  const query = useQuery({
    queryKey: logsQueryKeys.taskLogList(params),
    queryFn: () => fetchTaskLogs(params),
  });
  const filters = filtersQuery.data || null;
  const items = query.data?.items || [];
  const error = query.error?.message || "";

  function updateParams(updates) {
    setSearchParams((current) => applyBillingTaskLogsParamUpdates(current, updates));
  }

  return (
    <>
      <FilterBar>
        <LogToolbar t={t} search={params.search} onSearch={(search) => updateParams({ search, page: 1 })} />
        <MultiSelect label={t.taskType || "Task type"} options={filters?.filters?.find((item) => item.name === "task_type")?.options || []} value={params.taskTypes} onChange={(taskTypes) => updateParams({ taskTypes, page: 1 })} />
        <MultiSelect label={t.status} options={filters?.filters?.find((item) => item.name === "status")?.options || []} value={params.statuses} onChange={(statuses) => updateParams({ statuses, page: 1 })} />
      </FilterBar>
      {error && <Alert severity="error">{error}</Alert>}
      <Stack spacing={1.5}>
        {!error && items.length === 0 && !query.isFetching && <EmptyState text={t.emptyLogs} />}
        {items.map((item) => (
          <ListCard key={item.id}>
            <Box sx={{ minWidth: 0 }}>
              <TitleRow label={item.status} title={item.task_type} />
              <Typography variant="body2" color="text.secondary">
                ID: {item.id}{item.user_id ? ` · User: ${item.user_id}` : ""}
              </Typography>
              <ActionRow>
                <LinkButton onClick={() => onOpenTaskLog?.(item.id)}>{t.openTaskLog}</LinkButton>
                {item.user_id && <LinkButton onClick={() => onOpenUser?.(item.user_id)}>{t.openUser}</LinkButton>}
              </ActionRow>
              <InlineDetailGrid>
                <InlineDetailBlock title={t.description}>
                  {item.description ? <PreLine>{item.description}</PreLine> : <Typography color="text.secondary">-</Typography>}
                </InlineDetailBlock>
                <InlineDetailBlock title={t.errorText || "Error"}>
                  {item.error_text ? <Alert severity="error" sx={{ whiteSpace: "pre-line" }}>{item.error_text}</Alert> : <Typography color="text.secondary">-</Typography>}
                </InlineDetailBlock>
                <InlineDetailBlock title={t.context}>
                  <EntityLinksFromJson value={item.result_json} t={t} user={user} taskType={item.task_type} onOpenUser={onOpenUser} onOpenTaskLog={onOpenTaskLog} />
                </InlineDetailBlock>
              </InlineDetailGrid>
            </Box>
            <SideMeta>
              <LogField layout="inline" label={t.source} value={[item.source_type, item.source_identifier].filter(Boolean).join(" · ")} />
              <LogField layout="inline" label={t.started} value={item.started} />
              <LogField layout="inline" label={t.finished} value={item.finished} />
              <LogField layout="inline" label={t.date} value={item.created} />
            </SideMeta>
          </ListCard>
        ))}
        {query.isFetching && <LoadingLine text={t.loading} />}
      </Stack>
      <Pager page={params.page} pageSize={params.pageSize} total={query.data?.total || 0} onPageChange={(page) => updateParams({ page })} onPageSizeChange={(pageSize) => updateParams({ pageSize, page: 1 })} />
    </>
  );
}

function PaymentDetailDialog({ paymentId, t, onClose, onOpenUser }) {
  const query = useQuery({
    queryKey: billingQueryKeys.paymentDetail(paymentId),
    queryFn: () => fetchBillingPaymentDetail(paymentId),
    enabled: Boolean(paymentId),
  });
  const data = query.data || {};
  const payment = data.payment || {};

  return (
    <Dialog open={Boolean(paymentId)} onClose={onClose} fullWidth maxWidth="lg">
      <DialogTitle>{t.billingPaymentDetail || "Детали платежа"} #{paymentId}</DialogTitle>
      <DialogContent dividers>
        {query.error && <Alert severity="error">{query.error.message || t.loadError}</Alert>}
        {query.isFetching && <LoadingLine text={t.loading} />}
        {query.data && (
          <Stack spacing={2}>
            <DetailGrid>
              <DetailPanel title={t.billingPayment || "Платеж"}>
                <LogField label="ID" value={payment.id} />
                <LogField label={t.status} value={payment.status} />
                <LogField label={t.plan || "Plan"} value={payment.plan_key} />
                <LogField label={t.billingPeriod || "Period"} value={payment.period_months} />
                <LogField label={t.amount || "Amount"} value={formatAmount(payment.amount_minor, payment.currency)} />
                <LogField label={t.source || "Source"} value={payment.source_path} />
              </DetailPanel>
              <DetailPanel title="Monobank">
                <LogField label={t.monobankMode || "Mono mode"} value={payment.provider_mode} />
                <LogField label="Invoice" value={payment.provider_invoice_id} />
                <LogField label="Reference" value={payment.provider_reference} />
                <LogField label="Checkout" value={payment.checkout_url} />
              </DetailPanel>
              <DetailPanel title={t.context}>
                <LogField label="User UUID" value={payment.user_uuid} />
                {payment.user_uuid && <LinkButton onClick={() => onOpenUser?.(payment.user_uuid)}>{t.openUser}</LinkButton>}
                <LogField label="Telegram" value={payment.telegram_user_id} />
                <LogField label={t.created || t.date} value={payment.created} />
                <LogField label={t.updated || "Updated"} value={payment.updated} />
              </DetailPanel>
            </DetailGrid>
            {payment.failure_reason && <Alert severity="error">{payment.failure_reason}</Alert>}
            <JsonPreview title="Provider status" value={payment.provider_status_json} />
            <JsonPreview title={t.events || "Events"} value={data.events || []} />
            <JsonPreview title={t.receipts || "Receipts"} value={data.receipts || []} />
            <JsonPreview title={t.billingBotNotifications || "Bot notifications"} value={data.bot_notifications || []} />
            <JsonPreview title={t.billingOfferAcceptances || "Offer acceptances"} value={data.offer_acceptances || []} />
            <JsonPreview title={t.monobankAudit || "Monobank audit"} value={data.monobank_audit_logs || []} />
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t.close || "Закрыть"}</Button>
      </DialogActions>
    </Dialog>
  );
}

function AuditDetailDialog({ auditLogId, t, onClose }) {
  const query = useQuery({
    queryKey: billingQueryKeys.monobankAuditDetail(auditLogId),
    queryFn: () => fetchMonobankAuditDetail(auditLogId),
    enabled: Boolean(auditLogId),
  });
  const auditLog = query.data?.audit_log || {};

  return (
    <Dialog open={Boolean(auditLogId)} onClose={onClose} fullWidth maxWidth="lg">
      <DialogTitle>{t.monobankAuditDetail || "Monobank audit"} #{auditLogId}</DialogTitle>
      <DialogContent dividers>
        {query.error && <Alert severity="error">{query.error.message || t.loadError}</Alert>}
        {query.isFetching && <LoadingLine text={t.loading} />}
        {query.data && (
          <Stack spacing={2}>
            <DetailGrid>
              <DetailPanel title={t.request || "Request"}>
                <LogField label={t.direction || "Direction"} value={auditLog.direction} />
                <LogField label={t.source || "Source"} value={auditLog.source_place} />
                <LogField label="Method" value={auditLog.request_method} />
                <LogField label="URL" value={auditLog.request_url} />
                <LogField label="IP" value={auditLog.request_ip} />
              </DetailPanel>
              <DetailPanel title={t.response || "Response"}>
                <LogField label={t.status} value={auditLog.response_status_code} />
                <LogField label={t.result || "Result"} value={auditLog.processing_result} />
                <LogField label={t.signature || "Signature"} value={String(auditLog.signature_valid)} />
                <LogField label={t.duration || "Duration"} value={auditLog.duration_ms} />
              </DetailPanel>
              <DetailPanel title={t.context}>
                <LogField label="Payment" value={auditLog.payment_id} />
                <LogField label="Order" value={auditLog.order_reference} />
                <LogField label="Invoice" value={auditLog.invoice_id} />
                <LogField label="User" value={auditLog.telegram_user_id || auditLog.actor_user_uuid} />
              </DetailPanel>
            </DetailGrid>
            {auditLog.error_text && <Alert severity="error">{auditLog.error_text}</Alert>}
            <JsonPreview title="Request headers" value={auditLog.request_headers_json} />
            <JsonPreview title="Request body" value={auditLog.request_body_json || auditLog.request_raw_body} />
            <JsonPreview title="Response headers" value={auditLog.response_headers_json} />
            <JsonPreview title="Response body" value={auditLog.response_body_json || auditLog.response_raw_body} />
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t.close || "Закрыть"}</Button>
      </DialogActions>
    </Dialog>
  );
}

function option(value) {
  return { value, label: value };
}

function formatAmount(amountMinor, currency) {
  if (amountMinor === null || amountMinor === undefined) return "-";
  const suffix = Number(currency) === 980 ? "UAH" : String(currency || "");
  return `${(Number(amountMinor) / 100).toFixed(2)} ${suffix}`.trim();
}
