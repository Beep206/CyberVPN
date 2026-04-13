'use client';

import React, { memo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import {
  useServerStats,
  useSystemStats,
  useBandwidthAnalytics,
  useMonitoringRecap,
} from '../hooks/useDashboardData';
import { usageApi } from '@/lib/api/usage';

// --- Pure formatting functions outside component ---
const formatTraffic = (bytes: number | undefined | null) => {
  if (!bytes) return '0 GB';

  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  let value = bytes;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  const precision = value >= 100 || unitIndex === 0 ? 0 : 1;
  return `${value.toFixed(precision)} ${units[unitIndex]}`;
};

const formatDataUsage = (bytes: number | undefined) => {
  if (!bytes) return '0 GB';
  const gb = bytes / (1024 ** 3);
  if (gb >= 1000) {
    const tb = gb / 1024;
    return `${tb.toFixed(2)} TB`;
  }
  return `${gb.toFixed(2)} GB`;
};

const getBandwidthPercentage = (used: number | undefined, limit: number | undefined) => {
  if (!used || !limit) return 0;
  return Math.min((used / limit) * 100, 100);
};

// --- Atomic Components ---
const ServerStatusCard = memo(() => {
  const t = useTranslations('Dashboard');
  const { data: serverStats, isLoading } = useServerStats();

  return (
    <div className="cyber-card p-6 rounded-xl">
      <h2 className="text-xl font-mono text-neon-pink mb-2">{t('serverStatus')}</h2>
      {isLoading ? (
        <div className="text-2xl font-display text-muted-foreground animate-pulse">Loading...</div>
      ) : (
        <div className="text-4xl font-display text-server-online drop-shadow-glow">
          {serverStats?.online ?? 0} / {serverStats?.total ?? 0}
        </div>
      )}
      <p className="text-sm text-muted-foreground mt-2">{t('nodesOnline')}</p>
    </div>
  );
});
ServerStatusCard.displayName = 'ServerStatusCard';

const ActiveSessionsCard = memo(() => {
  const t = useTranslations('Dashboard');
  const { data: systemStats, isLoading } = useSystemStats();

  return (
    <div className="cyber-card p-6 rounded-xl">
      <h2 className="text-xl font-mono text-neon-pink mb-2">{t('activeSessions')}</h2>
      {isLoading ? (
        <div className="text-2xl font-display text-muted-foreground animate-pulse">Loading...</div>
      ) : (
        <div className="text-4xl font-display text-neon-cyan drop-shadow-glow">
          {systemStats?.active_users?.toLocaleString() ?? '--'}
        </div>
      )}
      <p className="text-sm text-muted-foreground mt-2">{t('currentConnections')}</p>
    </div>
  );
});
ActiveSessionsCard.displayName = 'ActiveSessionsCard';

const NetworkLoadCard = memo(() => {
  const t = useTranslations('Dashboard');
  const { data: bandwidth, isLoading } = useBandwidthAnalytics();

  return (
    <div className="cyber-card p-6 rounded-xl">
      <h2 className="text-xl font-mono text-neon-pink mb-2">{t('networkLoad')}</h2>
      {isLoading ? (
        <div className="text-2xl font-display text-muted-foreground animate-pulse">Loading...</div>
      ) : (
        <div className="text-4xl font-display text-matrix-green drop-shadow-glow">
          {formatTraffic(bandwidth?.bytes_out)}
        </div>
      )}
      <p className="text-sm text-muted-foreground mt-2">{t('trafficToday')}</p>
    </div>
  );
});
NetworkLoadCard.displayName = 'NetworkLoadCard';

const OpsRecapCard = memo(() => {
  const t = useTranslations('Dashboard');
  const { data: recap, isLoading } = useMonitoringRecap();

  return (
    <div className="cyber-card rounded-xl border border-neon-cyan/20 p-6">
      <div className="mb-5 flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="mb-2 text-xl font-mono text-neon-pink">{t('networkRecap')}</h2>
          <p className="text-sm text-muted-foreground">{t('opsBaseline')}</p>
        </div>
        <div className="font-mono text-xs text-muted-foreground">
          {recap?.this_month
            ? `${t('thisMonth')}: ${recap.this_month.users.toLocaleString()} / ${formatTraffic(recap.this_month.traffic_bytes)}`
            : t('monthlyRecapUnavailable')}
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
          {[...Array(4)].map((_, index) => (
            <div key={index} className="rounded-lg border border-grid-line/30 bg-terminal-surface/40 p-4 animate-pulse">
              <div className="mb-3 h-3 w-20 rounded bg-grid-line/30" />
              <div className="h-7 w-24 rounded bg-grid-line/20" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
          <div className="rounded-lg border border-grid-line/30 bg-terminal-surface/40 p-4">
            <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">{t('totalUsers')}</p>
            <p className="text-3xl font-display text-neon-cyan drop-shadow-glow">
              {recap?.total.users?.toLocaleString() ?? '--'}
            </p>
          </div>

          <div className="rounded-lg border border-grid-line/30 bg-terminal-surface/40 p-4">
            <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">{t('totalNodes')}</p>
            <p className="text-3xl font-display text-matrix-green drop-shadow-glow">
              {recap?.total.nodes?.toLocaleString() ?? '--'}
            </p>
          </div>

          <div className="rounded-lg border border-grid-line/30 bg-terminal-surface/40 p-4">
            <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">{t('lifetimeTraffic')}</p>
            <p className="text-3xl font-display text-neon-purple drop-shadow-glow">
              {formatTraffic(recap?.total.traffic_bytes)}
            </p>
          </div>

          <div className="rounded-lg border border-grid-line/30 bg-terminal-surface/40 p-4">
            <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">{t('countries')}</p>
            <p className="text-3xl font-display text-neon-pink drop-shadow-glow">
              {(recap?.total.distinct_countries ?? 0).toLocaleString()}
            </p>
          </div>
        </div>
      )}
    </div>
  );
});
OpsRecapCard.displayName = 'OpsRecapCard';

const VpnUsageCard = memo(() => {
  const t = useTranslations('Dashboard');
  const { data: usage, isLoading } = useQuery({
    queryKey: ['user-usage'],
    queryFn: async () => {
      const response = await usageApi.getMyUsage();
      return response.data;
    },
    staleTime: 30 * 1000,
  });

  const percentage = getBandwidthPercentage(usage?.bandwidth_used_bytes, usage?.bandwidth_limit_bytes);

  return (
    <div className="cyber-card p-6 rounded-xl">
      <h2 className="text-xl font-mono text-neon-pink mb-2">{t('vpnUsage') || 'VPN Usage'}</h2>
      {isLoading ? (
        <div className="text-2xl font-display text-muted-foreground animate-pulse">Loading...</div>
      ) : (
        <div className="space-y-4">
          <div>
            <div className="flex justify-between items-baseline mb-2">
              <span className="text-2xl font-display text-neon-cyan drop-shadow-glow">
                {formatDataUsage(usage?.bandwidth_used_bytes)}
              </span>
              <span className="text-sm text-muted-foreground font-mono">
                / {formatDataUsage(usage?.bandwidth_limit_bytes)}
              </span>
            </div>
            <div className="h-2 bg-grid-line/30 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-neon-cyan to-matrix-green transition-all duration-500"
                style={{ width: `${percentage}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-1 font-mono">
              {percentage.toFixed(1)}% used
            </p>
          </div>
          <div className="pt-2 border-t border-grid-line/30">
            <div className="text-3xl font-display text-neon-purple drop-shadow-glow">
              {usage?.connections_active?.toLocaleString() ?? '0'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">{t('activeConnections') || 'Active Connections'}</p>
          </div>
        </div>
      )}
    </div>
  );
});
VpnUsageCard.displayName = 'VpnUsageCard';

/**
 * Dashboard statistics cards component
 * Displays real-time server status, active sessions, and network load
 */
export const DashboardStats = memo(() => {
  const t = useTranslations('Dashboard');

  return (
    <section aria-label={t('serverStatus')} className="space-y-6">
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <ServerStatusCard />
        <ActiveSessionsCard />
        <NetworkLoadCard />
        <VpnUsageCard />
      </div>
      <OpsRecapCard />
    </section>
  );
});
DashboardStats.displayName = 'DashboardStats';
