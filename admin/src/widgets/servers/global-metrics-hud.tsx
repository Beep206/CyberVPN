'use client';

import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { Activity, ShieldAlert, Cpu } from 'lucide-react';
import { useEffect, useState } from 'react';
import { CypherText } from '@/shared/ui/atoms/cypher-text';

export function GlobalMetricsHud() {
    const t = useTranslations('Network');
    const [threats, setThreats] = useState(14200000); // Base starting number

    // Simulate live incrementing threats
    useEffect(() => {
        const interval = setInterval(() => {
            setThreats(prev => prev + Math.floor(Math.random() * 50));
        }, 100);
        return () => clearInterval(interval);
    }, []);

    // Format number to "14.2M/s" style or full commas
    const formattedThreats = new Intl.NumberFormat('en-US').format(threats);

    return (
        <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto mt-12 md:mt-0">
            {/* HUD Blocks */}
            <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.2 }}
                className="bg-[#050510]/80 backdrop-blur-md border border-neon-cyan/20 rounded-lg p-5 flex-1 md:w-48 relative overflow-hidden group shadow-[0_0_30px_rgba(0,255,255,0.05)]"
            >
                <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-neon-cyan to-transparent opacity-50" />
                <div className="flex items-center gap-3 mb-2">
                    <Activity className="w-4 h-4 text-neon-cyan animate-pulse" />
                    <span className="font-mono text-[10px] uppercase text-muted-foreground tracking-widest">
                        {t('labels.totalBandwidth')}
                    </span>
                </div>
                <div className="font-display text-2xl font-black text-white">
                    {t('metrics.bandwidth')}
                </div>
            </motion.div>

            <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.3 }}
                className="bg-[#050510]/80 backdrop-blur-md border border-matrix-green/20 rounded-lg p-5 flex-1 md:w-48 relative overflow-hidden group shadow-[0_0_30px_rgba(0,255,136,0.05)]"
            >
                 <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-matrix-green to-transparent opacity-50" />
                <div className="flex items-center gap-3 mb-2">
                    <Cpu className="w-4 h-4 text-matrix-green" />
                    <span className="font-mono text-[10px] uppercase text-muted-foreground tracking-widest">
                        {t('labels.activeNodes')}
                    </span>
                </div>
                <div className="font-display text-2xl font-black text-white">
                    <CypherText text={t('metrics.nodes')} />
                </div>
            </motion.div>

            <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.4 }}
                className="bg-[#050510]/80 backdrop-blur-md border border-neon-purple/20 rounded-lg p-5 flex-1 md:w-56 relative overflow-hidden group shadow-[0_0_30px_rgba(255,0,255,0.05)]"
            >
                <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-neon-purple to-transparent opacity-50" />
                <div className="flex items-center gap-3 mb-2">
                    <ShieldAlert className="w-4 h-4 text-neon-purple" />
                    <span className="font-mono text-[10px] uppercase text-muted-foreground tracking-widest">
                        {t('labels.threatsIntercepted')}
                    </span>
                </div>
                <div className="font-display text-2xl font-black text-white font-mono">
                    {formattedThreats}
                </div>
            </motion.div>
        </div>
    );
}
