'use client';

import { useQuery } from '@tanstack/react-query';
import { TrendingUp } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { growthApi } from '@/lib/api/growth';
import { GrowthEmptyState } from '@/features/growth/components/growth-empty-state';
import { GrowthPageShell } from '@/features/growth/components/growth-page-shell';
import { GrowthStatusChip } from '@/features/growth/components/growth-status-chip';
import {
  formatCompactNumber,
  formatCurrencyAmount,
  formatDateTime,
  shortId,
} from '@/features/growth/lib/formatting';

export function ReferralSignalsConsole() {
  const t = useTranslations('Growth');
  const locale = useLocale();
  const referralQuery = useQuery({
    queryKey: ['growth', 'referrals', 'overview'],
    queryFn: async () => {
      const response = await growthApi.getReferralOverview();
      return response.data;
    },
    staleTime: 15_000,
  });

  const overview = referralQuery.data;

  return (
    <GrowthPageShell
      eyebrow={t('referrals.eyebrow')}
      title={t('referrals.title')}
      description={t('referrals.description')}
      icon={TrendingUp}
      metrics={[
        {
          label: t('referrals.metrics.adminSurface'),
          value: formatCompactNumber(overview?.total_commissions ?? 0, locale),
          hint: t('referrals.metrics.adminSurfaceHint'),
          tone: overview?.total_commissions ? 'success' : 'neutral',
        },
        {
          label: t('referrals.metrics.uniqueReferrers'),
          value: formatCompactNumber(overview?.unique_referrers ?? 0, locale),
          hint: t('referrals.metrics.uniqueReferrersHint'),
          tone: 'warning',
        },
        {
          label: t('referrals.metrics.uniqueReferred'),
          value: formatCompactNumber(overview?.unique_referred_users ?? 0, locale),
          hint: t('referrals.metrics.uniqueReferredHint'),
          tone: 'info',
        },
        {
          label: t('referrals.metrics.totalEarned'),
          value: formatCurrencyAmount(overview?.total_earned, 'USD', locale),
          hint: t('referrals.metrics.totalEarnedHint'),
          tone: 'warning',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('referrals.currentStateTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('referrals.currentStateDescription')}
              </p>
            </div>
            <GrowthStatusChip label={t('referrals.liveOverview')} tone="success" />
          </div>

          <div className="mt-5 grid gap-3">
            {referralQuery.isLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="h-20 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))
            ) : overview?.top_referrers.length ? (
              overview.top_referrers.map((row) => (
                <div
                  key={row.user.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {row.user.email}
                      </p>
                      <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        @{row.user.username ?? shortId(row.user.id, 12)} / #{shortId(row.user.id, 12)}
                      </p>
                    </div>
                    <GrowthStatusChip
                      label={formatCurrencyAmount(row.total_earned, 'USD', locale)}
                      tone={row.total_earned > 0 ? 'warning' : 'neutral'}
                    />
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <GrowthStatusChip
                      label={t('referrals.badges.commissions', { count: row.commission_count })}
                      tone="info"
                    />
                    <GrowthStatusChip
                      label={t('referrals.badges.referredUsers', { count: row.referred_users })}
                      tone="success"
                    />
                    <GrowthStatusChip
                      label={formatDateTime(row.last_commission_at, locale)}
                      tone="neutral"
                    />
                  </div>

                  <div className="mt-4">
                    <Link
                      href={`/customers/${row.user.id}`}
                      className="text-xs font-mono uppercase tracking-[0.18em] text-neon-cyan transition-opacity hover:opacity-80"
                    >
                      {t('referrals.openCustomer')}
                    </Link>
                  </div>
                </div>
              ))
            ) : (
              <GrowthEmptyState label={t('referrals.topReferrersEmpty')} />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('referrals.recentTitle')}
          </h2>
          <div className="mt-5 space-y-3">
            {referralQuery.isLoading ? (
              Array.from({ length: 3 }).map((_, index) => (
                <div
                  key={index}
                  className="h-20 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))
            ) : overview?.recent_commissions.length ? (
              overview.recent_commissions.map((commission) => (
                <div
                  key={commission.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {formatCurrencyAmount(commission.commission_amount, commission.currency, locale)}
                      </p>
                      <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {commission.referrer?.email ?? shortId(commission.referrer_user_id, 12)}
                        {' -> '}
                        {commission.referred_user?.email ?? shortId(commission.referred_user_id, 12)}
                      </p>
                    </div>
                    <GrowthStatusChip
                      label={`${commission.commission_rate}%`}
                      tone="warning"
                    />
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {formatDateTime(commission.created_at, locale)}
                  </p>
                </div>
              ))
            ) : (
              <GrowthEmptyState label={t('referrals.recentEmpty')} />
            )}
          </div>

          <div className="mt-5 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                {t('referrals.nextFocusTitle')}
              </p>
              <GrowthStatusChip label={t('common.backendLimited')} tone="warning" />
            </div>
            <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
              {t('referrals.nextFocusDescription')}
            </p>
          </div>
        </article>
      </div>
    </GrowthPageShell>
  );
}
