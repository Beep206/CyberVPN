'use client';

import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { useServerStats, useSystemStats, useBandwidthAnalytics } from '../hooks/useDashboardData';
import { usageApi } from '@/lib/api/usage';

/**
 * Dashboard statistics cards component
 * Displays real-time server status, active sessions, and network load
 */
export function DashboardStats() {
  const t = useTranslations('Dashboard');
  const { data: serverStats, isLoading: serverStatsLoading } = useServerStats();
  const { data: systemStats, isLoading: systemStatsLoading } = useSystemStats();
  const { data: bandwidth, isLoading: bandwidthLoading } = useBandwidthAnalytics();

  // Fetch user VPN usage
  const { data: usage, isLoading: usageLoading } = useQuery({
    queryKey: ['user-usage'],
    queryFn: async () => {
      const response = await usageApi.getMyUsage();
      return response.data;
    },
    staleTime: 30 * 1000, // Fresh for 30 seconds
  });

  // Format bandwidth for display (convert bytes to Pb/s or appropriate unit)
  const formatBandwidth = (bytes: number | undefined) => {
    if (!bytes) return '--';
    const pb = bytes / (1024 ** 5); // Convert to petabytes
    if (pb >= 1) return `${pb.toFixed(1)} Pb/s`;
    const tb = bytes / (1024 ** 4); // Convert to terabytes
    if (tb >= 1) return `${tb.toFixed(1)} Tb/s`;
    const gb = bytes / (1024 ** 3); // Convert to gigabytes
    return `${gb.toFixed(1)} Gb/s`;
  };

  // Format bytes for data usage display
  const formatDataUsage = (bytes: number | undefined) => {
    if (!bytes) return '0 GB';
    const gb = bytes / (1024 ** 3);
    if (gb >= 1000) {
      const tb = gb / 1024;
      return `${tb.toFixed(2)} TB`;
    }
    return `${gb.toFixed(2)} GB`;
  };

  // Calculate bandwidth usage percentage
  const getBandwidthPercentage = () => {
    if (!usage?.bandwidth_used_bytes || !usage?.bandwidth_limit_bytes) return 0;
    return Math.min((usage.bandwidth_used_bytes / usage.bandwidth_limit_bytes) * 100, 100);
  };

  return (
    <section aria-label={t('serverStatus')} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {/* Server Status Card */}
      <div className="cyber-card p-6 rounded-xl">
        <h2 className="text-xl font-mono text-neon-pink mb-2">{t('serverStatus')}</h2>
        {serverStatsLoading ? (
          <div className="text-2xl font-display text-muted-foreground animate-pulse">Loading...</div>
        ) : (
          <div className="text-4xl font-display text-server-online drop-shadow-glow">
            {serverStats?.online ?? 0} / {serverStats?.total ?? 0}
          </div>
        )}
        <p className="text-sm text-muted-foreground mt-2">{t('nodesOnline')}</p>
      </div>

      {/* Active Sessions Card */}
      <div className="cyber-card p-6 rounded-xl">
        <h2 className="text-xl font-mono text-neon-pink mb-2">{t('activeSessions')}</h2>
        {systemStatsLoading ? (
          <div className="text-2xl font-display text-muted-foreground animate-pulse">Loading...</div>
        ) : (
          <div className="text-4xl font-display text-neon-cyan drop-shadow-glow">
            {systemStats?.active_users?.toLocaleString() ?? '--'}
          </div>
        )}
        <p className="text-sm text-muted-foreground mt-2">{t('currentConnections')}</p>
      </div>

      {/* Network Load Card */}
      <div className="cyber-card p-6 rounded-xl">
        <h2 className="text-xl font-mono text-neon-pink mb-2">{t('networkLoad')}</h2>
        {bandwidthLoading ? (
          <div className="text-2xl font-display text-muted-foreground animate-pulse">Loading...</div>
        ) : (
          <div className="text-4xl font-display text-matrix-green drop-shadow-glow">
            {formatBandwidth(bandwidth?.bytes_out)}
          </div>
        )}
        <p className="text-sm text-muted-foreground mt-2">{t('aggregateThroughput')}</p>
      </div>

      {/* VPN Usage Card */}
      <div className="cyber-card p-6 rounded-xl">
        <h2 className="text-xl font-mono text-neon-pink mb-2">{t('vpnUsage') || 'VPN Usage'}</h2>
        {usageLoading ? (
          <div className="text-2xl font-display text-muted-foreground animate-pulse">Loading...</div>
        ) : (
          <div className="space-y-4">
            {/* Bandwidth Gauge */}
            <div>
              <div className="flex justify-between items-baseline mb-2">
                <span className="text-2xl font-display text-neon-cyan drop-shadow-glow">
                  {formatDataUsage(usage?.bandwidth_used_bytes)}
                </span>
                <span className="text-sm text-muted-foreground font-mono">
                  / {formatDataUsage(usage?.bandwidth_limit_bytes)}
                </span>
              </div>
              {/* Progress Bar */}
              <div className="h-2 bg-grid-line/30 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-neon-cyan to-matrix-green transition-all duration-500"
                  style={{ width: `${getBandwidthPercentage()}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground mt-1 font-mono">
                {getBandwidthPercentage().toFixed(1)}% used
              </p>
            </div>

            {/* Connections Count */}
            <div className="pt-2 border-t border-grid-line/30">
              <div className="text-3xl font-display text-neon-purple drop-shadow-glow">
                {usage?.connections_active?.toLocaleString() ?? '0'}
              </div>
              <p className="text-xs text-muted-foreground mt-1">{t('activeConnections') || 'Active Connections'}</p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
