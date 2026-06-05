'use client';

import { useQuery } from '@tanstack/react-query';
import { motion } from 'motion/react';
import { useLocale, useTranslations } from 'next-intl';
import { Activity, AlertTriangle, Server, Users } from 'lucide-react';
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
        retry: false,
    });

    const globalMetrics = overviewQuery.data?.global;
    const isOverviewUnavailable = overviewQuery.isError || (overviewQuery.isSuccess && !globalMetrics);
    const unavailableValue = t('telemetry.unavailableValue');
    const monthlyTraffic = formatTraffic(globalMetrics?.monthlyTrafficBytes, locale);
    const onlineServers = formatCount(globalMetrics?.onlineServers, locale);
    const liveUsers = formatCount(globalMetrics?.activeUsers, locale);
    const metricValueClassName = isOverviewUnavailable
        ? 'font-display text-base font-black uppercase tracking-[0.12em] text-amber-200'
        : 'font-display text-2xl font-black text-foreground dark:text-white';

    return (
        <div className="flex w-full flex-col gap-4 md:w-auto mt-12 md:mt-0">
            {isOverviewUnavailable ? (
                <motion.div
                    role="status"
                    aria-live="polite"
                    initial={{ opacity: 0, y: 14 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.45, delay: 0.1 }}
                    className="max-w-xl rounded-lg border border-warning/35 bg-warning/10 p-4 text-amber-100 shadow-[0_0_30px_rgba(255,184,0,0.08)] backdrop-blur-md dark:bg-warning/10"
                >
                    <div className="flex items-start gap-3">
                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
                        <div>
                            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-warning">
                                {t('telemetry.overviewUnavailableTitle')}
                            </p>
                            <p className="mt-2 text-sm leading-6 text-amber-100/80">
                                {t('telemetry.overviewUnavailableDescription')}
                            </p>
                        </div>
                    </div>
                </motion.div>
            ) : null}

            <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto">
                {/* HUD Blocks */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.2 }}
                    className="group relative flex-1 overflow-hidden rounded-lg border border-neon-cyan/20 bg-card/85 p-5 shadow-[0_0_30px_rgba(0,255,255,0.05)] backdrop-blur-md dark:bg-[#050510]/80 md:w-48"
                >
                    <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-neon-cyan to-transparent opacity-50" />
                    <div className="flex items-center gap-3 mb-2">
                        <Activity className="w-4 h-4 text-neon-cyan animate-pulse" />
                        <span className="font-mono text-[10px] uppercase text-muted-foreground tracking-widest">
                            {t('labels.totalBandwidth')}
                        </span>
                    </div>
                    <div className={metricValueClassName}>
                        {isOverviewUnavailable ? unavailableValue : monthlyTraffic}
                    </div>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.3 }}
                    className="group relative flex-1 overflow-hidden rounded-lg border border-matrix-green/20 bg-card/85 p-5 shadow-[0_0_30px_rgba(0,255,136,0.05)] backdrop-blur-md dark:bg-[#050510]/80 md:w-48"
                >
                    <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-matrix-green to-transparent opacity-50" />
                    <div className="flex items-center gap-3 mb-2">
                        <Server className="w-4 h-4 text-matrix-green" />
                        <span className="font-mono text-[10px] uppercase text-muted-foreground tracking-widest">
                            {t('labels.activeNodes')}
                        </span>
                    </div>
                    <div className={metricValueClassName}>
                        {isOverviewUnavailable ? unavailableValue : onlineServers}
                    </div>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.4 }}
                    className="group relative flex-1 overflow-hidden rounded-lg border border-neon-pink/20 bg-card/85 p-5 shadow-[0_0_30px_rgba(255,0,255,0.05)] backdrop-blur-md dark:bg-[#050510]/80 md:w-56"
                >
                    <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-neon-pink to-transparent opacity-50" />
                    <div className="flex items-center gap-3 mb-2">
                        <Users className="w-4 h-4 text-neon-pink" />
                        <span className="font-mono text-[10px] uppercase text-muted-foreground tracking-widest">
                            {t('labels.threatsIntercepted')}
                        </span>
                    </div>
                    <div className={metricValueClassName}>
                        {isOverviewUnavailable ? unavailableValue : liveUsers}
                    </div>
                </motion.div>
            </div>
        </div>
    );
}
