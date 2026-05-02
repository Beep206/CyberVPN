'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  CreditCard,
  History,
  ReceiptText,
  RefreshCw,
  RotateCcw,
  WalletCards,
  XCircle,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { useState, type ReactNode } from 'react';
import { Link } from '@/i18n/navigation';
import { commerceApi, paymentsApi } from '@/lib/api';
import { createClientIdempotencyKey } from '@/lib/api/commerce';
import { markPerformance, measurePerformance, PerformanceMarks } from '@/shared/lib/web-vitals';
import {
  buildBillingEvents,
  canRetryOrder,
  filterBillingEvents,
  formatDateTime,
  formatLabel,
  formatMoney,
  formatShortId,
  getBillingFilter,
  getCompletedPaymentTotal,
  getOrderGatewayTotal,
  getOrderWalletTotal,
  getStatusTone,
  type BillingFilter,
  type BillingEvent,
  type OrderRecord,
  type StatusTone,
} from './billing-cabinet-model';

const PAGE_LIMIT = 20;
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

function LoadingBlock({ className = 'min-h-24' }: { className?: string }) {
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
  tone = 'cyan',
  value,
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

function getEventIcon(event: BillingEvent) {
  if (event.tone === 'green') {
    return <CheckCircle2 className="h-5 w-5" aria-hidden="true" />;
  }

  if (event.tone === 'pink') {
    return <XCircle className="h-5 w-5" aria-hidden="true" />;
  }

  if (event.tone === 'cyan' || event.tone === 'amber') {
    return <Clock3 className="h-5 w-5" aria-hidden="true" />;
  }

  return <ReceiptText className="h-5 w-5" aria-hidden="true" />;
}

export function PaymentHistoryDashboard() {
  const t = useTranslations('PaymentHistory');
  const locale = useLocale();
  const [page, setPage] = useState(0);
  const [filter, setFilter] = useState<BillingFilter>('all');
  const [retryOrderId, setRetryOrderId] = useState('');

  const paymentsQuery = useQuery({
    queryKey: ['payments', 'history', page],
    queryFn: async () => {
      const response = await paymentsApi.getHistory({
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

  const ordersQuery = useQuery({
    queryKey: ['orders', 'billing-history'],
    queryFn: async () => {
      const response = await commerceApi.listOrders({ limit: PAGE_LIMIT, offset: 0 });
      return response.data;
    },
    refetchInterval: visiblePolling(LIVE_REFETCH_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    staleTime: LIVE_STALE_MS,
  });

  const retryPaymentMutation = useMutation({
    mutationFn: async (order: OrderRecord) => {
      setRetryOrderId(order.id);
      markPerformance(PerformanceMarks.PURCHASE_FLOW_START, {
        flow: 'payment_retry',
      });

      const response = await commerceApi.createPaymentAttempt(
        { order_id: order.id },
        createClientIdempotencyKey('payment-retry'),
      );
      return response.data;
    },
    onSettled: () => {
      setRetryOrderId('');
    },
    onSuccess: (attempt) => {
      markPerformance(PerformanceMarks.PURCHASE_FLOW_COMPLETE, {
        flow: 'payment_retry',
      });
      measurePerformance(
        'payment-retry-flow-duration',
        PerformanceMarks.PURCHASE_FLOW_START,
        PerformanceMarks.PURCHASE_FLOW_COMPLETE,
      );

      if (attempt.invoice?.payment_url && typeof window !== 'undefined') {
        window.open(attempt.invoice.payment_url, '_blank', 'noopener,noreferrer');
      }

      void ordersQuery.refetch();
      void paymentsQuery.refetch();
    },
  });

  const payments = paymentsQuery.data?.payments ?? [];
  const orders = ordersQuery.data ?? [];
  const currency = payments[0]?.currency ?? orders[0]?.currency_code ?? 'USD';
  const billingEvents = buildBillingEvents({
    labels: {
      order: t('timeline.kind.order'),
      paymentSuffix: t('timeline.paymentSuffix'),
    },
    orders,
    payments,
  });
  const filteredEvents = filterBillingEvents(billingEvents, filter);
  const completedTotal = getCompletedPaymentTotal(payments);
  const pendingCount = billingEvents.filter((event) => getBillingFilter(event.status) === 'pending').length;
  const failedCount = billingEvents.filter((event) => getBillingFilter(event.status) === 'failed').length;
  const hasAnyError = paymentsQuery.isError || ordersQuery.isError;

  const refetchAll = () => Promise.all([paymentsQuery.refetch(), ordersQuery.refetch()]);

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-[2rem] border border-neon-pink/25 bg-terminal-surface/55 p-6 shadow-[0_0_70px_rgba(255,0,255,0.08)] backdrop-blur md:p-8">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,0,255,0.16),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(0,255,255,0.12),transparent_30%)]" />
        <div className="relative grid gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.34em] text-neon-pink">
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
                href="/wallet"
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-neon-cyan/40 bg-neon-cyan/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-neon-cyan transition hover:bg-neon-cyan/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
              >
                {t('hero.wallet')}
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link
                href="/subscriptions"
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-matrix-green/35 bg-matrix-green/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-matrix-green transition hover:bg-matrix-green/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
              >
                {t('hero.subscription')}
              </Link>
            </div>
          </div>

          <div className="rounded-3xl border border-grid-line/30 bg-black/25 p-5">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
              {t('hero.completed')}
            </p>
            {paymentsQuery.isPending ? (
              <div className="mt-4 h-12 animate-pulse rounded bg-grid-line/20" />
            ) : (
              <p className="mt-3 text-5xl font-display text-matrix-green drop-shadow-glow">
                {formatMoney(locale, completedTotal, currency)}
              </p>
            )}
            <div className="mt-5 flex flex-wrap gap-2">
              <StatusPill tone={pendingCount ? 'amber' : 'green'}>
                {t('hero.pending', { count: pendingCount })}
              </StatusPill>
              <StatusPill tone={failedCount ? 'pink' : 'muted'}>
                {t('hero.failed', { count: failedCount })}
              </StatusPill>
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
          icon={<CreditCard className="h-5 w-5" aria-hidden="true" />}
          label={t('summary.completed')}
          tone="green"
          value={formatMoney(locale, completedTotal, currency)}
        />
        <MetricCard
          icon={<WalletCards className="h-5 w-5" aria-hidden="true" />}
          label={t('summary.walletApplied')}
          tone="cyan"
          value={formatMoney(locale, getOrderWalletTotal(orders), currency)}
        />
        <MetricCard
          icon={<ReceiptText className="h-5 w-5" aria-hidden="true" />}
          label={t('summary.gateway')}
          tone="purple"
          value={formatMoney(locale, getOrderGatewayTotal(orders), currency)}
        />
        <MetricCard
          icon={<Clock3 className="h-5 w-5" aria-hidden="true" />}
          label={t('summary.pending')}
          tone={pendingCount ? 'amber' : 'green'}
          value={String(pendingCount)}
        />
      </section>

      <section className="rounded-[2rem] border border-grid-line/30 bg-terminal-surface/55 p-6 backdrop-blur">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-cyan">
              {t('timeline.eyebrow')}
            </p>
            <h2 className="mt-2 text-2xl font-display text-white">{t('timeline.title')}</h2>
            <p className="mt-2 max-w-2xl font-mono text-sm leading-7 text-muted-foreground">
              {t('timeline.description')}
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

        <div className="mt-6 flex flex-wrap gap-2" aria-label={t('timeline.filters.ariaLabel')}>
          {(['all', 'completed', 'pending', 'failed', 'refunded'] as const).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setFilter(item)}
              className={`min-h-10 rounded-xl border px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] transition focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg ${
                filter === item
                  ? 'border-neon-pink/40 bg-neon-pink/10 text-neon-pink'
                  : 'border-grid-line/30 bg-terminal-bg/60 text-muted-foreground hover:border-neon-pink/30 hover:text-neon-pink'
              }`}
            >
              {t(`timeline.filters.${item}`)}
            </button>
          ))}
        </div>

        {paymentsQuery.isPending || ordersQuery.isPending ? (
          <div className="mt-6 space-y-3">
            {[0, 1, 2, 3].map((item) => (
              <LoadingBlock key={item} />
            ))}
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="mt-6 rounded-3xl border border-grid-line/30 bg-black/20 p-8 text-center">
            <History className="mx-auto h-10 w-10 text-muted-foreground/60" aria-hidden="true" />
            <p className="mt-3 font-mono text-sm text-muted-foreground">{t('timeline.empty')}</p>
          </div>
        ) : (
          <div className="mt-6 space-y-3">
            {filteredEvents.map((event) => {
              const order = event.kind === 'order' ? orders.find((item) => item.id === event.id) : null;
              const retryable = order ? canRetryOrder(order) : false;
              const tone = event.tone;

              return (
                <div
                  key={`${event.kind}-${event.id}`}
                  className="rounded-2xl border border-grid-line/30 bg-black/20 p-4 transition hover:border-neon-pink/25"
                >
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="flex items-start gap-4">
                      <div className={`rounded-2xl border p-3 ${toneClasses[tone].border} ${toneClasses[tone].fill} ${toneClasses[tone].text}`}>
                        {getEventIcon(event)}
                      </div>
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-mono text-sm text-white">{event.title}</p>
                          <StatusPill tone={getStatusTone(event.status)}>
                            {formatLabel(event.status, t('labels.notAvailable'))}
                          </StatusPill>
                        </div>
                        <p className="mt-2 font-mono text-xs leading-6 text-muted-foreground">
                          {formatDateTime(event.createdAt, locale)} / {formatShortId(event.id)} /{' '}
                          {event.kind === 'order' ? t('timeline.kind.order') : t('timeline.kind.payment')}
                        </p>
                        {order && (
                          <p className="mt-1 font-mono text-xs text-muted-foreground">
                            {t('timeline.orderSplit', {
                              gateway: formatMoney(locale, order.gateway_amount, order.currency_code),
                              wallet: formatMoney(locale, order.wallet_amount, order.currency_code),
                            })}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col gap-3 lg:items-end">
                      <p className={`font-display text-xl ${toneClasses[tone].text}`}>
                        {formatMoney(locale, event.amount, event.currency)}
                      </p>
                      {retryable && order && (
                        <button
                          type="button"
                          disabled={retryPaymentMutation.isPending}
                          onClick={() => retryPaymentMutation.mutate(order)}
                          className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-neon-cyan/40 bg-neon-cyan/10 px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-neon-cyan transition hover:bg-neon-cyan/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <RotateCcw className="h-4 w-4" aria-hidden="true" />
                          {retryOrderId === order.id && retryPaymentMutation.isPending
                            ? t('timeline.retrying')
                            : t('timeline.retry')}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {retryPaymentMutation.isError && (
          <p className="mt-4 font-mono text-sm text-neon-pink" role="alert">
            {t('timeline.retryError')}
          </p>
        )}

        <div className="mt-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <p className="font-mono text-xs text-muted-foreground">
            {t('timeline.page', { page: page + 1 })}
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
              disabled={(paymentsQuery.data?.payments.length ?? 0) < PAGE_LIMIT}
              className="min-h-10 rounded-xl border border-grid-line/40 bg-terminal-bg/60 px-4 py-2 font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground transition hover:border-neon-cyan/40 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t('actions.next')}
            </button>
          </div>
        </div>
      </section>

      <section className="rounded-[2rem] border border-matrix-green/20 bg-terminal-surface/45 p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.28em] text-matrix-green">
              {t('support.eyebrow')}
            </p>
            <h2 className="mt-2 text-2xl font-display text-white">{t('support.title')}</h2>
            <p className="mt-2 font-mono text-sm leading-7 text-muted-foreground">
              {t('support.description')}
            </p>
          </div>
          <Link
            href="/settings"
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-matrix-green/35 bg-matrix-green/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-matrix-green transition hover:bg-matrix-green/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
          >
            {t('support.cta')}
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
      </section>
    </div>
  );
}
