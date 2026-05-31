'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { CountrySelector } from '@/features/country-selector';
import { CurrencySelector } from '@/features/currency-selector';
import { isSupportedCurrency } from '@/features/currency-selector/currency-config';
import { useRouter } from '@/i18n/navigation';
import { useEnhancementReady } from '@/shared/hooks/use-enhancement-ready';
import { useVisualTier } from '@/shared/hooks/use-visual-tier';
import { ResponsiveSplitShell } from '@/shared/ui/layout/responsive-split-shell';
import type { PricingCatalogData, PricingTierCode } from '@/widgets/pricing/types';
import { getCatalogDefaultPeriod } from '@/widgets/pricing/utils';
import { TierCards } from './tier-cards';
import { FeatureMatrix } from './feature-matrix';
import { FAQAccordion } from './faq-accordion';

const PricingCore3D = dynamic(
  () => import('@/3d/scenes/PricingCore3D').then((mod) => mod.PricingCore3D),
  {
    ssr: false,
    loading: () => null,
  },
);

export type TierLevel = 'none' | PricingTierCode;

const TIER_VISUAL_STYLES: Record<
  TierLevel,
  {
    glowClassName: string;
    accentBorderClassName: string;
    accentTextClassName: string;
  }
> = {
  none: {
    glowClassName:
      'bg-[radial-gradient(circle_at_center,rgba(0,255,255,0.16),transparent_55%),linear-gradient(180deg,rgba(0,0,0,0.08)_0%,rgba(0,0,0,0.88)_100%)]',
    accentBorderClassName: 'border-neon-cyan/20',
    accentTextClassName: 'text-neon-cyan/70',
  },
  basic: {
    glowClassName:
      'bg-[radial-gradient(circle_at_center,rgba(0,255,255,0.2),transparent_55%),linear-gradient(180deg,rgba(0,0,0,0.08)_0%,rgba(0,10,14,0.88)_100%)]',
    accentBorderClassName: 'border-neon-cyan/30',
    accentTextClassName: 'text-neon-cyan/80',
  },
  plus: {
    glowClassName:
      'bg-[radial-gradient(circle_at_center,rgba(0,255,136,0.2),transparent_55%),linear-gradient(180deg,rgba(0,0,0,0.08)_0%,rgba(0,12,6,0.88)_100%)]',
    accentBorderClassName: 'border-matrix-green/30',
    accentTextClassName: 'text-matrix-green/80',
  },
  pro: {
    glowClassName:
      'bg-[radial-gradient(circle_at_center,rgba(255,0,255,0.16),transparent_55%),linear-gradient(180deg,rgba(0,0,0,0.08)_0%,rgba(12,0,8,0.88)_100%)]',
    accentBorderClassName: 'border-neon-pink/30',
    accentTextClassName: 'text-neon-pink/80',
  },
  max: {
    glowClassName:
      'bg-[radial-gradient(circle_at_center,rgba(255,0,255,0.18),transparent_55%),linear-gradient(180deg,rgba(0,0,0,0.08)_0%,rgba(10,0,12,0.88)_100%)]',
    accentBorderClassName: 'border-neon-purple/30',
    accentTextClassName: 'text-neon-purple/80',
  },
};

function PricingVisualFallback({
  hoveredTier,
  visualTier,
}: {
  hoveredTier: TierLevel;
  visualTier: 'minimal' | 'reduced' | 'full';
}) {
  const style = TIER_VISUAL_STYLES[hoveredTier];
  const tierLabel = hoveredTier === 'none' ? 'BASIC' : hoveredTier.toUpperCase();

  return (
    <div aria-hidden="true" data-visual-tier={visualTier} className="absolute inset-0 overflow-hidden">
      <div className={`absolute inset-0 ${style.glowClassName}`} />
      <div className="absolute inset-12 rounded-[2rem] border border-white/10 bg-[linear-gradient(165deg,rgba(255,255,255,0.03),rgba(0,0,0,0.86))]" />
      <div className={`absolute left-1/2 top-1/2 h-56 w-56 -translate-x-1/2 -translate-y-1/2 rotate-45 border ${style.accentBorderClassName}`} />
      <div className={`absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rotate-12 border ${style.accentBorderClassName} opacity-55`} />
      {visualTier === 'reduced' ? (
        <div className="absolute inset-x-10 bottom-10 flex flex-wrap items-center gap-3 font-mono text-[11px] tracking-[0.28em]">
          <span className={`rounded-full border px-4 py-2 ${style.accentBorderClassName} ${style.accentTextClassName}`}>
            TIER.{tierLabel}
          </span>
          <span className="rounded-full border border-white/10 px-4 py-2 text-white/60">
            STATIC CORE
          </span>
        </div>
      ) : null}
    </div>
  );
}

export function PricingDashboard({ catalog }: { catalog: PricingCatalogData }) {
  const t = useTranslations('Pricing');
  const router = useRouter();
  const [hoveredTier, setHoveredTier] = useState<TierLevel>('plus');
  const [selectedPeriod, setSelectedPeriod] = useState<number>(() => getCatalogDefaultPeriod(catalog));
  const { tier: visualTier, isFull } = useVisualTier();
  const { isReady: isSceneReady } = useEnhancementReady({
    minimumTier: 'full',
    defer: 'idle',
  });
  const hasPublicAddons = catalog.addons.length > 0;
  const dedicatedIpAddonAvailable = catalog.addons.some((addon) => addon.code === 'dedicated_ip');
  const showScene = visualTier === 'full' && isSceneReady;
  const sourceLabel = catalog.source === 'api' ? t('introPills.live') : t('introPills.unavailable');
  const defaultCurrency = isSupportedCurrency(catalog.context.currency)
    ? catalog.context.currency
    : undefined;
  const headerPills = [
    { label: t('introPills.plans') },
    { label: t('introPills.periods') },
    ...(hasPublicAddons ? [{ label: t('introPills.addons') }] : []),
    { label: sourceLabel },
  ];
  const refreshCatalog = () => {
    router.refresh();
  };

  const header = (
    <header className="mt-4 space-y-8 text-center">
      <p
        className={`mb-4 font-mono text-xs uppercase tracking-widest text-neon-cyan md:text-sm ${
          isFull ? 'animate-pulse' : ''
        }`}
      >
        {t('subtitle')}
      </p>
      <h1 className="font-display text-5xl font-black uppercase tracking-widest text-foreground shadow-black drop-shadow-2xl dark:text-white md:text-7xl">
        {t('title')}
      </h1>
      <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-center gap-3 px-4">
        {headerPills.map((pill) => (
          <span
            key={pill.label}
            className="rounded-full border border-border/60 bg-background/55 px-4 py-2 font-mono text-[11px] uppercase tracking-[0.24em] text-muted-foreground backdrop-blur dark:border-white/10 dark:bg-white/5 dark:text-white/70"
          >
            {pill.label}
          </span>
        ))}
      </div>
      <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-center gap-3 px-4">
        <div className="rounded-2xl border border-border/70 bg-card/70 px-4 py-3 backdrop-blur-xl dark:border-white/10 dark:bg-black/45">
          <p className="mb-2 text-center font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground">
            {t('commercialContext.title')}
          </p>
          <div className="flex flex-wrap items-center justify-center gap-2">
            <CountrySelector
              countries={catalog.context.selectableCountries}
              defaultCountry={catalog.context.displayCountry}
              onCountryChange={refreshCatalog}
            />
            <CurrencySelector
              availableCurrencies={catalog.context.selectableCurrencies}
              defaultCurrency={defaultCurrency}
              onCurrencyChange={refreshCatalog}
            />
          </div>
          <p className="mt-2 text-center font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
            {t('commercialContext.resolved', {
              country: catalog.context.pricingCountry,
              currency: catalog.context.currency,
            })}
          </p>
        </div>
      </div>
      <div className="mx-auto max-w-4xl rounded-[1.75rem] border border-border/70 bg-card/70 px-4 py-5 backdrop-blur-xl dark:border-white/10 dark:bg-black/45">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="text-left">
            <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-muted-foreground">
              {t('periods.label')}
            </p>
            <p className="mt-1 text-sm font-mono text-muted-foreground">
              {t('periods.helper')}
            </p>
          </div>
          <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-neon-cyan/70">
            {t('summary.selectedTerm', { days: selectedPeriod })}
          </p>
        </div>
        <div className="grid gap-3 md:grid-cols-4">
          {catalog.periods.map((period) => {
            const isSelected = selectedPeriod === period;
            return (
              <button
                key={period}
                type="button"
                onClick={() => setSelectedPeriod(period)}
                className={`rounded-2xl border px-4 py-3 text-left transition-all duration-300 ${
                  isSelected
                    ? 'border-neon-cyan bg-neon-cyan/10 shadow-[0_0_30px_rgba(0,255,255,0.12)]'
                    : 'border-border/70 bg-background/35 hover:border-border hover:bg-background/60 dark:border-white/10 dark:bg-white/[0.03] dark:hover:border-white/30 dark:hover:bg-white/[0.06]'
                }`}
              >
                <div className="font-display text-lg uppercase tracking-[0.18em] text-foreground dark:text-white">
                  {t(`periods.options.${period}`)}
                </div>
                <div className="mt-1 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground dark:text-white/55">
                  {period === 365 ? t('periods.best') : t('periods.term')}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );

  const content = (
    <div className="space-y-20 pb-12 md:space-y-24 lg:pb-24">
      {catalog.plans.length > 0 ? (
        <div className="relative z-20">
          <TierCards
            dedicatedIpAddonAvailable={dedicatedIpAddonAvailable}
            hoveredTier={hoveredTier}
            onHover={setHoveredTier}
            plans={catalog.plans}
            selectedPeriod={selectedPeriod}
          />
        </div>
      ) : (
        <div className="relative z-20 mx-auto max-w-3xl rounded-[1.75rem] border border-amber-400/30 bg-amber-400/10 p-6 text-center">
          <h2 className="font-display text-2xl uppercase tracking-[0.18em] text-amber-200">
            {t('catalog.unavailableTitle')}
          </h2>
          <p className="mt-3 font-mono text-sm leading-relaxed text-amber-100/75">
            {t('catalog.unavailableBody')}
          </p>
        </div>
      )}

      {catalog.plans.length > 0 ? (
        <div className="relative z-20 mx-auto max-w-5xl">
          <FeatureMatrix plans={catalog.plans} addons={catalog.addons} selectedPeriod={selectedPeriod} />
        </div>
      ) : null}

      <div className="relative z-20 mx-auto max-w-4xl">
        <FAQAccordion showAddonFaq={hasPublicAddons} />
      </div>
    </div>
  );

  const visual = (
    <div data-visual-tier={visualTier} className="absolute inset-0">
      {showScene ? (
        <PricingCore3D hoveredTier={hoveredTier} />
      ) : (
        <PricingVisualFallback
          hoveredTier={hoveredTier}
          visualTier={visualTier === 'full' ? 'reduced' : visualTier}
        />
      )}

      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-background via-transparent to-background dark:from-black dark:to-black" />
      <div className="pointer-events-none absolute left-0 top-0 h-full w-1/3 bg-gradient-to-r from-background dark:from-black" />
      <div className="pointer-events-none absolute right-0 top-0 h-full w-1/3 bg-gradient-to-l from-background dark:from-black" />
    </div>
  );

  return (
    <ResponsiveSplitShell
      className="min-h-[calc(100dvh-4rem)] overflow-x-hidden bg-background text-foreground"
      containerClassName="max-w-7xl"
      contentStackClassName="gap-10 md:gap-16"
      headerClassName="relative z-10"
      header={header}
      content={content}
      visual={visual}
      visualMode="background"
      visualPaneClassName="pointer-events-none hidden lg:block"
    />
  );
}
