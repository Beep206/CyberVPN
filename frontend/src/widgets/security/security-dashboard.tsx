'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';
import { useEnhancementReady } from '@/shared/hooks/use-enhancement-ready';
import type { VisualTier } from '@/shared/hooks/use-visual-tier';
import { ArchitectureStack } from './architecture-stack';
import { ThreatRadar } from './threat-radar';
import { ClassifiedContent } from './classified-content';
import { ProtocolGrid } from './protocol-grid';

// Lazy load the heavy 3D shield scene
const SecurityShield3D = dynamic(() => import('@/3d/scenes/SecurityShield3D'), { ssr: false });

export type SecurityLayerId = 'bareMetal' | 'network' | 'crypto' | 'client';

function SecurityVisualFallback({
    activeLayer,
    visualTier,
}: {
    activeLayer: SecurityLayerId;
    visualTier: VisualTier;
}) {
    const accentMap: Record<SecurityLayerId, { borderClassName: string; glowClassName: string; label: string }> = {
        bareMetal: {
            borderClassName: 'border-white/20',
            glowClassName:
                'bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.12),transparent_50%),linear-gradient(180deg,rgba(0,0,0,0)_0%,rgba(0,0,0,0.88)_100%)]',
            label: 'BAREMETAL.TIER',
        },
        network: {
            borderClassName: 'border-neon-cyan/30',
            glowClassName:
                'bg-[radial-gradient(circle_at_center,rgba(0,255,255,0.18),transparent_50%),linear-gradient(180deg,rgba(0,0,0,0)_0%,rgba(0,9,14,0.88)_100%)]',
            label: 'NETWORK.TIER',
        },
        crypto: {
            borderClassName: 'border-matrix-green/30',
            glowClassName:
                'bg-[radial-gradient(circle_at_center,rgba(0,255,136,0.18),transparent_50%),linear-gradient(180deg,rgba(0,0,0,0)_0%,rgba(0,12,8,0.88)_100%)]',
            label: 'CRYPTO.TIER',
        },
        client: {
            borderClassName: 'border-neon-purple/30',
            glowClassName:
                'bg-[radial-gradient(circle_at_center,rgba(255,0,255,0.16),transparent_50%),linear-gradient(180deg,rgba(0,0,0,0)_0%,rgba(10,0,12,0.88)_100%)]',
            label: 'CLIENT.TIER',
        },
    };

    const accent = accentMap[activeLayer];

    return (
        <div aria-hidden="true" data-visual-tier={visualTier} className="absolute inset-0 overflow-hidden">
            <div className={`absolute inset-0 ${accent.glowClassName}`} />
            <div className={`absolute left-1/2 top-1/2 h-64 w-64 -translate-x-1/2 -translate-y-1/2 rounded-full border ${accent.borderClassName}`} />
            <div className={`absolute left-1/2 top-1/2 h-[22rem] w-[22rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed ${accent.borderClassName} opacity-45`} />
            <div className="absolute inset-x-10 top-10 grid grid-cols-3 gap-3 opacity-75">
                <div className="h-16 rounded-2xl border border-white/10 bg-black/35" />
                <div className="h-16 rounded-2xl border border-white/10 bg-white/[0.04]" />
                <div className="h-16 rounded-2xl border border-white/10 bg-black/35" />
            </div>
            {visualTier === 'reduced' ? (
                <div className="absolute bottom-8 right-8 rounded-full border border-white/10 bg-black/35 px-4 py-2 font-mono text-[11px] tracking-[0.28em] text-white/75">
                    {accent.label}
                </div>
            ) : null}
        </div>
    );
}

export function SecurityDashboard() {
    const { isReady: isSceneReady, tier: visualTier } = useEnhancementReady({
        minimumTier: 'full',
        defer: 'idle',
    });
    const [activeLayer, setActiveLayer] = useState<SecurityLayerId>('bareMetal');
    const showScene = visualTier === 'full' && isSceneReady;

    return (
        <div className="relative w-full min-h-[calc(100vh-4rem)] bg-black flex flex-col overflow-x-hidden">
            
            {/* HERO SECTION: The Shield & Threat Radar */}
            <div className="relative w-full h-[80vh] flex flex-col md:flex-row border-b border-grid-line/30">
                
                {/* 3D Background (Aegis Shield) */}
                <div className="absolute inset-0 z-0 pointer-events-none">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.8)_100%)] z-10" />
                    {showScene ? (
                        <SecurityShield3D activeLayer={activeLayer} />
                    ) : (
                        <SecurityVisualFallback
                            activeLayer={activeLayer}
                            visualTier={visualTier === 'full' ? 'reduced' : visualTier}
                        />
                    )}
                </div>

                {/* Left: Architecture Stack selector */}
                <div className="w-full md:w-[400px] lg:w-[450px] relative z-20 flex flex-col h-full border-r border-grid-line/30 bg-black/60 backdrop-blur-md">
                    <ArchitectureStack activeLayer={activeLayer} setActiveLayer={setActiveLayer} />
                </div>

                {/* Right: Live Threat Radar */}
                <div className="hidden md:flex flex-1 relative z-20 h-full p-8 md:p-12 items-center justify-end pointer-events-none">
                    <ThreatRadar />
                </div>
            </div>

            {/* CONTENT SECTION: Classified Text & Protocols */}
            <div className="w-full max-w-7xl mx-auto px-6 py-24 grid grid-cols-1 lg:grid-cols-2 gap-24 relative z-20">
                <ClassifiedContent />
                <ProtocolGrid />
            </div>

        </div>
    );
}
