'use client';

import {
  Gift,
  TicketPlus,
  TrendingUp,
  UserRoundPlus,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { plansApi } from '@/lib/api/plans';
import { growthApi } from '@/lib/api/growth';
import { GrowthEmptyState } from '@/features/growth/components/growth-empty-state';
import { GrowthPageShell } from '@/features/growth/components/growth-page-shell';
import { GrowthStatusChip } from '@/features/growth/components/growth-status-chip';
import {
  formatCompactNumber,
  formatDateTime,
  formatCurrencyAmount,
  shortId,
} from '@/features/growth/lib/formatting';

export function GrowthOverview() {
  const t = useTranslations('Growth');
  const locale = useLocale();

  const promosQuery = useQuery({
    queryKey: ['growth', 'promo-codes', 'overview'],
    queryFn: async () => {
      const response = await growthApi.listPromos({ offset: 0, limit: 20 });
      return response.data;
    },
    staleTime: 30_000,
  });

  const plansQuery = useQuery({
    queryKey: ['growth', 'plans', 'overview'],
    queryFn: async () => {
      const response = await plansApi.list();
      return response.data;
    },
    staleTime: 60_000,
  });

  const promos = promosQuery.data ?? [];
  const plans = plansQuery.data ?? [];
  const referenceNow = promosQuery.dataUpdatedAt || 0;
  const expiringSoon = promos.filter((promo) => {
    if (!promo.expires_at) {
      return false;
    }

    const expiresAt = new Date(promo.expires_at).getTime();
    return (
      expiresAt >= referenceNow
      && expiresAt <= referenceNow + 7 * 24 * 60 * 60 * 1000
    );
  }).length;
  const exhausted = promos.filter(
    (promo) => promo.max_uses !== null && promo.current_uses >= promo.max_uses,
  ).length;

  return (
    <GrowthPageShell
      eyebrow={t('overview.eyebrow')}
      title={t('overview.title')}
      description={t('overview.description')}
      icon={TrendingUp}
      metrics={[
        {
          label: t('overview.metrics.promos'),
          value: formatCompactNumber(promos.length, locale),
          hint: t('overview.metrics.promosHint'),
          tone: 'info',
        },
        {
          label: t('overview.metrics.activePromos'),
          value: formatCompactNumber(
            promos.filter((promo) => promo.is_active).length,
            locale,
          ),
          hint: t('overview.metrics.activePromosHint'),
          tone: 'success',
        },
        {
          label: t('overview.metrics.expiring'),
          value: formatCompactNumber(expiringSoon, locale),
          hint: t('overview.metrics.expiringHint'),
          tone: expiringSoon > 0 ? 'warning' : 'neutral',
        },
        {
          label: t('overview.metrics.plans'),
          value: formatCompactNumber(plans.length, locale),
          hint: t('overview.metrics.plansHint'),
          tone: 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('overview.routesTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('overview.routesDescription')}
          </p>
          <div className="mt-5 grid gap-3">
            {[
              {
                href: '/growth/promo-codes',
                title: t('nav.promoCodes'),
                description: t('overview.routes.promoCodes'),
                icon: Gift,
              },
              {
                href: '/growth/invite-codes',
                title: t('nav.inviteCodes'),
                description: t('overview.routes.inviteCodes'),
                icon: TicketPlus,
              },
              {
                href: '/growth/partners',
                title: t('nav.partners'),
                description: t('overview.routes.partners'),
                icon: UserRoundPlus,
              },
              {
                href: '/growth/referrals',
                title: t('nav.referrals'),
                description: t('overview.routes.referrals'),
                icon: TrendingUp,
              },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4 transition-colors hover:border-neon-cyan/35 hover:bg-terminal-bg/60"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
                    <item.icon className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-sm font-display uppercase tracking-[0.18em] text-white">
                      {item.title}
                    </p>
                    <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                      {item.description}
                    </p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.liveInventoryTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('overview.liveInventoryDescription')}
              </p>
            </div>
            <GrowthStatusChip
              label={t('overview.partialCoverage')}
              tone="warning"
            />
          </div>

          <div className="mt-5 space-y-3">
            {promos.length ? (
              promos.slice(0, 5).map((promo) => (
                <div
                  key={promo.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {promo.code}
                      </p>
                      <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        #{shortId(promo.id)} / {promo.discount_type} / {promo.discount_type === 'percent'
                          ? `${promo.discount_value}%`
                          : formatCurrencyAmount(promo.discount_value, promo.currency, locale)}
                      </p>
                    </div>
                    <GrowthStatusChip
                      label={promo.is_active ? t('common.active') : t('common.inactive')}
                      tone={promo.is_active ? 'success' : 'warning'}
                    />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <GrowthStatusChip
                      label={t('overview.usesLabel', {
                        current: promo.current_uses,
                        max: promo.max_uses ?? '∞',
                      })}
                      tone={
                        promo.max_uses !== null && promo.current_uses >= promo.max_uses
                          ? 'danger'
                          : 'info'
                      }
                    />
                    <GrowthStatusChip
                      label={
                        promo.expires_at
                          ? formatDateTime(promo.expires_at, locale)
                          : t('common.noExpiry')
                      }
                      tone={promo.expires_at ? 'neutral' : 'warning'}
                    />
                  </div>
                </div>
              ))
            ) : (
              <GrowthEmptyState label={t('common.empty')} />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('overview.operatorNotesTitle')}
          </h2>
          <div className="mt-5 space-y-3">
            {[
              {
                title: t('overview.operatorNotes.invitesTitle'),
                description: t('overview.operatorNotes.invitesDescription'),
                tone: 'warning' as const,
              },
              {
                title: t('overview.operatorNotes.partnersTitle'),
                description: t('overview.operatorNotes.partnersDescription'),
                tone: 'warning' as const,
              },
              {
                title: t('overview.operatorNotes.referralsTitle'),
                description: t('overview.operatorNotes.referralsDescription'),
                tone: 'danger' as const,
              },
            ].map((item) => (
              <div
                key={item.title}
                className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                    {item.title}
                  </p>
                  <GrowthStatusChip
                    label={t('common.backendLimited')}
                    tone={item.tone}
                  />
                </div>
                <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('overview.planTargetingTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('overview.planTargetingDescription')}
          </p>
          <div className="mt-5 grid gap-3">
            {plans.length ? (
              plans.slice(0, 5).map((plan) => (
                <div
                  key={plan.uuid}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {plan.display_name}
                      </p>
                      <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        #{shortId(plan.uuid)} / {formatCurrencyAmount(plan.price_usd, 'USD', locale)}
                      </p>
                    </div>
                    <GrowthStatusChip
                      label={plan.is_active ? t('common.active') : t('common.inactive')}
                      tone={plan.is_active ? 'success' : 'warning'}
                    />
                  </div>
                </div>
              ))
            ) : (
              <GrowthEmptyState label={t('overview.noPlans')} />
            )}
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-muted-foreground">
                {t('overview.quickSignals.exhausted')}
              </p>
              <p className="mt-2 text-2xl font-display tracking-[0.12em] text-neon-pink">
                {formatCompactNumber(exhausted, locale)}
              </p>
            </div>
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-muted-foreground">
                {t('overview.quickSignals.coverage')}
              </p>
              <p className="mt-2 text-2xl font-display tracking-[0.12em] text-neon-cyan">
                {t('overview.quickSignals.coverageValue')}
              </p>
            </div>
          </div>
        </article>
      </div>
    </GrowthPageShell>
  );
}
