'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import GlobalNetworkScene from '@/3d/scenes/GlobalNetwork';
import { ServerLocationsList } from './server-locations-list';
import { GlobalMetricsHud } from './global-metrics-hud';

export function NetworkDashboard() {
    const t = useTranslations('Network');
    const [activeNodeId, setActiveNodeId] = useState<string | null>(null);

    return (
        <div className="relative w-full min-h-[calc(100vh-4rem)] bg-black overflow-hidden flex flex-col md:flex-row">
            
            {/* BACKGROUND EXPANSE: Fullscreen 3D Scene */}
            <div className="absolute inset-0 z-0">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.85)_100%)] z-10 pointer-events-none" />
                <div className="absolute inset-0 opacity-80 mix-blend-screen overflow-hidden">
                    <GlobalNetworkScene activeNodeId={activeNodeId} />
                </div>
            </div>

            {/* FOREGROUND UI OVERLAYS */}
            <div className="relative z-20 w-full h-full flex flex-col md:flex-row p-6 md:p-8 lg:p-12 gap-8 pointer-events-none">
                
                {/* LEFT: Sidebar / Locations List */}
                <div className="w-full md:w-[320px] lg:w-[400px] flex-shrink-0 flex flex-col pointer-events-auto">
                    <div className="mb-8">
                        <h1 className="font-display text-4xl font-black text-white uppercase tracking-tighter mix-blend-difference drop-shadow-[0_0_10px_rgba(255,255,255,0.3)]">
                            {t('title')}
                        </h1>
                        <p className="font-mono text-muted-foreground mt-4 text-sm max-w-sm">
                            {t('description')}
                        </p>
                    </div>

                    <div className="flex-1 overflow-y-auto no-scrollbar pb-24">
                        <ServerLocationsList activeNodeId={activeNodeId} setActiveNodeId={setActiveNodeId} />
                    </div>
                </div>

                {/* RIGHT/BOTTOM: HUD Elements */}
                <div className="flex-1 flex flex-col justify-end items-end pointer-events-none">
                    <GlobalMetricsHud />
                </div>

            </div>
        </div>
    );
}
