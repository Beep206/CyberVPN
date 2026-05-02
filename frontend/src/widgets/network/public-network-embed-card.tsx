'use client';

import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ArrowUpRight, Gauge, Globe2, RadioTower, ShieldCheck } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { publicNetworkApi } from '@/lib/api';
import {
  formatAvailability,
  formatCount,
  formatTraffic,
  pollingInterval,
  resolveCountryLabel,
} from '@/features/network-intelligence/lib/public-network';
import type {
  PublicNetworkWidgetThemeVariant,
  PublicNetworkWidgetType,
} from '@/lib/api/public-network';

type PublicNetworkEmbedCardProps = {
  locale: string;
  themeVariant: PublicNetworkWidgetThemeVariant;
  widgetType: PublicNetworkWidgetType;
  regionId?: string;
};

const THEME_STYLES: Record<
  PublicNetworkWidgetThemeVariant,
  {
    shell: string;
    accent: string;
    badge: string;
    chip: string;
  }
> = {
  cyber: {
    shell:
      'border-neon-cyan/20 bg-[radial-gradient(circle_at_top,rgba(0,255,255,0.14),transparent_36%),linear-gradient(160deg,rgba(4,10,20,0.98),rgba(2,5,12,0.96))] shadow-[0_0_48px_rgba(0,255,255,0.12)]',
    accent: 'text-neon-cyan',
    badge: 'border-neon-cyan/25 bg-neon-cyan/10 text-neon-cyan',
    chip: 'border-neon-cyan/20 bg-neon-cyan/8 text-neon-cyan/90',
  },
  matrix: {
    shell:
      'border-matrix-green/20 bg-[radial-gradient(circle_at_top,rgba(0,255,136,0.15),transparent_34%),linear-gradient(160deg,rgba(1,12,7,0.98),rgba(1,8,5,0.96))] shadow-[0_0_48px_rgba(0,255,136,0.12)]',
    accent: 'text-matrix-green',
    badge: 'border-matrix-green/25 bg-matrix-green/10 text-matrix-green',
    chip: 'border-matrix-green/20 bg-matrix-green/8 text-matrix-green/90',
  },
  graphite: {
    shell:
      'border-white/10 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.12),transparent_32%),linear-gradient(160deg,rgba(14,18,24,0.98),rgba(7,9,13,0.96))] shadow-[0_0_48px_rgba(255,255,255,0.08)]',
    accent: 'text-white',
    badge: 'border-white/15 bg-white/8 text-white',
    chip: 'border-white/10 bg-white/5 text-white/80',
  },
};

function resolveWidgetStatusTone(status: 'online' | 'degraded' | 'major_outage') {
  if (status === 'online') {
    return 'text-matrix-green';
  }
  if (status === 'degraded') {
    return 'text-amber-300';
  }
  return 'text-rose-300';
}

export function PublicNetworkEmbedCard({
  locale,
  themeVariant,
  widgetType,
  regionId,
}: PublicNetworkEmbedCardProps) {
  const t = useTranslations('Network.widget');
  const theme = THEME_STYLES[themeVariant];
  const widgetQuery = useQuery({
    queryKey: ['public-network-widget', locale, themeVariant, widgetType, regionId ?? null],
    queryFn: async () => {
      const { data } = await publicNetworkApi.getWidget({
        locale,
        themeVariant,
        widgetType,
        regionId,
      });
      return data;
    },
    staleTime: 30_000,
    refetchInterval: pollingInterval(30_000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    retry: false,
  });

  if (widgetQuery.isPending) {
    return (
      <div className={`mx-auto w-full max-w-[440px] rounded-[1.75rem] border p-5 ${theme.shell}`}>
        <div className="space-y-3 font-mono text-sm text-white/70">
          <p className="text-[11px] uppercase tracking-[0.28em] text-white/45">{t('eyebrow')}</p>
          <p>{t('loading')}</p>
        </div>
      </div>
    );
  }

  if (widgetQuery.isError || !widgetQuery.data) {
    return (
      <div className={`mx-auto w-full max-w-[440px] rounded-[1.75rem] border p-5 ${theme.shell}`}>
        <div className="flex items-start gap-3 font-mono text-sm text-rose-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="text-[11px] uppercase tracking-[0.28em] text-white/45">{t('eyebrow')}</p>
            <p className="mt-2">{t('error')}</p>
          </div>
        </div>
      </div>
    );
  }

  const widget = widgetQuery.data;
  const statusTone = resolveWidgetStatusTone(widget.summary.status);
  const availability = formatAvailability(widget.summary.currentAvailabilityPct, locale);
  const monthlyTraffic = formatTraffic(widget.summary.monthlyTrafficBytes, locale);
  const liveUsers = formatCount(widget.summary.activeUsers, locale);
  const onlineServers = formatCount(widget.summary.onlineServers, locale);
  const generatedAt = new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(widget.generatedAt));

  const metricCards = [
    {
      key: 'availability',
      icon: ShieldCheck,
      label: t('metrics.availability'),
      value: availability,
    },
    {
      key: 'servers',
      icon: RadioTower,
      label: t('metrics.onlineServers'),
      value: onlineServers,
    },
    {
      key: 'users',
      icon: Globe2,
      label: t('metrics.liveUsers'),
      value: liveUsers,
    },
  ];

  if (widgetType !== 'uptime_badge') {
    metricCards.push({
      key: 'traffic',
      icon: Gauge,
      label: t('metrics.monthlyTraffic'),
      value: monthlyTraffic,
    });
  }

  return (
    <article
      data-widget-type={widgetType}
      data-theme-variant={themeVariant}
      className={`mx-auto w-full max-w-[440px] overflow-hidden rounded-[1.75rem] border p-5 text-white ${theme.shell}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.28em] text-white/45">
            {t('eyebrow')}
          </p>
          <h1 className="mt-3 text-xl font-display uppercase tracking-[0.14em] text-white">
            {t('title')}
          </h1>
          <p className="mt-2 max-w-[28rem] text-sm font-mono leading-6 text-white/65">
            {t('description')}
          </p>
        </div>

        <div className={`rounded-full border px-3 py-1 text-[11px] font-mono uppercase tracking-[0.2em] ${theme.badge}`}>
          {widgetType.replace('_', ' ')}
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <span className={`rounded-full border px-3 py-1 text-[11px] font-mono uppercase tracking-[0.22em] ${theme.chip} ${statusTone}`}>
          {t(`statusValues.${widget.summary.status}`)}
        </span>
        <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-white/45">
          {t('freshness', { value: generatedAt })}
        </span>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        {metricCards.map((metric) => (
          <div key={metric.key} className="rounded-2xl border border-white/8 bg-black/20 p-4">
            <div className="flex items-center gap-2">
              <metric.icon className={`h-4 w-4 ${theme.accent}`} />
              <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-white/45">
                {metric.label}
              </span>
            </div>
            <p className="mt-3 text-xl font-display tracking-[0.08em] text-white">{metric.value}</p>
          </div>
        ))}
      </div>

      {widget.focusRegion ? (
        <section className="mt-5 rounded-2xl border border-white/8 bg-black/20 p-4">
          <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-white/45">
            {t('focusRegion')}
          </p>
          <div className="mt-3 flex items-center justify-between gap-3">
            <div>
              <p className="text-lg font-display uppercase tracking-[0.08em] text-white">
                {resolveCountryLabel(widget.focusRegion.countryCode, locale)}
              </p>
              <p className="mt-1 text-sm font-mono text-white/55">
                {t(`statusValues.${widget.focusRegion.status === 'offline' ? 'major_outage' : widget.focusRegion.status}`)}
              </p>
            </div>
            <div className="text-right text-sm font-mono text-white/65">
              <p>{t('regionServers', { value: formatCount(widget.focusRegion.onlineServers, locale) })}</p>
              <p>{t('regionUsers', { value: formatCount(widget.focusRegion.activeUsers, locale) })}</p>
            </div>
          </div>
        </section>
      ) : null}

      {widget.topRegions.length > 0 ? (
        <section className="mt-5 rounded-2xl border border-white/8 bg-black/20 p-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-white/45">
              {t('topRegions')}
            </p>
            <p className="text-xs font-mono text-white/45">
              {t('incidents', { value: formatCount(widget.summary.incidentsCount, locale) })}
            </p>
          </div>

          <div className="mt-3 space-y-2">
            {widget.topRegions.map((region) => (
              <div
                key={region.id}
                className="flex items-center justify-between gap-3 rounded-xl border border-white/6 px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-display uppercase tracking-[0.08em] text-white">
                    {resolveCountryLabel(region.countryCode, locale)}
                  </p>
                  <p className="text-xs font-mono text-white/45">
                    {t('regionServers', { value: formatCount(region.onlineServers, locale) })}
                  </p>
                </div>
                <div className="text-right text-sm font-mono text-white/70">
                  <p>#{region.rank}</p>
                  <p>{formatCount(region.activeUsers, locale)}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <footer className="mt-5 flex items-center justify-between gap-3 border-t border-white/8 pt-4">
        <a
          href={`/${locale}/network`}
          target="_blank"
          rel="noreferrer"
          className={`inline-flex items-center gap-2 text-sm font-mono uppercase tracking-[0.18em] ${theme.accent}`}
        >
          {t('actions.fullMap')}
          <ArrowUpRight className="h-4 w-4" />
        </a>

        <a
          href={`/${locale}/status`}
          target="_blank"
          rel="noreferrer"
          className="text-xs font-mono uppercase tracking-[0.16em] text-white/55 transition-colors hover:text-white"
        >
          {t('actions.statusPage')}
        </a>
      </footer>
    </article>
  );
}
