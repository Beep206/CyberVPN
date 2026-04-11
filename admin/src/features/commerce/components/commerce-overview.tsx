'use client';

import { Landmark, Package2, ReceiptText, WalletCards } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { paymentsApi } from '@/lib/api/payments';
import { plansApi } from '@/lib/api/plans';
import { subscriptionsApi } from '@/lib/api/subscriptions';
import { adminWalletApi } from '@/lib/api/wallet';
import { CommercePageShell } from '@/features/commerce/components/commerce-page-shell';
import { StatusChip } from '@/features/commerce/components/status-chip';
import {
  formatCompactNumber,
  formatCurrencyAmount,
  formatDateTime,
  humanizeToken,
  shortId,
} from '@/features/commerce/lib/formatting';

function EmptyState({ label }: { label: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
      {label}
    </div>
  );
}

function statusTone(status: string) {
  const normalized = status.toLowerCase();

  if (normalized === 'completed' || normalized === 'approved') {
    return 'success' as const;
  }

  if (normalized === 'failed' || normalized === 'rejected') {
    return 'danger' as const;
  }

  return 'info' as const;
}

export function CommerceOverview() {
  const t = useTranslations('Commerce');
  const plansQuery = useQuery({
    queryKey: ['commerce', 'plans'],
    queryFn: async () => {
      const response = await plansApi.list();
      return response.data;
    },
    staleTime: 60_000,
  });
  const templatesQuery = useQuery({
    queryKey: ['commerce', 'subscription-templates'],
    queryFn: async () => {
      const response = await subscriptionsApi.list();
      return response.data;
    },
    staleTime: 60_000,
  });
  const paymentsQuery = useQuery({
    queryKey: ['commerce', 'payments', { limit: 8 }],
    queryFn: async () => {
      const response = await paymentsApi.getHistory({ offset: 0, limit: 8 });
      return response.data.payments;
    },
    staleTime: 30_000,
  });
  const withdrawalsQuery = useQuery({
    queryKey: ['commerce', 'withdrawals', 'pending'],
    queryFn: async () => {
      const response = await adminWalletApi.getPendingWithdrawals();
      return response.data;
    },
    staleTime: 30_000,
  });

  const activePlans =
    plansQuery.data?.filter((plan) => plan.isActive).length ?? 0;
  const payoutVolume = withdrawalsQuery.data?.reduce(
    (sum, withdrawal) => sum + withdrawal.amount,
    0,
  );

  return (
    <CommercePageShell
      eyebrow={t('overview.eyebrow')}
      title={t('overview.title')}
      description={t('overview.description')}
      icon={Landmark}
      metrics={[
        {
          label: t('overview.metrics.plans'),
          value: formatCompactNumber(plansQuery.data?.length),
          hint: `${activePlans} ${t('overview.metrics.activePlansHint')}`,
          tone: 'info',
        },
        {
          label: t('overview.metrics.templates'),
          value: formatCompactNumber(templatesQuery.data?.length),
          hint: t('overview.metrics.templatesHint'),
          tone: 'neutral',
        },
        {
          label: t('overview.metrics.payments'),
          value: formatCompactNumber(paymentsQuery.data?.length),
          hint: t('overview.metrics.paymentsHint'),
          tone: 'success',
        },
        {
          label: t('overview.metrics.withdrawals'),
          value: formatCurrencyAmount(payoutVolume, 'USD'),
          hint: `${withdrawalsQuery.data?.length ?? 0} ${t('overview.metrics.pendingItemsHint')}`,
          tone: 'warning',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('overview.modulesTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('overview.modulesDescription')}
          </p>
          <div className="mt-5 grid gap-3">
            {[
              {
                href: '/commerce/plans',
                title: t('nav.plans'),
                description: t('overview.routes.plans'),
              },
              {
                href: '/commerce/subscription-templates',
                title: t('nav.subscriptionTemplates'),
                description: t('overview.routes.subscriptionTemplates'),
              },
              {
                href: '/commerce/payments',
                title: t('nav.payments'),
                description: t('overview.routes.payments'),
              },
              {
                href: '/commerce/wallets',
                title: t('nav.wallets'),
                description: t('overview.routes.wallets'),
              },
              {
                href: '/commerce/withdrawals',
                title: t('nav.withdrawals'),
                description: t('overview.routes.withdrawals'),
              },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4 transition-colors hover:border-neon-cyan/35 hover:bg-terminal-bg/60"
              >
                <p className="text-sm font-display uppercase tracking-[0.18em] text-white">
                  {item.title}
                </p>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {item.description}
                </p>
              </Link>
            ))}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <ReceiptText className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.paymentsTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('overview.paymentsDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {paymentsQuery.data?.length ? (
              paymentsQuery.data.slice(0, 5).map((payment) => (
                <div
                  key={payment.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-lg font-display tracking-[0.12em] text-white">
                        {formatCurrencyAmount(payment.amount, payment.currency)}
                      </p>
                      <p className="mt-1 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {humanizeToken(payment.provider)} / #{shortId(payment.id)}
                      </p>
                    </div>

                    <StatusChip
                      label={humanizeToken(payment.status)}
                      tone={statusTone(payment.status)}
                    />
                  </div>
                  <p className="mt-3 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {formatDateTime(payment.created_at)}
                  </p>
                </div>
              ))
            ) : (
              <EmptyState label={t('common.empty')} />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <Package2 className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.templatesTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('overview.templatesDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {templatesQuery.data?.length ? (
              templatesQuery.data.slice(0, 4).map((template) => (
                <div
                  key={template.uuid}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {template.name}
                      </p>
                      <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {template.templateType}
                      </p>
                    </div>

                    <StatusChip
                      label={template.flow ?? t('overview.noFlow')}
                      tone="info"
                    />
                  </div>
                </div>
              ))
            ) : (
              <EmptyState label={t('common.empty')} />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <WalletCards className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.withdrawalsTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('overview.withdrawalsDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {withdrawalsQuery.data?.length ? (
              withdrawalsQuery.data.slice(0, 4).map((withdrawal) => (
                <div
                  key={withdrawal.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-lg font-display tracking-[0.12em] text-white">
                        {formatCurrencyAmount(withdrawal.amount, withdrawal.currency)}
                      </p>
                      <p className="mt-1 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {humanizeToken(withdrawal.method)} / #{shortId(withdrawal.id)}
                      </p>
                    </div>

                    <StatusChip
                      label={humanizeToken(withdrawal.status)}
                      tone="warning"
                    />
                  </div>
                  <p className="mt-3 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {formatDateTime(withdrawal.created_at)}
                  </p>
                </div>
              ))
            ) : (
              <EmptyState label={t('common.empty')} />
            )}
          </div>
        </article>
      </div>
    </CommercePageShell>
  );
}
