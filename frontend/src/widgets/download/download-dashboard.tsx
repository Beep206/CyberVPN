'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { DownloadPayload3D } from '@/3d/scenes/DownloadPayload3D';
import { OSSelector } from './os-selector';
import { TerminalVerifier } from './terminal-verifier';
import { ChangelogAccordion } from './changelog-accordion';

export type OSPlatform = 'none' | 'windows' | 'macos' | 'linux' | 'ios' | 'android';

export function DownloadDashboard() {
    const t = useTranslations('Download');
    const [selectedOS, setSelectedOS] = useState<OSPlatform>('none');

    return (
        <div className="relative w-full h-full flex-1 flex flex-col md:flex-row bg-black overflow-hidden">
            {/* 3D Background Layer */}
            <div className="absolute inset-0 z-0">
                <DownloadPayload3D selectedOS={selectedOS} />
                
                {/* Advanced Vignette Overlays for reading text */}
                <div className="absolute inset-0 bg-gradient-to-b from-black/90 via-transparent to-black/90 pointer-events-none" />
                <div className="absolute inset-y-0 left-0 w-1/2 bg-gradient-to-r from-black via-black/80 to-transparent pointer-events-none md:block" />
            </div>

            {/* UI Foreground Layer */}
            <div className="relative z-10 w-full h-full p-4 md:p-12 flex flex-col pointer-events-none max-w-7xl mx-auto">
                {/* Header Section */}
                <header className="mb-12 pointer-events-auto mt-4">
                    <p className="text-neon-cyan font-mono text-xs tracking-widest uppercase mb-2">
                        {t('subtitle')}
                    </p>
                    <h1 className="text-4xl md:text-6xl font-display font-black text-white tracking-widest uppercase shadow-black drop-shadow-lg">
                        {t('title')}
                    </h1>
                </header>

                {/* Main Content Split */}
                <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-8 pointer-events-auto h-full pb-20">
                    {/* Left Column: UI Controls */}
                    <div className="md:col-span-5 flex flex-col gap-6 max-h-[70vh] overflow-y-auto custom-scrollbar pr-4">
                        <OSSelector selectedOS={selectedOS} onSelect={setSelectedOS} />
                        <TerminalVerifier selectedOS={selectedOS} />
                    </div>

                    {/* Right Column: Changelog */}
                    <div className="md:col-span-7 flex flex-col justify-end">
                        <ChangelogAccordion selectedOS={selectedOS} />
                    </div>
                </div>
            </div>
        </div>
    );
}
