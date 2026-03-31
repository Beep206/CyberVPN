'use client';

import dynamic from 'next/dynamic';
import { useEffect, useRef, useState } from 'react';
import { useEnhancementReady } from '@/shared/hooks/use-enhancement-ready';
import type { VisualTier } from '@/shared/hooks/use-visual-tier';
import { ResponsiveSplitShell } from '@/shared/ui/layout/responsive-split-shell';
import { ComplianceScanner } from './compliance-scanner';
import { TermsContent } from './terms-content';
import { SignatureTerminal } from './signature-terminal';

// Lazy load the 3D scene because WebGL struggles on SSR
const TermsMonolith3D = dynamic(() => import('@/3d/scenes/TermsMonolith3D'), { ssr: false });

export type TermsSectionId = 'acceptance' | 'prohibited' | 'service' | 'liability' | 'termination';

function TermsVisualFallback({
    isAccepted,
    activeSection,
    visualTier,
}: {
    isAccepted: boolean;
    activeSection: TermsSectionId;
    visualTier: VisualTier;
}) {
    const accentClassName = isAccepted ? 'border-matrix-green/30' : 'border-warning/30';
    const glowClassName = isAccepted
        ? 'bg-[radial-gradient(circle_at_top,rgba(0,255,136,0.16),transparent_48%),linear-gradient(180deg,rgba(0,10,6,0.08)_0%,rgba(0,5,2,0.92)_100%)]'
        : 'bg-[radial-gradient(circle_at_top,rgba(255,120,0,0.16),transparent_48%),linear-gradient(180deg,rgba(12,4,0,0.08)_0%,rgba(5,2,2,0.92)_100%)]';
    const statusLabel = isAccepted ? 'DIRECTIVES.ACCEPTED' : 'DIRECTIVES.PENDING';

    return (
        <div aria-hidden="true" data-visual-tier={visualTier} className="absolute inset-0 overflow-hidden">
            <div className={`absolute inset-0 ${glowClassName}`} />
            <div className={`absolute left-1/2 top-1/2 h-72 w-44 -translate-x-1/2 -translate-y-1/2 rounded-[1.75rem] border ${accentClassName} bg-[linear-gradient(180deg,rgba(255,255,255,0.04),rgba(0,0,0,0.92))] shadow-[0_0_60px_rgba(0,0,0,0.4)]`} />
            <div className={`absolute left-1/2 top-1/2 h-[21rem] w-56 -translate-x-1/2 -translate-y-1/2 rounded-[2rem] border border-dashed ${accentClassName} opacity-40`} />
            <div className="absolute inset-x-12 top-12 grid gap-3 opacity-75">
                <div className="h-3 rounded-full bg-white/10" />
                <div className="h-3 rounded-full bg-white/10 w-2/3" />
                <div className="grid grid-cols-4 gap-2 pt-2">
                    <div className="h-10 rounded-xl border border-white/10 bg-black/35" />
                    <div className="h-10 rounded-xl border border-white/10 bg-black/35" />
                    <div className="h-10 rounded-xl border border-white/10 bg-white/[0.04]" />
                    <div className="h-10 rounded-xl border border-white/10 bg-black/35" />
                </div>
            </div>
            {visualTier === 'reduced' ? (
                <div className="absolute inset-x-10 bottom-10 flex flex-wrap items-center gap-3 font-mono text-[11px] tracking-[0.28em]">
                    <span className={`rounded-full border px-4 py-2 ${accentClassName} text-white/80`}>
                        {statusLabel}
                    </span>
                    <span className="rounded-full border border-white/10 px-4 py-2 text-white/60">
                        SECTION.{activeSection.toUpperCase()}
                    </span>
                </div>
            ) : null}
        </div>
    );
}

export function TermsDashboard() {
    const { isReady: isSceneReady, tier: visualTier } = useEnhancementReady({
        minimumTier: 'full',
        defer: 'idle',
    });
    const [activeSection, setActiveSection] = useState<TermsSectionId>('acceptance');
    const [scrollDepth, setScrollDepth] = useState(0);
    const [isAccepted, setIsAccepted] = useState(false);
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
            data-testid="terms-dashboard-content"
            className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)] lg:gap-10"
        >
            <div
                data-testid="terms-dashboard-main"
                className="order-1 lg:order-2 min-w-0 rounded-[1.75rem] border border-grid-line/30 bg-black/60 backdrop-blur-xl"
            >
                <TermsContent setActiveSection={setActiveSection} isAccepted={isAccepted} />
                <SignatureTerminal isAccepted={isAccepted} onAccept={() => setIsAccepted(true)} />
            </div>

            <div
                data-testid="terms-dashboard-sidebar"
                className="order-2 lg:order-1 min-w-0 rounded-[1.75rem] border border-grid-line/30 bg-black/70 backdrop-blur-xl lg:sticky lg:top-24 lg:self-start"
            >
                <ComplianceScanner 
                    activeSection={activeSection} 
                    setActiveSection={setActiveSection} 
                    isAccepted={isAccepted}
                />
            </div>
        </div>
    );

    const visual = (
        <div className={`absolute inset-0 transition-colors duration-1000 ${isAccepted ? 'bg-[#000502]' : 'bg-[#050202]'}`}>
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,transparent_0%,rgba(0,0,0,0.95)_100%)] z-10 pointer-events-none" />
            {showScene ? (
                <TermsMonolith3D scrollDepth={scrollDepth} isAccepted={isAccepted} />
            ) : (
                <TermsVisualFallback
                    isAccepted={isAccepted}
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
            visualPaneClassName="pointer-events-none rounded-[1.75rem] border border-white/5 lg:rounded-none lg:border-0"
        />
    );
}
