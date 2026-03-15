'use client';

import { useTranslations } from 'next-intl';
import { NetworkCore3D } from '@/3d/scenes/StatusNetworkCore3D';
import { MetricsHUD } from './metrics-hud';
import { UptimeMatrix } from './uptime-matrix';
import { IncidentLog } from './incident-log';

export function StatusDashboard() {
    const t = useTranslations('Status');

    return (
        <div className="relative w-full h-full flex-1 flex flex-col md:flex-row bg-black overflow-hidden">
            {/* 3D Background Layer */}
            <div className="absolute inset-0 z-0">
                <NetworkCore3D />
                
                {/* Vignette & Gradient Overlays for better text readability */}
                <div className="absolute inset-0 bg-gradient-to-b from-black/80 via-transparent to-black/80 pointer-events-none" />
                <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-transparent to-black/80 pointer-events-none md:hidden" />
                <div className="absolute inset-y-0 left-0 w-1/3 bg-gradient-to-r from-black via-black/50 to-transparent pointer-events-none hidden md:block" />
                <div className="absolute inset-y-0 right-0 w-1/3 bg-gradient-to-l from-black via-black/50 to-transparent pointer-events-none hidden md:block" />
            </div>

            {/* UI Foreground Layer */}
            <div className="relative z-10 w-full h-full p-4 md:p-8 flex flex-col pointer-events-none">
                {/* Header Section */}
                <header className="mb-8 pointer-events-auto">
                    <h1 className="text-3xl md:text-5xl font-display font-black text-white tracking-widest uppercase">
                        {t('title')}
                    </h1>
                    <p className="text-neon-cyan font-mono text-sm tracking-widest uppercase mt-2">
                        {t('subtitle')}
                    </p>
                </header>

                {/* Main Content Grid */}
                <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-6 pointer-events-auto">
                    {/* Left Panel: Metrics & Logs */}
                    <div className="md:col-span-4 flex flex-col gap-6 max-h-[calc(100vh-200px)] overflow-y-auto custom-scrollbar pr-2">
                        <MetricsHUD />
                        <IncidentLog />
                    </div>

                    {/* Right Panel: Uptime Matrix & Global Controls */}
                    <div className="md:col-span-8 flex flex-col gap-6 justify-end pb-8">
                        <UptimeMatrix />
                    </div>
                </div>
            </div>
        </div>
    );
}
