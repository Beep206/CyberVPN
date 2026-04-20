'use client';

import { motion } from 'motion/react';
import { useTranslations } from 'next-intl';
import { Database, ShieldAlert, WifiOff, FileX2 } from 'lucide-react';

export function DataRadar() {
    const t = useTranslations('Privacy');

    return (
        <div className="w-full flex flex-col items-center gap-8 mt-4 border border-grid-line/30 bg-black/50 p-6 relative overflow-hidden">
            
            {/* Background Scanner Grid */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(0,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(0,255,255,0.05)_1px,transparent_1px)] bg-[size:20px_20px] pointer-events-none" />

            <div className="flex items-center gap-2 text-neon-cyan max-w-full z-10">
                <ShieldAlert className="w-4 h-4" />
                <span className="text-xs tracking-widest uppercase font-bold">ACTIVE SCAN: TELEMETRY PROTOCOLS</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 w-full max-w-2xl z-10 relative">
                
                {/* ALLOWED (What we collect) */}
                <div className="flex flex-col items-center gap-4">
                    <div className="relative w-32 h-32 rounded-full border border-matrix-green/30 flex items-center justify-center bg-matrix-green/5 shadow-[0_0_15px_rgba(0,255,136,0.1)]">
                        {/* Radar Sweep */}
                        <motion.div 
                            className="absolute inset-0 rounded-full border-r-2 border-matrix-green opacity-50 block origin-center"
                            animate={{ rotate: 360 }}
                            transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
                            style={{ background: 'conic-gradient(from 0deg, transparent 70%, rgba(0,255,136,0.2) 100%)' }}
                        />
                        <Database className="w-8 h-8 text-matrix-green" />
                        
                        {/* Ping rings */}
                        <motion.div 
                            className="absolute inset-0 rounded-full border border-matrix-green"
                            animate={{ scale: [1, 1.5], opacity: [0.8, 0] }}
                            transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
                        />
                    </div>
                    
                    <div className="text-center flex flex-col gap-1">
                        <span className="text-matrix-green font-bold tracking-widest text-xs uppercase">
                            [ ALLOWED_DATA ]
                        </span>
                        <span className="text-white text-sm">
                            {t('sections.dataCollection.radarLabels.collected')}
                        </span>
                    </div>
                </div>

                {/* BLOCKED (What we don't collect) */}
                <div className="flex flex-col items-center gap-4">
                    <div className="relative w-32 h-32 rounded-full border border-red-500/30 flex items-center justify-center bg-red-500/5 shadow-[0_0_15px_rgba(255,0,0,0.1)]">
                        {/* Crosshairs */}
                        <div className="absolute inset-0 flex items-center justify-center">
                            <div className="w-full h-px bg-red-500/30" />
                            <div className="absolute h-full w-px bg-red-500/30" />
                        </div>
                        
                        {/* Static NO entry icons rotating slowly */}
                        <motion.div 
                            className="absolute inset-0 flex items-center justify-center text-red-500/40"
                            animate={{ rotate: -360 }}
                            transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
                        >
                            <FileX2 className="w-16 h-16" />
                        </motion.div>
                        
                        <div className="bg-black p-2 rounded-full z-10 border border-red-500">
                            <WifiOff className="w-6 h-6 text-red-500 animate-pulse" />
                        </div>
                    </div>

                    <div className="text-center flex flex-col gap-1">
                        <span className="text-red-500 font-bold tracking-widest text-xs uppercase">
                            [ BLOCKED_DATA ]
                        </span>
                        <span className="text-white text-sm">
                            {t('sections.dataCollection.radarLabels.blocked')}
                        </span>
                    </div>
                </div>

            </div>

        </div>
    );
}
