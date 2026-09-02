'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ClipboardCheck, RefreshCw } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import {
  adminRemnawaveConnectionsApi,
  type AdminRemnawaveConnectionDropReconciliationRequest,
  type RemnawaveConnectionDropReconciliationReason,
} from '@/lib/api/remnawave-connections';

const PAGE_SIZE = 25;
const RECONCILIATION_REFERENCE_PATTERN = /^(?:CASE|INC|REQ|TKT|RW)-[A-Z0-9][A-Z0-9_-]{5,58}$/;
const UNRESOLVED_RECEIPTS_QUERY_KEY = [
  'infrastructure',
  'remnawave',
  'connections',
  'drop-receipts',
  'unresolved',
] as const;

type TerminalOutcome = AdminRemnawaveConnectionDropReconciliationRequest['outcome'];

const COMPATIBLE_REASONS: Record<
  TerminalOutcome,
  readonly RemnawaveConnectionDropReconciliationReason[]
> = {
  accepted: [
    'provider_confirmed_applied',
    'postcondition_confirmed_applied',
  ],
  rejected: [
    'provider_confirmed_not_applied',
    'postcondition_confirmed_not_applied',
  ],
};

function errorStatus(error: unknown): number | null {
  if (typeof error !== 'object' || error === null) return null;
  const response = (error as { response?: { status?: unknown } }).response;
  return typeof response?.status === 'number' ? response.status : null;
}

function errorKey(error: unknown): string {
  const status = errorStatus(error);
  if (status === 404) return 'reconciliation.errors.notFound';
  if (status === 409) return 'reconciliation.errors.conflict';
  if (status === 503) return 'reconciliation.errors.unavailable';
  return 'reconciliation.errors.generic';
}

function formatTimestamp(value: string, locale: string): string {
  try {
    return new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
      timeStyle: 'medium',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function RemnawaveConnectionReconciliationQueue() {
  const t = useTranslations('Infrastructure.remnawaveConnections');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [cursor, setCursor] = useState<string | null>(null);
  const [cursorHistory, setCursorHistory] = useState<Array<string | null>>([]);
  const [selectedReceiptId, setSelectedReceiptId] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<TerminalOutcome>('accepted');
  const [reason, setReason] = useState<RemnawaveConnectionDropReconciliationReason>(
    'provider_confirmed_applied',
  );
  const [reference, setReference] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [validationError, setValidationError] = useState(false);

  const receiptsQuery = useQuery({
    queryKey: [...UNRESOLVED_RECEIPTS_QUERY_KEY, cursor],
    queryFn: () => adminRemnawaveConnectionsApi.listUnresolvedDropReceipts({
      limit: PAGE_SIZE,
      cursor,
    }),
    retry: false,
  });

  const reconciliationMutation = useMutation({
    mutationFn: ({
      receiptId,
      body,
    }: {
      receiptId: string;
      body: AdminRemnawaveConnectionDropReconciliationRequest;
    }) => adminRemnawaveConnectionsApi.reconcileDropReceipt(receiptId, body),
    retry: false,
    onSuccess: async () => {
      setSelectedReceiptId(null);
      setReference('');
      setConfirmed(false);
      setValidationError(false);
      await queryClient.invalidateQueries({ queryKey: UNRESOLVED_RECEIPTS_QUERY_KEY });
    },
  });

  const selectedReceipt = receiptsQuery.data?.items.find(
    (item) => item.receipt_id === selectedReceiptId,
  ) ?? null;
  const compatibleReasons = COMPATIBLE_REASONS[outcome];
  const referenceIsValid = RECONCILIATION_REFERENCE_PATTERN.test(reference);

  function resetFormState() {
    setSelectedReceiptId(null);
    setOutcome('accepted');
    setReason('provider_confirmed_applied');
    setReference('');
    setConfirmed(false);
    setValidationError(false);
    reconciliationMutation.reset();
  }

  function selectReceipt(receiptId: string) {
    resetFormState();
    setSelectedReceiptId(receiptId);
  }

  function refreshQueue() {
    resetFormState();
    void receiptsQuery.refetch();
  }

  function chooseOutcome(nextOutcome: TerminalOutcome) {
    setOutcome(nextOutcome);
    setReason(COMPATIBLE_REASONS[nextOutcome][0]);
    setValidationError(false);
  }

  function goToNextPage() {
    const nextCursor = receiptsQuery.data?.next_cursor ?? null;
    if (nextCursor === null || receiptsQuery.isFetching) return;
    setCursorHistory((history) => [...history, cursor]);
    setCursor(nextCursor);
    resetFormState();
  }

  function goToPreviousPage() {
    if (cursorHistory.length === 0 || receiptsQuery.isFetching) return;
    setCursor(cursorHistory[cursorHistory.length - 1] ?? null);
    setCursorHistory((history) => history.slice(0, -1));
    resetFormState();
  }

  function submitReconciliation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      selectedReceipt === null
      || !referenceIsValid
      || !confirmed
      || !compatibleReasons.includes(reason)
    ) {
      setValidationError(true);
      return;
    }
    setValidationError(false);
    reconciliationMutation.mutate({
      receiptId: selectedReceipt.receipt_id,
      body: { outcome, reason, reference },
    });
  }

  const sectionClass = 'rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/70 p-5 md:p-6';
  const inputClass = 'mt-2 min-h-11 w-full rounded-xl border border-grid-line/30 bg-terminal-surface/70 px-3 py-2 font-mono text-sm text-white outline-none focus:border-neon-cyan focus-visible:ring-2 focus-visible:ring-neon-cyan/30';
  const actionClass = 'inline-flex min-h-11 items-center justify-center rounded-xl border border-neon-cyan/40 bg-neon-cyan/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.12em] text-neon-cyan transition-colors hover:bg-neon-cyan/15 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-neon-cyan disabled:cursor-not-allowed disabled:opacity-45';

  return (
    <section className={sectionClass} aria-labelledby="remnawave-reconciliation-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex max-w-4xl items-start gap-3">
          <ClipboardCheck className="mt-1 h-5 w-5 shrink-0 text-amber-300" aria-hidden="true" />
          <div>
            <h2 id="remnawave-reconciliation-title" className="font-display text-xl text-white">
              {t('reconciliation.title')}
            </h2>
            <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">
              {t('reconciliation.description')}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={refreshQueue}
          disabled={receiptsQuery.isFetching}
          className={actionClass}
        >
          <RefreshCw
            className={`mr-2 h-4 w-4 ${receiptsQuery.isFetching ? 'animate-spin' : ''}`}
            aria-hidden="true"
          />
          {t('reconciliation.actions.refresh')}
        </button>
      </div>

      <div className="mt-5" aria-live="polite">
        {receiptsQuery.isPending ? (
          <p role="status" className="font-mono text-sm text-neon-cyan">
            {t('reconciliation.states.loading')}
          </p>
        ) : receiptsQuery.error ? (
          <div
            role="alert"
            className="rounded-xl border border-neon-pink/30 bg-neon-pink/5 p-4 font-mono text-sm text-neon-pink"
          >
            <p>{t(errorKey(receiptsQuery.error))}</p>
            <button
              type="button"
              onClick={refreshQueue}
              disabled={receiptsQuery.isFetching}
              className={`${actionClass} mt-3`}
            >
              {t('reconciliation.actions.refresh')}
            </button>
          </div>
        ) : receiptsQuery.data.items.length === 0 ? (
          <p role="status" className="font-mono text-sm text-muted-foreground">
            {t('reconciliation.states.empty')}
          </p>
        ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[860px] border-separate border-spacing-y-2 text-left font-mono text-xs">
                <caption className="sr-only">{t('reconciliation.table.caption')}</caption>
                <thead className="text-muted-foreground">
                  <tr>
                    <th scope="col" className="px-3 py-2">{t('reconciliation.table.receipt')}</th>
                    <th scope="col" className="px-3 py-2">{t('reconciliation.table.audience')}</th>
                    <th scope="col" className="px-3 py-2">{t('reconciliation.table.created')}</th>
                    <th scope="col" className="px-3 py-2">{t('reconciliation.table.updated')}</th>
                    <th scope="col" className="px-3 py-2">{t('reconciliation.table.action')}</th>
                  </tr>
                </thead>
                <tbody>
                  {receiptsQuery.data.items.map((receipt) => (
                    <tr key={receipt.receipt_id} className="bg-terminal-bg/45 text-foreground">
                      <td className="max-w-72 break-all rounded-l-xl px-3 py-3">{receipt.receipt_id}</td>
                      <td className="px-3 py-3">{t(`reconciliation.audiences.${receipt.audience}`)}</td>
                      <td className="px-3 py-3">
                        <time dateTime={receipt.created_at}>{formatTimestamp(receipt.created_at, locale)}</time>
                      </td>
                      <td className="px-3 py-3">
                        <time dateTime={receipt.updated_at}>{formatTimestamp(receipt.updated_at, locale)}</time>
                      </td>
                      <td className="rounded-r-xl px-3 py-3">
                        <button
                          type="button"
                          onClick={() => selectReceipt(receipt.receipt_id)}
                          aria-pressed={selectedReceiptId === receipt.receipt_id}
                          className={actionClass}
                        >
                          {t('reconciliation.actions.select')}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
        )}
      </div>

      {receiptsQuery.data ? (
        <nav
          className="mt-4 flex flex-wrap gap-3"
          aria-label={t('reconciliation.pagination.label')}
        >
          <button
            type="button"
            onClick={goToPreviousPage}
            disabled={cursorHistory.length === 0 || receiptsQuery.isFetching}
            className={actionClass}
          >
            {t('reconciliation.actions.previous')}
          </button>
          <button
            type="button"
            onClick={goToNextPage}
            disabled={receiptsQuery.data.next_cursor == null || receiptsQuery.isFetching}
            className={actionClass}
          >
            {t('reconciliation.actions.next')}
          </button>
        </nav>
      ) : null}

      {selectedReceipt ? (
        <form className="mt-6 space-y-5 border-t border-grid-line/20 pt-6" onSubmit={submitReconciliation} noValidate>
          <div>
            <h3 className="font-display text-lg text-white">{t('reconciliation.form.title')}</h3>
            <p className="mt-2 break-all font-mono text-xs text-muted-foreground">
              {selectedReceipt.receipt_id}
            </p>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <label className="font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground">
              {t('reconciliation.form.outcome')}
              <select
                value={outcome}
                onChange={(event) => chooseOutcome(event.target.value as TerminalOutcome)}
                className={inputClass}
              >
                <option value="accepted">{t('reconciliation.form.accepted')}</option>
                <option value="rejected">{t('reconciliation.form.rejected')}</option>
              </select>
            </label>
            <label className="font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground">
              {t('reconciliation.form.reason')}
              <select
                value={reason}
                onChange={(event) => {
                  setReason(event.target.value as RemnawaveConnectionDropReconciliationReason);
                  setValidationError(false);
                }}
                className={inputClass}
              >
                {compatibleReasons.map((reasonOption) => (
                  <option key={reasonOption} value={reasonOption}>
                    {t(`reconciliation.reasons.${reasonOption}`)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div>
            <label
              htmlFor="remnawave-reconciliation-reference"
              className="font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground"
            >
              {t('reconciliation.form.reference')}
            </label>
            <input
              id="remnawave-reconciliation-reference"
              value={reference}
              onChange={(event) => {
                setReference(event.target.value.toUpperCase());
                setValidationError(false);
              }}
              minLength={11}
              maxLength={64}
              pattern={RECONCILIATION_REFERENCE_PATTERN.source}
              autoComplete="off"
              spellCheck={false}
              aria-invalid={validationError && !referenceIsValid}
              aria-describedby={
                validationError
                  ? 'remnawave-reconciliation-reference-help remnawave-reconciliation-error'
                  : 'remnawave-reconciliation-reference-help'
              }
              className={inputClass}
              placeholder="CASE-ABC123"
            />
            <p id="remnawave-reconciliation-reference-help" className="mt-2 font-mono text-xs text-muted-foreground">
              {t('reconciliation.form.referenceHelp')}
            </p>
          </div>
          <label className="flex items-start gap-3 rounded-xl border border-amber-300/25 bg-amber-300/5 p-4 font-mono text-sm text-amber-100">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(event) => {
                setConfirmed(event.target.checked);
                setValidationError(false);
              }}
              className="mt-1 h-4 w-4 accent-cyan-400"
              aria-describedby={validationError ? 'remnawave-reconciliation-error' : undefined}
            />
            <span>{t('reconciliation.form.confirm')}</span>
          </label>
          {validationError ? (
            <p id="remnawave-reconciliation-error" role="alert" className="font-mono text-sm text-neon-pink">
              {t('reconciliation.form.validation')}
            </p>
          ) : null}
          {reconciliationMutation.error ? (
            <p role="alert" className="font-mono text-sm text-neon-pink">
              {t(errorKey(reconciliationMutation.error))}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={reconciliationMutation.isPending || Boolean(reconciliationMutation.error)}
            className={actionClass}
          >
            {reconciliationMutation.isPending
              ? t('reconciliation.actions.reconciling')
              : t('reconciliation.actions.reconcile')}
          </button>
        </form>
      ) : null}

      {reconciliationMutation.data ? (
        <p role="status" className="mt-5 rounded-xl border border-matrix-green/30 bg-matrix-green/5 p-4 font-mono text-sm text-matrix-green">
          {t(`reconciliation.states.success.${reconciliationMutation.data.state}`)}
        </p>
      ) : null}
    </section>
  );
}
