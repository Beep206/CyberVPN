'use client';

import { useQuery } from '@tanstack/react-query';
import { Activity, ArrowUpRight, Globe2, Radar, ShieldAlert } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { publicNetworkApi } from '@/lib/api';
import { Link } from '@/i18n/navigation';
import { pollingInterval } from '@/features/network-intelligence/lib/public-network';

function formatDateTime(value: string, locale: string) {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function DpiResistanceDashboard() {
  const locale = useLocale();
  const t = useTranslations('Network.dpi');
  const dpiScoreQuery = useQuery({
    queryKey: ['public-network-dpi-score'],
    queryFn: async () => {
      const { data } = await publicNetworkApi.getDpiScore();
      return data;
    },
    staleTime: 30_000,
    refetchInterval: pollingInterval(30_000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    retry: false,
  });

  const dpiScore = dpiScoreQuery.data;
  const publishedCountries = dpiScore?.countries.slice(0, 4) ?? [];

  const summaryCards = [
    {
      key: 'methodology',
      icon: Radar,
      label: t('cards.methodology'),
      value: dpiScore?.methodologyVersion ?? '—',
    },
    {
      key: 'confidence',
      icon: ShieldAlert,
      label: t('cards.confidence'),
      value: dpiScore?.confidence ? t(`confidenceValues.${dpiScore.confidence}`) : '—',
    },
    {
      key: 'countries',
      icon: Globe2,
      label: t('cards.countriesTracked'),
      value: typeof dpiScore?.countriesTracked === 'number' ? String(dpiScore.countriesTracked) : '—',
    },
    {
      key: 'window',
      icon: Activity,
      label: t('cards.measurementWindow'),
      value: dpiScore?.measurementWindow
        ? t('windowValue', { hours: dpiScore.measurementWindow.hours })
        : '—',
    },
  ];

  return (
    <section className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-black text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(0,255,255,0.12),transparent_32%),radial-gradient(circle_at_80%_20%,rgba(0,255,136,0.12),transparent_28%),linear-gradient(180deg,rgba(2,4,10,1)_0%,rgba(3,7,14,1)_100%)]" />
      <div className="absolute inset-0 opacity-20 [background-image:linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px)] [background-size:3.5rem_3.5rem]" />

      <div className="relative z-10 mx-auto flex w-full max-w-[1440px] flex-col gap-8 px-6 pb-16 pt-24 md:px-8 lg:px-12">
        <header className="max-w-4xl">
          <p className="text-[11px] font-mono uppercase tracking-[0.28em] text-neon-cyan/80">
            {t('eyebrow')}
          </p>
          <h1 className="mt-3 font-display text-4xl font-black uppercase tracking-[0.12em] text-white md:text-5xl">
            {t('title')}
          </h1>
          <p className="mt-4 max-w-3xl text-sm font-mono leading-7 text-white/68 md:text-base">
            {t('description')}
          </p>
        </header>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <article className="rounded-[1.75rem] border border-white/10 bg-black/35 p-6 backdrop-blur-xl">
            <div className="grid gap-4 md:grid-cols-2">
              {summaryCards.map((card) => (
                <div
                  key={card.key}
                  className="rounded-2xl border border-white/8 bg-white/[0.03] p-4 shadow-[0_0_24px_rgba(0,255,255,0.04)]"
                >
                  <div className="flex items-center gap-2">
                    <card.icon className="h-4 w-4 text-neon-cyan" />
                    <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-white/45">
                      {card.label}
                    </p>
                  </div>
                  <p className="mt-3 text-lg font-display uppercase tracking-[0.08em] text-white">
                    {card.value}
                  </p>
                </div>
              ))}
            </div>

            <div className="mt-6 rounded-[1.5rem] border border-amber-300/20 bg-amber-300/6 p-5">
              <p className="text-[11px] font-mono uppercase tracking-[0.24em] text-amber-200/80">
                {t('gating.eyebrow')}
              </p>
              {dpiScoreQuery.isPending ? (
                <p className="mt-3 text-sm font-mono leading-6 text-white/70">{t('loading')}</p>
              ) : dpiScoreQuery.isError || !dpiScore ? (
                <p className="mt-3 text-sm font-mono leading-6 text-rose-200">{t('error')}</p>
              ) : dpiScore.enabled ? (
                <div className="mt-3 space-y-3">
                  <p className="text-sm font-mono leading-6 text-white/75">
                    {t('enabledState')}
                  </p>
                  {dpiScore.lastUpdatedAt ? (
                    <p className="text-xs font-mono uppercase tracking-[0.18em] text-white/45">
                      {t('lastUpdated', { value: formatDateTime(dpiScore.lastUpdatedAt, locale) })}
                    </p>
                  ) : null}
                  {publishedCountries.length > 0 ? (
                    <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
                      <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-white/45">
                        {t('publishedCountries.title')}
                      </p>
                      <div className="mt-4 space-y-3">
                        {publishedCountries.map((country) => (
                          <div
                            key={country.countryCode}
                            className="rounded-2xl border border-white/8 bg-black/30 p-4"
                          >
                            <div className="flex items-start justify-between gap-4">
                              <div>
                                <p className="text-sm font-display uppercase tracking-[0.12em] text-white">
                                  {country.publicName}
                                </p>
                                <p className="mt-1 text-[11px] font-mono uppercase tracking-[0.18em] text-white/45">
                                  {t('publishedCountries.updated', {
                                    value: country.lastUpdatedAt
                                      ? formatDateTime(country.lastUpdatedAt, locale)
                                      : '—',
                                  })}
                                </p>
                              </div>
                              <div className="text-right">
                                <p className="text-xl font-display uppercase tracking-[0.08em] text-neon-cyan">
                                  {country.score}
                                </p>
                                <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-white/45">
                                  {t(`confidenceValues.${country.confidence}`)}
                                </p>
                              </div>
                            </div>

                            <div className="mt-4 grid gap-3">
                              {country.protocols.slice(0, 2).map((protocol) => (
                                <div
                                  key={`${country.countryCode}-${protocol.protocol}`}
                                  className="rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2"
                                >
                                  <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-matrix-green">
                                    {protocol.protocol}
                                  </p>
                                  <div className="mt-2 flex flex-wrap gap-3 text-[11px] font-mono uppercase tracking-[0.14em] text-white/55">
                                    <span>
                                      {t('publishedCountries.score')} {protocol.successRate.toFixed(0)}%
                                    </span>
                                    {protocol.httpsBaselineSuccessRate != null ? (
                                      <span>
                                        {t('publishedCountries.baseline')}{' '}
                                        {protocol.httpsBaselineSuccessRate.toFixed(0)}%
                                      </span>
                                    ) : null}
                                    {protocol.medianHandshakeMs != null ? (
                                      <span>
                                        {t('publishedCountries.handshake')}{' '}
                                        {protocol.medianHandshakeMs}ms
                                      </span>
                                    ) : null}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="mt-3 space-y-3">
                  <p className="text-sm font-mono leading-6 text-white/75">
                    {t('disabledState')}
                  </p>
                  <p className="text-xs font-mono uppercase tracking-[0.18em] text-white/45">
                    {t(`reasonCodes.${dpiScore.reasonCode ?? 'public_dpi_not_enabled'}`)}
                  </p>
                </div>
              )}
            </div>
          </article>

          <div className="space-y-6">
            <article className="rounded-[1.75rem] border border-white/10 bg-black/35 p-6 backdrop-blur-xl">
              <p className="text-[11px] font-mono uppercase tracking-[0.24em] text-neon-cyan/80">
                {t('methodology.eyebrow')}
              </p>
              <h2 className="mt-3 text-2xl font-display uppercase tracking-[0.12em] text-white">
                {t('methodology.title')}
              </h2>
              <ul className="mt-5 space-y-3">
                {['connection', 'handshake', 'baseline', 'survival', 'freshness'].map((item) => (
                  <li
                    key={item}
                    className="rounded-2xl border border-white/8 bg-white/[0.03] px-4 py-3 text-sm font-mono leading-6 text-white/72"
                  >
                    {t(`methodology.items.${item}`)}
                  </li>
                ))}
              </ul>
            </article>

            <article className="rounded-[1.75rem] border border-white/10 bg-black/35 p-6 backdrop-blur-xl">
              <p className="text-[11px] font-mono uppercase tracking-[0.24em] text-neon-cyan/80">
                {t('guardrails.eyebrow')}
              </p>
              <h2 className="mt-3 text-2xl font-display uppercase tracking-[0.12em] text-white">
                {t('guardrails.title')}
              </h2>
              <ul className="mt-5 space-y-3">
                {['noMagic', 'noInternals', 'directional', 'conditionsChange'].map((item) => (
                  <li
                    key={item}
                    className="rounded-2xl border border-white/8 bg-white/[0.03] px-4 py-3 text-sm font-mono leading-6 text-white/72"
                  >
                    {t(`guardrails.items.${item}`)}
                  </li>
                ))}
              </ul>
            </article>

            <article className="rounded-[1.75rem] border border-white/10 bg-black/35 p-6 backdrop-blur-xl">
              <p className="text-[11px] font-mono uppercase tracking-[0.24em] text-neon-cyan/80">
                {t('links.eyebrow')}
              </p>
              <div className="mt-4 flex flex-col gap-3">
                <Link
                  href="/network"
                  className="inline-flex items-center gap-2 text-sm font-mono text-neon-cyan underline underline-offset-4"
                >
                  <span>{t('links.network')}</span>
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </Link>
                <Link
                  href="/guides/how-to-bypass-dpi-with-vless-reality"
                  className="inline-flex items-center gap-2 text-sm font-mono text-matrix-green underline underline-offset-4"
                >
                  <span>{t('links.guide')}</span>
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </article>
          </div>
        </div>
      </div>
    </section>
  );
}
