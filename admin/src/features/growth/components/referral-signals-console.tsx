'use client';

import { ShieldAlert } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useLocale, useTranslations } from 'next-intl';
import { GrowthEmptyState } from '@/features/growth/components/growth-empty-state';
import { GrowthPageShell } from '@/features/growth/components/growth-page-shell';
import { GrowthStatusChip } from '@/features/growth/components/growth-status-chip';
import {
  formatCompactNumber,
  formatCurrencyAmount,
  formatDateTime,
  humanizeToken,
} from '@/features/growth/lib/formatting';
import { growthApi } from '@/lib/api/growth';

export function ReferralSignalsConsole() {
  const t = useTranslations('Growth');
  const locale = useLocale();

  const overviewQuery = useQuery({
    queryKey: ['growth', 'signals', 'overview', 'referrals'],
    queryFn: async () => {
      const response = await growthApi.getGrowthSignalsOverview();
      return response.data;
    },
    staleTime: 15_000,
  });

  const abuseQuery = useQuery({
    queryKey: ['growth', 'signals', 'abuse-queue'],
    queryFn: async () => {
      const response = await growthApi.listGrowthAbuseSignals({ limit: 25 });
      return response.data;
    },
    staleTime: 15_000,
  });

  const overview = overviewQuery.data;
  const abuseSignals = abuseQuery.data?.items ?? [];
  const referralEvents = (overview?.recent_lifecycle_events ?? []).filter(
    (event) => event.event_family === 'referral' || event.event_family === 'growth_reward',
  );

  return (
    <GrowthPageShell
      eyebrow={t('referrals.eyebrow')}
      title={t('referrals.title')}
      description={t('referrals.description')}
      icon={ShieldAlert}
      metrics={[
        {
          label: t('referrals.metrics.availableCredit'),
          value: formatCurrencyAmount(overview?.available_referral_credit_usd, 'USD', locale),
          hint: t('referrals.metrics.availableCreditHint'),
          tone: 'warning',
        },
        {
          label: t('referrals.metrics.blockedRewards'),
          value: formatCompactNumber(overview?.blocked_reward_count ?? 0, locale),
          hint: t('referrals.metrics.blockedRewardsHint'),
          tone: (overview?.blocked_reward_count ?? 0) > 0 ? 'danger' : 'neutral',
        },
        {
          label: t('referrals.metrics.totalRedemptions'),
          value: formatCompactNumber(overview?.total_redemptions ?? 0, locale),
          hint: t('referrals.metrics.totalRedemptionsHint'),
          tone: 'success',
        },
        {
          label: t('referrals.metrics.activeReservations'),
          value: formatCompactNumber(overview?.active_reservations ?? 0, locale),
          hint: t('referrals.metrics.activeReservationsHint'),
          tone: 'info',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('referrals.abuseQueueTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('referrals.abuseQueueDescription')}
              </p>
            </div>
            <GrowthStatusChip label={t('referrals.liveOverview')} tone="warning" />
          </div>

          <div className="mt-5 space-y-3">
            {abuseQuery.isLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="h-24 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))
            ) : abuseSignals.length ? (
              abuseSignals.map((signal) => (
                <div
                  key={signal.signal_key}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {humanizeToken(signal.signal_type)}
                      </p>
                      <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {humanizeToken(signal.reason_code)}
                        {signal.code_type ? ` / ${humanizeToken(signal.code_type)}` : ''}
                      </p>
                    </div>
                    <GrowthStatusChip
                      label={humanizeToken(signal.severity)}
                      tone={signal.severity === 'danger' ? 'danger' : 'warning'}
                    />
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <GrowthStatusChip
                      label={t('referrals.badges.count', { count: signal.count })}
                      tone="danger"
                    />
                    <GrowthStatusChip
                      label={t('referrals.badges.users', { count: signal.unique_users })}
                      tone="info"
                    />
                    <GrowthStatusChip
                      label={formatDateTime(signal.latest_event_at, locale)}
                      tone="neutral"
                    />
                  </div>

                  <p className="mt-4 text-sm font-mono leading-6 text-muted-foreground">
                    {signal.review_hint}
                  </p>
                </div>
              ))
            ) : (
              <GrowthEmptyState label={t('referrals.abuseQueueEmpty')} />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('referrals.breakdownTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('referrals.breakdownDescription')}
          </p>

          <div className="mt-5 flex flex-wrap gap-2">
            {(overview?.reward_status_breakdown ?? []).map((item) => (
              <GrowthStatusChip
                key={item.key}
                label={`${humanizeToken(item.key)} · ${formatCompactNumber(item.count, locale)}`}
                tone={item.key === 'blocked_by_risk' ? 'danger' : 'neutral'}
              />
            ))}
          </div>

          <div className="mt-6">
            <h3 className="text-sm font-display uppercase tracking-[0.2em] text-white">
              {t('referrals.lifecycleTitle')}
            </h3>
            <div className="mt-4 space-y-3">
              {referralEvents.length ? (
                referralEvents.slice(0, 6).map((event) => (
                  <div
                    key={event.id}
                    className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {humanizeToken(event.event_name)}
                      </p>
                      <GrowthStatusChip
                        label={humanizeToken(event.event_status)}
                        tone={event.event_status === 'published' ? 'success' : 'warning'}
                      />
                    </div>
                    <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                      {formatDateTime(event.occurred_at, locale)}
                    </p>
                  </div>
                ))
              ) : (
                <GrowthEmptyState label={t('referrals.lifecycleEmpty')} />
              )}
            </div>
          </div>
        </article>
      </div>
    </GrowthPageShell>
  );
}
