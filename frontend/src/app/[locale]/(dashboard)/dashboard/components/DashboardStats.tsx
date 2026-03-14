'use client';

import React, { memo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { useServerStats, useSystemStats, useBandwidthAnalytics } from '../hooks/useDashboardData';
import { usageApi } from '@/lib/api/usage';

// --- Pure formatting functions outside component ---
const formatBandwidth = (bytes: number | undefined) => {
  if (!bytes) return '--';
  const pb = bytes / (1024 ** 5);
  if (pb >= 1) return `${pb.toFixed(1)} Pb/s`;
  const tb = bytes / (1024 ** 4);
  if (tb >= 1) return `${tb.toFixed(1)} Tb/s`;
  const gb = bytes / (1024 ** 3);
  return `${gb.toFixed(1)} Gb/s`;
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
          {formatBandwidth(bandwidth?.bytes_out)}
        </div>
      )}
      <p className="text-sm text-muted-foreground mt-2">{t('aggregateThroughput')}</p>
    </div>
  );
});
NetworkLoadCard.displayName = 'NetworkLoadCard';

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
    <section aria-label={t('serverStatus')} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <ServerStatusCard />
      <ActiveSessionsCard />
      <NetworkLoadCard />
      <VpnUsageCard />
    </section>
  );
});
DashboardStats.displayName = 'DashboardStats';
