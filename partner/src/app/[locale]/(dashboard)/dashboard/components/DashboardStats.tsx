'use client';

import type { ComponentType } from 'react';
import { Activity, Server, ShieldCheck, UsersRound, WalletCards } from 'lucide-react';
import { useTranslations } from 'next-intl';
import {
  useBandwidthAnalytics,
  usePendingWithdrawals,
  useServerStats,
  useSystemHealth,
  useSystemStats,
} from '../hooks/useDashboardData';
import { cn } from '@/lib/utils';

type HealthStatus = 'healthy' | 'degraded' | 'unhealthy' | 'unknown';

interface MetricCardProps {
  title: string;
  value: string;
  description: string;
  accentClassName: string;
  icon: ComponentType<{ className?: string }>;
  isLoading?: boolean;
  supportingValue?: string;
}

function formatCompactNumber(value: number | undefined) {
  if (typeof value !== 'number') return '--';

  return new Intl.NumberFormat(undefined, {
    notation: 'compact',
    maximumFractionDigits: value >= 1000 ? 1 : 0,
  }).format(value);
}

function formatThroughput(bytes: number | undefined) {
  if (!bytes) return '0 B/s';

  const units = ['B/s', 'KB/s', 'MB/s', 'GB/s', 'TB/s', 'PB/s'];
  let current = bytes;
  let unitIndex = 0;

  while (current >= 1024 && unitIndex < units.length - 1) {
    current /= 1024;
    unitIndex += 1;
  }

  const decimals = current >= 100 ? 0 : 1;
  return `${current.toFixed(decimals)} ${units[unitIndex]}`;
}

function formatCurrencyAmount(amount: number | undefined, currency: string = 'USD') {
  if (typeof amount !== 'number') return '--';

  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

function resolveHealthStatus(status: string | undefined): HealthStatus {
  if (status === 'healthy' || status === 'degraded' || status === 'unhealthy') {
    return status;
  }

  return 'unknown';
}

function countHealthyComponents(
  components: Record<string, { status: string } | undefined> | undefined,
) {
  if (!components) {
    return { healthy: 0, failing: 0 };
  }

  return Object.values(components).reduce(
    (acc, component) => {
      if (component?.status === 'healthy') {
        acc.healthy += 1;
      } else {
        acc.failing += 1;
      }

      return acc;
    },
    { healthy: 0, failing: 0 },
  );
}

function MetricCard({
  title,
  value,
  description,
  accentClassName,
  icon: Icon,
  isLoading = false,
  supportingValue,
}: MetricCardProps) {
  return (
    <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] backdrop-blur">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <p className="text-[11px] font-mono uppercase tracking-[0.24em] text-muted-foreground">
            {title}
          </p>
          <div
            className={cn(
              'text-3xl font-display tracking-[0.14em] text-white md:text-4xl',
              accentClassName,
            )}
          >
            {isLoading ? <span className="animate-pulse text-muted-foreground">...</span> : value}
          </div>
        </div>

        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/70 text-neon-cyan">
          <Icon className="h-5 w-5" />
        </div>
      </div>

      <div className="mt-4 border-t border-grid-line/20 pt-3">
        <p className="text-sm font-mono leading-6 text-foreground/90">{description}</p>
        {supportingValue ? (
          <p className="mt-2 text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
            {supportingValue}
          </p>
        ) : null}
      </div>
    </article>
  );
}

/**
 * Operational metrics at the top of the command center.
 */
export function DashboardStats() {
  const t = useTranslations('Dashboard');
  const { data: health, isPending: isHealthPending } = useSystemHealth();
  const { data: serverStats, isPending: isServerStatsPending } = useServerStats();
  const { data: systemStats, isPending: isSystemStatsPending } = useSystemStats();
  const { data: bandwidth, isPending: isBandwidthPending } = useBandwidthAnalytics();
  const { data: pendingWithdrawals, isPending: isWithdrawalsPending } = usePendingWithdrawals();

  const healthStatus = resolveHealthStatus(health?.status);
  const healthCounts = countHealthyComponents(health?.components);
  const pendingWithdrawalTotal = pendingWithdrawals?.reduce(
    (sum, withdrawal) => sum + withdrawal.amount,
    0,
  );

  return (
    <section
      aria-label={t('opsGridLabel')}
      className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5"
    >
      <MetricCard
        title={t('cards.health.title')}
        value={t(`cards.health.${healthStatus}`)}
        description={t('cards.health.description')}
        supportingValue={`${healthCounts.healthy} ${t('cards.health.componentsHealthy')} / ${healthCounts.failing} ${t('cards.health.componentsFailing')}`}
        accentClassName={cn(
          healthStatus === 'healthy' && 'text-matrix-green drop-shadow-[0_0_18px_rgba(0,255,136,0.28)]',
          healthStatus === 'degraded' && 'text-neon-cyan drop-shadow-[0_0_18px_rgba(0,255,255,0.24)]',
          healthStatus === 'unhealthy' && 'text-neon-pink drop-shadow-[0_0_18px_rgba(255,0,255,0.24)]',
          healthStatus === 'unknown' && 'text-white',
        )}
        icon={ShieldCheck}
        isLoading={isHealthPending}
      />

      <MetricCard
        title={t('cards.servers.title')}
        value={
          typeof serverStats?.online === 'number' && typeof serverStats?.total === 'number'
            ? `${serverStats.online}/${serverStats.total}`
            : '--'
        }
        description={t('cards.servers.description')}
        supportingValue={`${serverStats?.warning ?? 0} warning / ${serverStats?.maintenance ?? 0} maintenance`}
        accentClassName="text-neon-cyan drop-shadow-[0_0_18px_rgba(0,255,255,0.24)]"
        icon={Server}
        isLoading={isServerStatsPending}
      />

      <MetricCard
        title={t('cards.users.title')}
        value={formatCompactNumber(systemStats?.active_users)}
        description={t('cards.users.description')}
        supportingValue={`${formatCompactNumber(systemStats?.total_users)} ${t('labels.totalUsers')}`}
        accentClassName="text-white drop-shadow-[0_0_18px_rgba(255,255,255,0.18)]"
        icon={UsersRound}
        isLoading={isSystemStatsPending}
      />

      <MetricCard
        title={t('cards.bandwidth.title')}
        value={formatThroughput(bandwidth?.bytes_out)}
        description={t('cards.bandwidth.description')}
        supportingValue={`${formatThroughput(bandwidth?.bytes_in)} ${t('labels.inbound')}`}
        accentClassName="text-matrix-green drop-shadow-[0_0_18px_rgba(0,255,136,0.28)]"
        icon={Activity}
        isLoading={isBandwidthPending}
      />

      <MetricCard
        title={t('cards.withdrawals.title')}
        value={formatCompactNumber(pendingWithdrawals?.length)}
        description={t('cards.withdrawals.description')}
        supportingValue={formatCurrencyAmount(pendingWithdrawalTotal)}
        accentClassName="text-neon-pink drop-shadow-[0_0_18px_rgba(255,0,255,0.24)]"
        icon={WalletCards}
        isLoading={isWithdrawalsPending}
      />
    </section>
  );
}
