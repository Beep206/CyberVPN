'use client';

import dynamic from 'next/dynamic';
import { useEffect, useRef, useState } from 'react';
import { useEnhancementReady } from '@/shared/hooks/use-enhancement-ready';
import type { VisualTier } from '@/shared/hooks/use-visual-tier';
import { ResponsiveSplitShell } from '@/shared/ui/layout/responsive-split-shell';
import { PrivacyIndex } from './privacy-index';
import { PrivacyContent } from './privacy-content';

// Lazy load the 3D scene to prevent SSR issues
const PrivacyVault3D = dynamic(() => import('@/3d/scenes/PrivacyVault3D'), { ssr: false });

export type PrivacySectionId = 'introduction' | 'dataCollection' | 'noLogs' | 'encryption' | 'thirdParties';

function PrivacyVisualFallback({
    activeSection,
    visualTier,
}: {
    activeSection: PrivacySectionId;
    visualTier: VisualTier;
}) {
    const accentMap: Record<PrivacySectionId, { borderClassName: string; glowClassName: string; label: string }> = {
        introduction: {
            borderClassName: 'border-white/20',
            glowClassName:
                'bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.14),transparent_52%),linear-gradient(180deg,rgba(0,0,0,0.04)_0%,rgba(0,0,0,0.92)_100%)]',
            label: 'PRIVACY.CORE',
        },
        dataCollection: {
            borderClassName: 'border-warning/30',
            glowClassName:
                'bg-[radial-gradient(circle_at_center,rgba(255,184,0,0.18),transparent_52%),linear-gradient(180deg,rgba(0,0,0,0.04)_0%,rgba(16,10,0,0.92)_100%)]',
            label: 'DATA.MINIMUM',
        },
        noLogs: {
            borderClassName: 'border-matrix-green/30',
            glowClassName:
                'bg-[radial-gradient(circle_at_center,rgba(0,255,136,0.18),transparent_52%),linear-gradient(180deg,rgba(0,0,0,0.04)_0%,rgba(0,12,8,0.92)_100%)]',
            label: 'NO.LOGS',
        },
        encryption: {
            borderClassName: 'border-neon-cyan/30',
            glowClassName:
                'bg-[radial-gradient(circle_at_center,rgba(0,255,255,0.18),transparent_52%),linear-gradient(180deg,rgba(0,0,0,0.04)_0%,rgba(0,9,14,0.92)_100%)]',
            label: 'ENCRYPTION.LAYER',
        },
        thirdParties: {
            borderClassName: 'border-neon-purple/30',
            glowClassName:
                'bg-[radial-gradient(circle_at_center,rgba(255,0,255,0.16),transparent_52%),linear-gradient(180deg,rgba(0,0,0,0.04)_0%,rgba(10,0,12,0.92)_100%)]',
            label: 'VENDOR.BOUNDARY',
        },
    };

    const accent = accentMap[activeSection];

    return (
        <div aria-hidden="true" data-visual-tier={visualTier} className="absolute inset-0 overflow-hidden">
            <div className={`absolute inset-0 ${accent.glowClassName}`} />
            <div className="absolute inset-8 rounded-[2rem] border border-white/10 bg-[linear-gradient(165deg,rgba(255,255,255,0.03),rgba(0,0,0,0.9))]" />
            <div className={`absolute left-1/2 top-1/2 h-52 w-52 -translate-x-1/2 -translate-y-1/2 rounded-[1.75rem] border ${accent.borderClassName} rotate-12`} />
            <div className={`absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-[2rem] border ${accent.borderClassName} opacity-45 -rotate-6`} />
            <div className="absolute inset-x-14 top-14 grid gap-4 opacity-75">
                <div className="h-4 rounded-full bg-white/10" />
                <div className="grid grid-cols-3 gap-3">
                    <div className="h-16 rounded-2xl border border-white/10 bg-black/35" />
                    <div className="h-24 rounded-2xl border border-white/10 bg-white/[0.04]" />
                    <div className="h-16 rounded-2xl border border-white/10 bg-black/35" />
                </div>
            </div>
            {visualTier === 'reduced' ? (
                <div className="absolute inset-x-10 bottom-10 flex flex-wrap items-center gap-3 font-mono text-[11px] tracking-[0.28em]">
                    <span className={`rounded-full border px-4 py-2 ${accent.borderClassName} text-white/80`}>
                        {accent.label}
                    </span>
                    <span className="rounded-full border border-white/10 px-4 py-2 text-white/60">
                        SECTION.{activeSection.toUpperCase()}
                    </span>
                </div>
            ) : null}
        </div>
    );
}

export function PrivacyDashboard() {
    const { isReady: isSceneReady, tier: visualTier } = useEnhancementReady({
        minimumTier: 'full',
        defer: 'idle',
    });
    const [activeSection, setActiveSection] = useState<PrivacySectionId>('introduction');
    const [scrollDepth, setScrollDepth] = useState(0);
    const rootRef = useRef<HTMLDivElement>(null);
    const showScene = visualTier === 'full' && isSceneReady;

    useEffect(() => {
        if (!showScene) {
            return;
        }

        const updateScrollDepth = () => {
            if (!rootRef.current) {
                return;
            }

            const rect = rootRef.current.getBoundingClientRect();
            const totalScrollable = Math.max(rootRef.current.offsetHeight - window.innerHeight, 1);
            const scrolled = Math.min(Math.max(-rect.top, 0), totalScrollable);
            setScrollDepth(totalScrollable <= 1 ? 0 : scrolled / totalScrollable);
        };

        updateScrollDepth();
        window.addEventListener('scroll', updateScrollDepth, { passive: true });
        window.addEventListener('resize', updateScrollDepth);

        return () => {
            window.removeEventListener('scroll', updateScrollDepth);
            window.removeEventListener('resize', updateScrollDepth);
        };
    }, [showScene]);

    const content = (
        <div
            ref={rootRef}
            data-testid="privacy-dashboard-content"
            className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)] lg:gap-10"
        >
            <div
                data-testid="privacy-dashboard-main"
                className="order-1 lg:order-2 min-w-0 rounded-[1.75rem] border border-grid-line/30 bg-black/55 backdrop-blur-xl"
            >
                <PrivacyContent setActiveSection={setActiveSection} />
            </div>

            <div
                data-testid="privacy-dashboard-sidebar"
                className="order-2 lg:order-1 min-w-0 rounded-[1.75rem] border border-grid-line/30 bg-black/60 backdrop-blur-xl lg:sticky lg:top-24 lg:self-start"
            >
                <PrivacyIndex activeSection={activeSection} setActiveSection={setActiveSection} />
            </div>
        </div>
    );

    const visual = (
        <div className="absolute inset-0 bg-[#020205] overflow-hidden">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.9)_100%)] z-10 pointer-events-none" />
            {showScene ? (
                <PrivacyVault3D activeSection={activeSection} scrollDepth={scrollDepth} />
            ) : (
                <PrivacyVisualFallback
                    activeSection={activeSection}
                    visualTier={visualTier === 'full' ? 'reduced' : visualTier}
                />
            )}
        </div>
    );

    return (
        <ResponsiveSplitShell
            className="min-h-[calc(100dvh-4rem)] bg-black"
            containerClassName="max-w-[1680px]"
            content={content}
            visual={visual}
            visualMode="background"
            visualPaneClassName="pointer-events-none rounded-[1.75rem] border border-white/5 bg-[#020205] lg:rounded-none lg:border-0"
        />
    );
}
