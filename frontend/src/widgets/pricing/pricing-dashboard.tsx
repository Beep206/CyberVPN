'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { PricingCore3D } from '@/3d/scenes/PricingCore3D';
import { TierCards } from './tier-cards';
import { FeatureMatrix } from './feature-matrix';
import { FAQAccordion } from './faq-accordion';

export type TierLevel = 'none' | 'basic' | 'pro' | 'elite';

export function PricingDashboard() {
    const t = useTranslations('Pricing');
    const [hoveredTier, setHoveredTier] = useState<TierLevel>('none');

    return (
        <div className="relative w-full h-full flex-1 flex flex-col bg-black overflow-x-hidden">
            {/* 3D Background Layer */}
            <div className="absolute inset-0 z-0 hidden lg:block">
                <PricingCore3D hoveredTier={hoveredTier} />
                
                {/* Advanced Light Bleed Overlays */}
                <div className="absolute inset-0 bg-gradient-to-b from-black via-transparent to-black pointer-events-none" />
                <div className="absolute top-0 right-0 w-1/3 h-full bg-gradient-to-l from-black pointer-events-none" />
                <div className="absolute top-0 left-0 w-1/3 h-full bg-gradient-to-r from-black pointer-events-none" />
            </div>

            {/* UI Foreground Layer */}
            <div className="relative z-10 w-full p-4 md:p-12 flex flex-col pointer-events-none max-w-7xl mx-auto">
                <header className="mb-16 pointer-events-auto mt-8 text-center pointer-events-none">
                    <p className="text-neon-cyan font-mono text-xs md:text-sm tracking-widest uppercase mb-4 animate-pulse">
                        {t('subtitle')}
                    </p>
                    <h1 className="text-5xl md:text-7xl font-display font-black text-white tracking-widest uppercase shadow-black drop-shadow-2xl">
                        {t('title')}
                    </h1>
                </header>

                <div className="pointer-events-auto space-y-32 pb-24">
                    {/* Tiers Module */}
                    <div className="relative z-20">
                        <TierCards hoveredTier={hoveredTier} onHover={setHoveredTier} />
                    </div>

                    {/* Features Matrix Module */}
                    <div className="relative z-20 max-w-5xl mx-auto">
                        <FeatureMatrix />
                    </div>

                    {/* FAQ Module */}
                    <div className="relative z-20 max-w-4xl mx-auto">
                         <FAQAccordion />
                    </div>
                </div>
            </div>
        </div>
    );
}
