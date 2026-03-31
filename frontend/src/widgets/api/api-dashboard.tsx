'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { useTranslations } from 'next-intl';
import { useEnhancementReady } from '@/shared/hooks/use-enhancement-ready';
import type { VisualTier } from '@/shared/hooks/use-visual-tier';
import { ResponsiveSplitShell } from '@/shared/ui/layout/responsive-split-shell';
import { EndpointsSidebar } from './endpoints-sidebar';
import { EndpointDetails } from './endpoint-details';
import { CodeTerminal } from './code-terminal';

const ApiNexus3D = dynamic(() => import('@/3d/scenes/ApiNexus3D'), { ssr: false });

export type EndpointCategory = 'auth' | 'servers';
export type EndpointId = 'generateToken' | 'listServers' | 'connect';

export interface ActiveEndpoint {
    category: EndpointCategory;
    id: EndpointId;
}

function ApiVisualFallback({
    activeEndpoint,
    visualTier,
}: {
    activeEndpoint: ActiveEndpoint;
    visualTier: VisualTier;
}) {
    const accentStyles = activeEndpoint.category === 'auth'
        ? {
            glowClassName:
                'bg-[radial-gradient(circle_at_center,rgba(0,255,255,0.18),transparent_48%),linear-gradient(180deg,rgba(0,0,0,0.05)_0%,rgba(0,9,14,0.92)_100%)]',
            borderClassName: 'border-neon-cyan/30',
            textClassName: 'text-neon-cyan/75',
            statusLabel: 'TOKEN.GATE',
        }
        : {
            glowClassName:
                'bg-[radial-gradient(circle_at_center,rgba(0,255,136,0.18),transparent_48%),linear-gradient(180deg,rgba(0,0,0,0.05)_0%,rgba(0,12,8,0.92)_100%)]',
            borderClassName: 'border-matrix-green/30',
            textClassName: 'text-matrix-green/75',
            statusLabel: 'EDGE.ROUTER',
        };

    const endpointLabel = `${activeEndpoint.category.toUpperCase()}.${activeEndpoint.id.toUpperCase()}`;

    return (
        <div aria-hidden="true" data-visual-tier={visualTier} className="absolute inset-0 overflow-hidden">
            <div className={`absolute inset-0 ${accentStyles.glowClassName}`} />
            <div className="absolute inset-10 rounded-[2rem] border border-white/10 bg-[linear-gradient(160deg,rgba(255,255,255,0.03),rgba(0,0,0,0.88))]" />
            <div className={`absolute left-1/2 top-1/2 h-56 w-56 -translate-x-1/2 -translate-y-1/2 rounded-full border ${accentStyles.borderClassName}`} />
            <div className={`absolute left-1/2 top-1/2 h-[19rem] w-[19rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed ${accentStyles.borderClassName} opacity-45`} />
            <div className="absolute inset-x-12 top-12 grid grid-cols-3 gap-3 opacity-75">
                <div className="h-14 rounded-2xl border border-white/10 bg-black/35" />
                <div className="h-20 rounded-2xl border border-white/10 bg-white/[0.04]" />
                <div className="h-14 rounded-2xl border border-white/10 bg-black/35" />
            </div>
            {visualTier === 'reduced' ? (
                <div className="absolute inset-x-10 bottom-10 flex flex-wrap items-center gap-3 font-mono text-[11px] tracking-[0.28em]">
                    <span className={`rounded-full border px-4 py-2 ${accentStyles.borderClassName} ${accentStyles.textClassName}`}>
                        {accentStyles.statusLabel}
                    </span>
                    <span className="rounded-full border border-white/10 px-4 py-2 text-white/60">
                        {endpointLabel}
                    </span>
                </div>
            ) : null}
        </div>
    );
}

export function ApiDashboard() {
    const t = useTranslations('Api');
    const { isReady: isSceneReady, tier: visualTier } = useEnhancementReady({
        minimumTier: 'full',
        defer: 'idle',
    });
    const [activeEndpoint, setActiveEndpoint] = useState<ActiveEndpoint>({
        category: 'auth',
        id: 'generateToken'
    });
    const showScene = visualTier === 'full' && isSceneReady;

    const content = (
        <div
            data-testid="api-dashboard-main"
            className="grid grid-cols-1 gap-8 xl:grid-cols-[minmax(0,360px)_minmax(0,1fr)_minmax(320px,560px)] xl:gap-10"
        >
            <div
                data-testid="api-dashboard-details"
                className="order-1 xl:order-2 min-w-0 rounded-[1.75rem] border border-grid-line/30 bg-black/45 p-6 md:p-8 lg:p-10 backdrop-blur-xl"
            >
                <EndpointDetails activeEndpoint={activeEndpoint} />
            </div>

            <div
                data-testid="api-dashboard-sidebar"
                className="order-2 xl:order-1 min-w-0 rounded-[1.75rem] border border-grid-line/30 bg-black/60 backdrop-blur-xl xl:sticky xl:top-24 xl:self-start"
            >
                <div className="p-6 md:p-8">
                    <h1 className="font-display text-3xl font-bold text-white uppercase tracking-tighter drop-shadow-[0_0_10px_rgba(255,255,255,0.3)]">
                        {t('title')}
                    </h1>
                    <p className="font-mono text-muted-foreground mt-4 text-xs leading-relaxed">
                        {t('description')}
                    </p>
                </div>

                <div className="px-6 pb-6 md:px-8 md:pb-8">
                    <EndpointsSidebar activeEndpoint={activeEndpoint} setActiveEndpoint={setActiveEndpoint} />
                </div>
            </div>

            <div
                data-testid="api-dashboard-terminal"
                className="order-3 min-w-0 xl:sticky xl:top-24 xl:self-start"
            >
                <CodeTerminal activeEndpoint={activeEndpoint} />
            </div>
        </div>
    );

    const visual = (
        <div className="absolute inset-0 bg-[#020205] overflow-hidden">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.9)_100%)] z-10 pointer-events-none" />
            {showScene ? (
                <ApiNexus3D activeEndpoint={activeEndpoint} />
            ) : (
                <ApiVisualFallback
                    activeEndpoint={activeEndpoint}
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
