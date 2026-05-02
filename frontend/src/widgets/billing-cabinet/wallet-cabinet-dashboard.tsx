'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowDownLeft,
  ArrowRight,
  ArrowUpRight,
  Clock3,
  CreditCard,
  History,
  LockKeyhole,
  RefreshCw,
  ShieldCheck,
  Wallet,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { useState, type FormEvent, type ReactNode } from 'react';
import { Link } from '@/i18n/navigation';
import { walletApi } from '@/lib/api';
import { markPerformance, measurePerformance, PerformanceMarks } from '@/shared/lib/web-vitals';
import {
  formatDateTime,
  formatLabel,
  formatMoney,
  formatShortId,
  getPendingWithdrawals,
  getRecentTransaction,
  getSortedTransactions,
  getSortedWithdrawals,
  getTransactionDirection,
  getTransactionTone,
  getWalletLiability,
  type StatusTone,
  type TransactionDirection,
  type WalletTransactionRecord,
} from './billing-cabinet-model';

type DirectionFilter = 'all' | TransactionDirection;

const PAGE_LIMIT = 12;
const LIVE_STALE_MS = 30_000;
const LIVE_REFETCH_MS = 45_000;

const toneClasses: Record<StatusTone, { border: string; fill: string; text: string }> = {
  amber: {
    border: 'border-amber-400/30',
    fill: 'bg-amber-400/10',
    text: 'text-amber-300',
  },
  cyan: {
    border: 'border-neon-cyan/30',
    fill: 'bg-neon-cyan/10',
    text: 'text-neon-cyan',
  },
  green: {
    border: 'border-matrix-green/30',
    fill: 'bg-matrix-green/10',
    text: 'text-matrix-green',
  },
  muted: {
    border: 'border-grid-line/30',
    fill: 'bg-terminal-bg/40',
    text: 'text-muted-foreground',
  },
  pink: {
    border: 'border-neon-pink/30',
    fill: 'bg-neon-pink/10',
    text: 'text-neon-pink',
  },
  purple: {
    border: 'border-neon-purple/30',
    fill: 'bg-neon-purple/10',
    text: 'text-neon-purple',
  },
};

function visiblePolling(intervalMs: number) {
  return (query: { state: { error: unknown } }) => {
    if (query.state.error) {
      return false;
    }

    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
      return false;
    }

    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      return false;
    }

    return intervalMs;
  };
}

function StatusPill({ children, tone }: { children: ReactNode; tone: StatusTone }) {
  const classes = toneClasses[tone];

  return (
    <span
      className={`inline-flex min-h-8 items-center rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] ${classes.border} ${classes.fill} ${classes.text}`}
    >
      {children}
    </span>
  );
}

function LoadingBlock({ className = 'min-h-36' }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`${className} animate-pulse rounded-3xl border border-grid-line/30 bg-terminal-surface/40`}
    />
  );
}

function MetricCard({
  icon,
  label,
  value,
  tone = 'cyan',
}: {
  icon: ReactNode;
  label: string;
  tone?: StatusTone;
  value: string;
}) {
  return (
    <article className="rounded-2xl border border-grid-line/30 bg-terminal-surface/45 p-5">
      <div className={toneClasses[tone].text}>{icon}</div>
      <p className="mt-4 font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 truncate text-2xl font-display text-white">{value}</p>
    </article>
  );
}

function getDirectionSign(transaction: WalletTransactionRecord) {
  const direction = getTransactionDirection(transaction);
  if (direction === 'credit') {
    return '+';
  }

  if (direction === 'debit') {
    return '-';
  }

  return '';
}

export function WalletCabinetDashboard() {
  const t = useTranslations('Wallet');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [filter, setFilter] = useState<DirectionFilter>('all');
  const [amount, setAmount] = useState('');
  const [method, setMethod] = useState('cryptobot');
  const [formError, setFormError] = useState('');

  const walletQuery = useQuery({
    queryKey: ['wallet', 'balance'],
    queryFn: async () => {
      const response = await walletApi.getBalance();
      return response.data;
    },
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    staleTime: LIVE_STALE_MS,
  });

  const transactionsQuery = useQuery({
    queryKey: ['wallet', 'transactions', page],
    queryFn: async () => {
      const response = await walletApi.getTransactions({
        limit: PAGE_LIMIT,
        offset: page * PAGE_LIMIT,
      });
      return response.data;
    },
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    staleTime: LIVE_STALE_MS,
  });

  const withdrawalsQuery = useQuery({
    queryKey: ['wallet', 'withdrawals'],
    queryFn: async () => {
      const response = await walletApi.getWithdrawals();
      return response.data;
    },
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    staleTime: LIVE_STALE_MS,
  });

  const withdrawalMutation = useMutation({
    mutationFn: async (input: { amount: number; method: string }) => {
      markPerformance(PerformanceMarks.WITHDRAWAL_FLOW_START, {
        method: input.method,
      });

      const response = await walletApi.requestWithdrawal(input);
      return response.data;
    },
    onSuccess: () => {
      markPerformance(PerformanceMarks.WITHDRAWAL_FLOW_COMPLETE, {
        method,
      });
      measurePerformance(
        'wallet-withdrawal-flow-duration',
        PerformanceMarks.WITHDRAWAL_FLOW_START,
        PerformanceMarks.WITHDRAWAL_FLOW_COMPLETE,
      );
      setAmount('');
      setFormError('');
      void queryClient.invalidateQueries({ queryKey: ['wallet'] });
    },
  });

  const wallet = walletQuery.data ?? null;
  const transactions = getSortedTransactions(transactionsQuery.data ?? []);
  const withdrawals = getSortedWithdrawals(withdrawalsQuery.data ?? []);
  const pendingWithdrawals = getPendingWithdrawals(withdrawals);
  const filteredTransactions =
    filter === 'all'
      ? transactions
      : transactions.filter((transaction) => getTransactionDirection(transaction) === filter);
  const recentTransaction = getRecentTransaction(transactions);
  const currency = wallet?.currency ?? 'USD';
  const hasAnyError = walletQuery.isError || transactionsQuery.isError || withdrawalsQuery.isError;

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const parsedAmount = Number(amount);
    if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      setFormError(t('withdrawForm.errors.amount'));
      return;
    }

    if (wallet && parsedAmount > wallet.balance) {
      setFormError(t('withdrawForm.errors.balance'));
      return;
    }

    setFormError('');
    withdrawalMutation.mutate({
      amount: parsedAmount,
      method,
    });
  };

  const refetchAll = () =>
    Promise.all([
      walletQuery.refetch(),
      transactionsQuery.refetch(),
      withdrawalsQuery.refetch(),
    ]);

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-[2rem] border border-neon-cyan/25 bg-terminal-surface/55 p-6 shadow-[0_0_70px_rgba(0,255,255,0.08)] backdrop-blur md:p-8">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(0,255,255,0.18),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(0,255,136,0.12),transparent_30%)]" />
        <div className="relative grid gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.34em] text-neon-cyan">
              {t('hero.eyebrow')}
            </p>
            <h1 className="mt-4 max-w-3xl text-4xl font-display tracking-[0.08em] text-white md:text-5xl">
              {t('title')}
            </h1>
            <p className="mt-4 max-w-2xl font-mono text-sm leading-7 text-muted-foreground">
              {t('subtitle')}
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/payment-history"
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-neon-cyan/40 bg-neon-cyan/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-neon-cyan transition hover:bg-neon-cyan/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
              >
                {t('hero.paymentHistory')}
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link
                href="/subscriptions"
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-matrix-green/35 bg-matrix-green/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-matrix-green transition hover:bg-matrix-green/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
              >
                {t('hero.managePlan')}
              </Link>
            </div>
          </div>

          <div className="rounded-3xl border border-grid-line/30 bg-black/25 p-5">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
              {t('hero.available')}
            </p>
            {walletQuery.isPending ? (
              <div className="mt-4 h-12 animate-pulse rounded bg-grid-line/20" />
            ) : (
              <p className="mt-3 text-5xl font-display text-matrix-green drop-shadow-glow">
                {formatMoney(locale, wallet?.balance ?? 0, currency)}
              </p>
            )}
            <div className="mt-5 flex flex-wrap gap-2">
              <StatusPill tone={wallet?.frozen ? 'amber' : 'green'}>
                {wallet?.frozen ? t('hero.fundsFrozen') : t('hero.fundsReady')}
              </StatusPill>
              <StatusPill tone="cyan">{t('hero.currency', { currency })}</StatusPill>
            </div>
          </div>
        </div>
      </section>

      {hasAnyError && (
        <section
          className="rounded-2xl border border-amber-400/30 bg-amber-400/10 p-4 font-mono text-sm text-amber-200"
          role="status"
        >
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
            <div>
              <p className="font-semibold">{t('errors.partialTitle')}</p>
              <p className="mt-1 text-amber-100/80">{t('errors.partialDescription')}</p>
            </div>
          </div>
        </section>
      )}

      <section className="grid gap-4 md:grid-cols-4" aria-label={t('summary.ariaLabel')}>
        <MetricCard
          icon={<Wallet className="h-5 w-5" aria-hidden="true" />}
          label={t('summary.balance')}
          tone="green"
          value={formatMoney(locale, wallet?.balance ?? 0, currency)}
        />
        <MetricCard
          icon={<LockKeyhole className="h-5 w-5" aria-hidden="true" />}
          label={t('summary.frozen')}
          tone={wallet?.frozen ? 'amber' : 'muted'}
          value={formatMoney(locale, wallet?.frozen ?? 0, currency)}
        />
        <MetricCard
          icon={<ShieldCheck className="h-5 w-5" aria-hidden="true" />}
          label={t('summary.liability')}
          tone="cyan"
          value={formatMoney(locale, getWalletLiability(wallet), currency)}
        />
        <MetricCard
          icon={<Clock3 className="h-5 w-5" aria-hidden="true" />}
          label={t('summary.pendingWithdrawals')}
          tone={pendingWithdrawals.length ? 'amber' : 'green'}
          value={String(pendingWithdrawals.length)}
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        <article className="rounded-[2rem] border border-neon-purple/25 bg-terminal-surface/55 p-6 backdrop-blur">
          <div className="flex items-start gap-4">
            <div className="rounded-2xl border border-neon-purple/30 bg-neon-purple/10 p-3">
              <ArrowUpRight className="h-6 w-6 text-neon-purple" aria-hidden="true" />
            </div>
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-purple">
                {t('withdrawForm.eyebrow')}
              </p>
              <h2 className="mt-2 text-2xl font-display text-white">{t('withdrawForm.title')}</h2>
              <p className="mt-2 font-mono text-sm leading-7 text-muted-foreground">
                {t('withdrawForm.description')}
              </p>
            </div>
          </div>

          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label className="block font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground" htmlFor="wallet-withdraw-amount">
                {t('withdrawForm.amount')}
              </label>
              <input
                id="wallet-withdraw-amount"
                inputMode="decimal"
                min="0"
                onChange={(event) => setAmount(event.target.value)}
                placeholder="0.00"
                step="0.01"
                type="number"
                value={amount}
                className="min-h-12 w-full rounded-xl border border-grid-line/40 bg-terminal-bg px-4 py-3 font-mono text-sm text-white outline-hidden transition focus:border-neon-cyan focus:ring-2 focus:ring-neon-cyan/30"
              />
            </div>
            <div className="space-y-2">
              <label className="block font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground" htmlFor="wallet-withdraw-method">
                {t('withdrawForm.method')}
              </label>
              <select
                id="wallet-withdraw-method"
                onChange={(event) => setMethod(event.target.value)}
                value={method}
                className="min-h-12 w-full rounded-xl border border-grid-line/40 bg-terminal-bg px-4 py-3 font-mono text-sm text-white outline-hidden transition focus:border-neon-cyan focus:ring-2 focus:ring-neon-cyan/30"
              >
                <option value="cryptobot">{t('withdrawForm.methods.cryptobot')}</option>
                <option value="manual">{t('withdrawForm.methods.manual')}</option>
              </select>
            </div>

            <div className="rounded-2xl border border-grid-line/30 bg-black/20 p-4 font-mono text-xs leading-6 text-muted-foreground">
              {t('withdrawForm.notice')}
            </div>

            {(formError || withdrawalMutation.isError) && (
              <p className="font-mono text-sm text-neon-pink" role="alert">
                {formError || t('withdrawForm.errors.submit')}
              </p>
            )}
            {withdrawalMutation.isSuccess && (
              <p className="font-mono text-sm text-matrix-green" role="status">
                {t('withdrawForm.success')}
              </p>
            )}

            <button
              type="submit"
              disabled={withdrawalMutation.isPending || walletQuery.isPending}
              className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-neon-purple/45 bg-neon-purple/15 px-4 py-3 font-mono text-xs uppercase tracking-[0.16em] text-neon-purple transition hover:bg-neon-purple/20 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
            >
              <CreditCard className="h-4 w-4" aria-hidden="true" />
              {withdrawalMutation.isPending ? t('withdrawForm.submitting') : t('withdrawForm.submit')}
            </button>
          </form>
        </article>

        <article className="rounded-[2rem] border border-grid-line/30 bg-terminal-surface/55 p-6 backdrop-blur">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-cyan">
                {t('withdrawals.eyebrow')}
              </p>
              <h2 className="mt-2 text-2xl font-display text-white">{t('withdrawals.title')}</h2>
              <p className="mt-2 font-mono text-sm leading-7 text-muted-foreground">
                {recentTransaction
                  ? t('withdrawals.lastLedger', {
                      id: formatShortId(recentTransaction.id),
                    })
                  : t('withdrawals.description')}
              </p>
            </div>
            <button
              type="button"
              onClick={() => void refetchAll()}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-grid-line/40 bg-terminal-bg/60 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground transition hover:border-neon-cyan/40 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              {t('actions.refresh')}
            </button>
          </div>

          {withdrawalsQuery.isPending ? (
            <LoadingBlock className="mt-6 min-h-56" />
          ) : withdrawals.length === 0 ? (
            <div className="mt-6 rounded-3xl border border-grid-line/30 bg-black/20 p-8 text-center">
              <History className="mx-auto h-10 w-10 text-muted-foreground/60" aria-hidden="true" />
              <p className="mt-3 font-mono text-sm text-muted-foreground">{t('withdrawals.empty')}</p>
            </div>
          ) : (
            <div className="mt-6 space-y-3">
              {withdrawals.slice(0, 5).map((withdrawal) => (
                <div
                  key={withdrawal.id}
                  className="rounded-2xl border border-grid-line/30 bg-black/20 p-4"
                >
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <p className="font-mono text-sm text-white">
                        {formatMoney(locale, withdrawal.amount, withdrawal.currency)}
                      </p>
                      <p className="mt-1 font-mono text-xs text-muted-foreground">
                        {formatShortId(withdrawal.id)} / {formatDateTime(withdrawal.created_at, locale)}
                      </p>
                    </div>
                    <StatusPill tone={withdrawal.status === 'completed' ? 'green' : 'amber'}>
                      {formatLabel(withdrawal.status, t('labels.notAvailable'))}
                    </StatusPill>
                  </div>
                </div>
              ))}
            </div>
          )}
        </article>
      </section>

      <section className="rounded-[2rem] border border-grid-line/30 bg-terminal-surface/55 p-6 backdrop-blur">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.28em] text-matrix-green">
              {t('transactions.eyebrow')}
            </p>
            <h2 className="mt-2 text-2xl font-display text-white">{t('transactions.title')}</h2>
          </div>
          <div className="flex flex-wrap gap-2" aria-label={t('transactions.filters.ariaLabel')}>
            {(['all', 'credit', 'debit'] as const).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setFilter(item)}
                className={`min-h-10 rounded-xl border px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] transition focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg ${
                  filter === item
                    ? 'border-matrix-green/40 bg-matrix-green/10 text-matrix-green'
                    : 'border-grid-line/30 bg-terminal-bg/60 text-muted-foreground hover:border-matrix-green/30 hover:text-matrix-green'
                }`}
              >
                {t(`transactions.filters.${item}`)}
              </button>
            ))}
          </div>
        </div>

        {transactionsQuery.isPending ? (
          <div className="mt-6 space-y-3">
            {[0, 1, 2, 3].map((item) => (
              <LoadingBlock key={item} className="min-h-20" />
            ))}
          </div>
        ) : filteredTransactions.length === 0 ? (
          <div className="mt-6 rounded-3xl border border-grid-line/30 bg-black/20 p-8 text-center">
            <History className="mx-auto h-10 w-10 text-muted-foreground/60" aria-hidden="true" />
            <p className="mt-3 font-mono text-sm text-muted-foreground">{t('transactions.empty')}</p>
          </div>
        ) : (
          <div className="mt-6 space-y-3">
            {filteredTransactions.map((transaction) => {
              const direction = getTransactionDirection(transaction);
              const tone = getTransactionTone(transaction);

              return (
                <div
                  key={transaction.id}
                  className="rounded-2xl border border-grid-line/30 bg-black/20 p-4 transition hover:border-neon-cyan/25"
                >
                  <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div className="flex items-start gap-4">
                      <div className={`rounded-2xl border p-3 ${toneClasses[tone].border} ${toneClasses[tone].fill}`}>
                        {direction === 'credit' ? (
                          <ArrowDownLeft className={`h-5 w-5 ${toneClasses[tone].text}`} aria-hidden="true" />
                        ) : (
                          <ArrowUpRight className={`h-5 w-5 ${toneClasses[tone].text}`} aria-hidden="true" />
                        )}
                      </div>
                      <div>
                        <p className="font-mono text-sm text-white">
                          {transaction.description || formatLabel(transaction.reason, t('labels.transaction'))}
                        </p>
                        <p className="mt-1 font-mono text-xs text-muted-foreground">
                          {formatDateTime(transaction.created_at, locale)} / {formatShortId(transaction.id)}
                        </p>
                      </div>
                    </div>
                    <div className="text-left md:text-right">
                      <p className={`font-display text-lg ${toneClasses[tone].text}`}>
                        {getDirectionSign(transaction)}
                        {formatMoney(locale, Math.abs(transaction.amount), currency)}
                      </p>
                      <p className="mt-1 font-mono text-xs text-muted-foreground">
                        {t('transactions.balanceAfter', {
                          amount: formatMoney(locale, transaction.balance_after, currency),
                        })}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <p className="font-mono text-xs text-muted-foreground">
            {t('transactions.page', { page: page + 1 })}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setPage((current) => Math.max(0, current - 1))}
              disabled={page === 0}
              className="min-h-10 rounded-xl border border-grid-line/40 bg-terminal-bg/60 px-4 py-2 font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground transition hover:border-neon-cyan/40 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t('actions.previous')}
            </button>
            <button
              type="button"
              onClick={() => setPage((current) => current + 1)}
              disabled={(transactionsQuery.data?.length ?? 0) < PAGE_LIMIT}
              className="min-h-10 rounded-xl border border-grid-line/40 bg-terminal-bg/60 px-4 py-2 font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground transition hover:border-neon-cyan/40 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t('actions.next')}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
