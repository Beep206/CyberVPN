'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import type { PricingCatalogData } from '@/widgets/pricing/types';
import { getCatalogDefaultPeriod } from '@/widgets/pricing/utils';
import type { TierLevel } from './pricing-dashboard';
import { TierCards } from './tier-cards';
import { cn } from '@/lib/utils';

interface HomePricingPreviewProps {
  catalog: PricingCatalogData;
}

export function HomePricingPreview({ catalog }: HomePricingPreviewProps) {
  const t = useTranslations('Pricing');
  const [hoveredTier, setHoveredTier] = useState<TierLevel>('plus');
  const [selectedPeriod, setSelectedPeriod] = useState<number>(() => getCatalogDefaultPeriod(catalog));

  return (
    <section className="relative overflow-hidden border-y border-grid-line/40 bg-background py-16 text-foreground dark:bg-black/70 md:py-20">
      <div className="mx-auto max-w-7xl space-y-9">
        <div className="mx-auto max-w-4xl px-4 text-center">
          <p className="font-mono text-xs uppercase tracking-widest text-neon-cyan md:text-sm">
            {t('subtitle')}
          </p>
          <h2 className="mt-4 font-display text-3xl font-black uppercase tracking-widest md:text-5xl">
            {t('title')}
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-6 text-muted-foreground md:text-base">
            {t('periods.helper')}
          </p>
        </div>

        <div className="mx-auto max-w-4xl px-4">
          <div className="grid gap-2 rounded-2xl border border-border/70 bg-card/70 p-2 backdrop-blur dark:border-white/10 dark:bg-white/[0.03] sm:grid-cols-2 lg:grid-cols-4">
            {catalog.periods.map((period) => {
              const isSelected = selectedPeriod === period;

              return (
                <button
                  key={period}
                  type="button"
                  onClick={() => setSelectedPeriod(period)}
                  className={cn(
                    'rounded-xl px-4 py-3 text-left transition-colors',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan/50',
                    isSelected
                      ? 'bg-neon-cyan/10 text-neon-cyan ring-1 ring-neon-cyan/40'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                  )}
                >
                  <span className="block font-display text-sm uppercase tracking-[0.18em]">
                    {t(`periods.options.${period}`)}
                  </span>
                  <span className="mt-1 block font-mono text-[11px] uppercase tracking-[0.16em]">
                    {period === 365 ? t('periods.best') : t('periods.term')}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <TierCards
          dedicatedIpAddonAvailable={catalog.addons.some((addon) => addon.code === 'dedicated_ip')}
          hoveredTier={hoveredTier}
          onHover={setHoveredTier}
          plans={catalog.plans}
          selectedPeriod={selectedPeriod}
        />
      </div>
    </section>
  );
}
