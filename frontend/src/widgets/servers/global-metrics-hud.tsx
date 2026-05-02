'use client';

import { useQuery } from '@tanstack/react-query';
import { motion } from 'motion/react';
import { useLocale, useTranslations } from 'next-intl';
import { Activity, Server, Users } from 'lucide-react';
import { publicNetworkApi } from '@/lib/api';
import {
    formatCount,
    formatTraffic,
    pollingInterval,
} from '@/features/network-intelligence/lib/public-network';

export function GlobalMetricsHud() {
    const locale = useLocale();
    const t = useTranslations('Network');
    const overviewQuery = useQuery({
        queryKey: ['public-network-overview'],
        queryFn: async () => {
            const { data } = await publicNetworkApi.getOverview();
            return data;
        },
        staleTime: 30_000,
        refetchInterval: pollingInterval(30_000),
        refetchIntervalInBackground: false,
        refetchOnWindowFocus: false,
    });

    const globalMetrics = overviewQuery.data?.global;
    const monthlyTraffic = formatTraffic(globalMetrics?.monthlyTrafficBytes, locale);
    const onlineServers = formatCount(globalMetrics?.onlineServers, locale);
    const liveUsers = formatCount(globalMetrics?.activeUsers, locale);

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
                    {monthlyTraffic}
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
                    <Server className="w-4 h-4 text-matrix-green" />
                    <span className="font-mono text-[10px] uppercase text-muted-foreground tracking-widest">
                        {t('labels.activeNodes')}
                    </span>
                </div>
                <div className="font-display text-2xl font-black text-white">
                    {onlineServers}
                </div>
            </motion.div>

            <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.4 }}
                className="bg-[#050510]/80 backdrop-blur-md border border-neon-pink/20 rounded-lg p-5 flex-1 md:w-56 relative overflow-hidden group shadow-[0_0_30px_rgba(255,0,255,0.05)]"
            >
                <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-neon-pink to-transparent opacity-50" />
                <div className="flex items-center gap-3 mb-2">
                    <Users className="w-4 h-4 text-neon-pink" />
                    <span className="font-mono text-[10px] uppercase text-muted-foreground tracking-widest">
                        {t('labels.threatsIntercepted')}
                    </span>
                </div>
                <div className="font-display text-2xl font-black text-white font-mono">
                    {liveUsers}
                </div>
            </motion.div>
        </div>
    );
}
