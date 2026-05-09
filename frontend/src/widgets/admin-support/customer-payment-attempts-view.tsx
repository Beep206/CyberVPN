'use client';

import { AlertTriangle, Clock3, ReceiptText, ShieldCheck } from 'lucide-react';

import {
  canViewFinancePaymentAttempts,
  canViewSupportPaymentAttempts,
  summarizePaymentAttemptForAdmin,
  type AdminPaymentAttemptRecord,
  type Stage1PaymentAttemptViewRole,
} from './customer-payment-attempts-view-model';

export type CustomerPaymentAttemptsViewProps = {
  actorRole: Stage1PaymentAttemptViewRole;
  attempts: AdminPaymentAttemptRecord[];
  customerLabel: string;
  isLoading?: boolean;
  userId: string;
};

const toneClassMap = {
  danger: 'border-server-offline/50 bg-server-offline/10 text-server-offline',
  muted: 'border-grid-line/60 bg-black/20 text-muted-foreground',
  success: 'border-matrix-green/50 bg-matrix-green/10 text-matrix-green',
  warning: 'border-server-warning/50 bg-server-warning/10 text-server-warning',
} as const;

export function CustomerPaymentAttemptsView({
  actorRole,
  attempts,
  customerLabel,
  isLoading = false,
  userId,
}: CustomerPaymentAttemptsViewProps) {
  const supportAllowed = canViewSupportPaymentAttempts(actorRole);
  const financeAllowed = canViewFinancePaymentAttempts(actorRole);

  return (
    <section
      aria-labelledby="customer-payment-attempts-title"
      className="rounded border border-grid-line/60 bg-black/30 p-4"
      data-testid="customer-payment-attempts-view"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2 text-neon-cyan">
            <ReceiptText aria-hidden="true" className="h-4 w-4 shrink-0" />
            <h3
              className="truncate text-sm font-display uppercase"
              id="customer-payment-attempts-title"
            >
              Payment attempts
            </h3>
          </div>
          <p className="break-words text-xs font-mono text-muted-foreground">
            {customerLabel} · {userId}
          </p>
        </div>
        <span
          className="w-fit rounded border border-neon-cyan/60 px-2 py-1 text-[10px] font-bold uppercase text-neon-cyan"
          data-testid="payment-attempts-role"
        >
          {financeAllowed ? 'finance view' : 'support view'}
        </span>
      </div>

      {!supportAllowed ? (
        <div
          className="mt-4 flex items-start gap-2 rounded border border-server-warning/50 bg-server-warning/10 p-3 text-xs text-server-warning"
          role="alert"
        >
          <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
          <span>Payment attempt status is restricted to support, finance, admin, and owner roles.</span>
        </div>
      ) : null}

      {supportAllowed && isLoading ? (
        <div
          aria-label="Loading payment attempts"
          className="mt-4 h-24 animate-pulse rounded border border-grid-line/40 bg-white/5"
        />
      ) : null}

      {supportAllowed && !isLoading && attempts.length === 0 ? (
        <div className="mt-4 rounded border border-grid-line/50 bg-black/20 p-3 text-xs text-muted-foreground">
          No payment attempts recorded for this customer.
        </div>
      ) : null}

      {supportAllowed && !isLoading && attempts.length > 0 ? (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full table-fixed border-collapse text-left text-xs">
            <thead className="border-b border-grid-line/60 text-muted-foreground">
              <tr>
                <th className="w-36 px-2 py-2 font-mono uppercase">Status</th>
                <th className="w-36 px-2 py-2 font-mono uppercase">Provider</th>
                <th className="w-32 px-2 py-2 font-mono uppercase">Amount</th>
                <th className="w-48 px-2 py-2 font-mono uppercase">Review</th>
                <th className="w-40 px-2 py-2 font-mono uppercase">Reference</th>
                <th className="w-32 px-2 py-2 font-mono uppercase">Age</th>
              </tr>
            </thead>
            <tbody>
              {attempts.map((attempt) => (
                <PaymentAttemptRow
                  attempt={attempt}
                  canShowFinance={financeAllowed}
                  key={attempt.id}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

function PaymentAttemptRow({
  attempt,
  canShowFinance,
}: {
  attempt: AdminPaymentAttemptRecord;
  canShowFinance: boolean;
}) {
  const summary = summarizePaymentAttemptForAdmin(attempt);
  const StatusIcon = summary.requiresSupport ? AlertTriangle : ShieldCheck;

  return (
    <tr className="border-b border-grid-line/30 align-top last:border-b-0">
      <td className="px-2 py-3">
        <span
          className={`inline-flex max-w-full items-center gap-1 rounded border px-2 py-1 font-mono uppercase ${toneClassMap[summary.tone]}`}
        >
          <StatusIcon aria-hidden="true" className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{summary.statusLabel}</span>
        </span>
      </td>
      <td className="px-2 py-3">
        <div className="break-words text-foreground">{summary.providerLabel}</div>
        <div className="mt-1 break-words font-mono text-muted-foreground">
          {attempt.provider_status ?? attempt.sale_channel}
        </div>
      </td>
      <td className="px-2 py-3">
        <div className="font-mono text-foreground">{summary.amountLabel}</div>
        {canShowFinance && summary.financeBreakdownLabel ? (
          <div className="mt-1 break-words text-muted-foreground">
            {summary.financeBreakdownLabel}
          </div>
        ) : null}
      </td>
      <td className="px-2 py-3">
        <div className="break-words text-foreground">{summary.reviewLabel}</div>
        {attempt.payment_record_present ? (
          <div className="mt-1 text-muted-foreground">payment record linked</div>
        ) : (
          <div className="mt-1 text-server-warning">no canonical payment record</div>
        )}
      </td>
      <td className="px-2 py-3">
        <div className="break-words font-mono text-muted-foreground">{summary.referenceLabel}</div>
        <div className="mt-1 break-words text-muted-foreground">
          order {attempt.order_id.slice(0, 8)}
        </div>
      </td>
      <td className="px-2 py-3">
        <div className="inline-flex items-center gap-1 font-mono text-muted-foreground">
          <Clock3 aria-hidden="true" className="h-3.5 w-3.5" />
          {attempt.age_minutes}m
        </div>
      </td>
    </tr>
  );
}
