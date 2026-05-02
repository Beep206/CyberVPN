'use client';

import { useLocale, useTranslations } from 'next-intl';
import { Activity, Cpu, Wifi } from 'lucide-react';
import { motion } from 'motion/react';
import type { PublicNetworkOverview, PublicNetworkUptimeResponse } from '@/lib/api/public-network';
import {
  formatAvailability,
  formatCount,
  formatTraffic,
} from '@/features/network-intelligence/lib/public-network';

interface MetricsHUDProps {
  overview?: PublicNetworkOverview;
  uptime?: PublicNetworkUptimeResponse;
}

export function MetricsHUD({ overview, uptime }: MetricsHUDProps) {
  const locale = useLocale();
  const t = useTranslations('Status');

  const statusLabel = overview?.global.status === 'online'
    ? t('metrics.status_nominal')
    : overview?.global.status === 'degraded'
      ? t('metrics.status_warning')
      : t('metrics.status_outage');

  const metrics = [
    {
      label: t('metrics.bandwidth'),
      value: formatTraffic(overview?.global.todayBytesOut, locale),
      icon: Wifi,
      color: '#00ffff',
    },
    {
      label: t('metrics.active_nodes'),
      value: `${formatCount(overview?.global.onlineServers, locale)} / ${formatCount(overview?.global.totalServers, locale)}`,
      icon: Cpu,
      color: '#00ff88',
    },
    {
      label: t('metrics.uptime'),
      value: formatAvailability(uptime?.summary.currentAvailabilityPct, locale),
      icon: Activity,
      color: overview?.global.status === 'major_outage' ? '#ff0055' : overview?.global.status === 'degraded' ? '#ffb800' : '#00ff88',
      status: statusLabel,
    },
  ];

  return (
    <div className="grid gap-4">
      {metrics.map((metric, index) => {
        const Icon = metric.icon;
        return (
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            key={metric.label}
            className="p-4 border border-white/10 bg-black/40 backdrop-blur-md rounded-xl relative overflow-hidden group"
          >
            <div
              className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-500"
              style={{ background: `radial-gradient(circle at right center, ${metric.color}, transparent 70%)` }}
            />

            <div className="flex justify-between items-start gap-4 relative z-10">
              <div className="min-w-0">
                <p className="text-[10px] font-mono text-muted-foreground-low uppercase tracking-wider mb-1">
                  {metric.label}
                </p>
                <p className="text-2xl font-display font-bold text-white tracking-widest">
                  {metric.value}
                </p>
                {'status' in metric && metric.status ? (
                  <p className="mt-2 text-[10px] font-mono uppercase tracking-[0.24em] text-white/45">
                    {metric.status}
                  </p>
                ) : null}
              </div>
              <div className="p-2 bg-white/5 rounded-lg border border-white/5">
                <Icon className="w-4 h-4" style={{ color: metric.color }} />
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
