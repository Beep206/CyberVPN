'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { FeaturesScene3D } from '@/3d/scenes/FeaturesScene3D';
import { FeatureModules } from './feature-modules';
import { TechSpecsTerminal } from './tech-specs-terminal';
import { SecondaryGrid } from './secondary-grid';

export type FeatureId = 'quantum' | 'multihop' | 'obfuscation' | 'killswitch';

export function FeaturesDashboard() {
    const t = useTranslations('Features');
    const [activeFeature, setActiveFeature] = useState<FeatureId>('quantum');

    return (
        <div className="relative w-full min-h-[calc(100vh-4rem)] flex flex-col md:flex-row bg-black overflow-hidden">
            
            {/* LEFT COLUMN: Feature List & Terminal (UI Overlays) */}
            <div className="w-full md:w-1/2 lg:w-[45%] h-full z-10 p-6 md:p-12 flex flex-col justify-start md:h-[calc(100vh-4rem)] md:overflow-y-auto no-scrollbar scroll-smooth">
                
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                >
                    <h1 className="font-display text-4xl md:text-5xl lg:text-6xl font-black text-white uppercase tracking-tighter mb-4">
                        {t('title')}
                    </h1>
                    <p className="font-mono text-muted-foreground mb-12 max-w-md">
                        {t('description')}
                    </p>
                </motion.div>

                <div className="flex-1 flex flex-col gap-8">
                    <FeatureModules activeFeature={activeFeature} setActiveFeature={setActiveFeature} />
                    <TechSpecsTerminal activeFeature={activeFeature} />
                </div>
                
                <div className="mt-24 pb-24">
                    <SecondaryGrid />
                </div>
            </div>

            {/* RIGHT COLUMN: 3D Engine Core (Sticky Visualizer) */}
            <div className="w-full md:w-1/2 lg:w-[55%] h-[50vh] md:h-[calc(100vh-4rem)] sticky top-16 right-0 z-0 border-l border-grid-line/30 bg-terminal-bg/50">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.8)_100%)] z-10 pointer-events-none" />
                
                 <div className="absolute inset-0 w-full h-full opacity-80 mix-blend-screen overflow-hidden">
                    <FeaturesScene3D activeFeature={activeFeature} />
                 </div>
                
                {/* HUD Overlay inside 3D view */}
                <div className="absolute top-6 right-6 z-20 font-mono text-xs text-matrix-green/70 flex flex-col items-end pointer-events-none">
                    <span>SYS.CORE.ENGAGED</span>
                    <span>OP.MODE: {activeFeature.toUpperCase()}</span>
                    <span className="animate-pulse">RENDERING...</span>
                </div>
            </div>

        </div>
    );
}
