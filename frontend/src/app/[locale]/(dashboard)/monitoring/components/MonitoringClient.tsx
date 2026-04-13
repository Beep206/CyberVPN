'use client';

import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { motion } from 'motion/react';
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  Server,
  Database,
  Activity,
  Zap,
  Clock,
} from 'lucide-react';
import { monitoringApi } from '@/lib/api';
import type { operations } from '@/lib/api/generated/types';

type HealthResponse =
  operations['health_check_api_v1_monitoring_health_get']['responses'][200]['content']['application/json'];
type StatsResponse =
  operations['get_system_stats_api_v1_monitoring_stats_get']['responses'][200]['content']['application/json'];
type BandwidthResponse =
  operations['get_bandwidth_analytics_api_v1_monitoring_bandwidth_get']['responses'][200]['content']['application/json'];
type MetadataResponse =
  operations['get_metadata_api_v1_monitoring_metadata_get']['responses'][200]['content']['application/json'];
type RecapResponse =
  operations['get_recap_api_v1_monitoring_recap_get']['responses'][200]['content']['application/json'];

type HealthStatus = HealthResponse['status'];
type ComponentStatus = NonNullable<HealthResponse['components']>[string]['status'];

const SERVICE_DEFINITIONS = [
  {
    key: 'remnawave',
    name: 'Remnawave API',
    Icon: Server,
    accentClass: 'text-neon-cyan',
  },
  {
    key: 'database',
    name: 'PostgreSQL Database',
    Icon: Database,
    accentClass: 'text-neon-purple',
  },
  {
    key: 'redis',
    name: 'Redis Cache',
    Icon: Zap,
    accentClass: 'text-matrix-green',
  },
] as const;

function pollingInterval(intervalMs: number) {
  return (query: { state: { error: unknown } }) => {
    if (query.state.error) return false;
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return false;
    if (typeof navigator !== 'undefined' && !navigator.onLine) return false;
    return intervalMs;
  };
}

function formatTraffic(bytes: number | null | undefined) {
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
}

function formatTimestamp(value: string | null | undefined) {
  if (!value || value === 'unknown') return 'Unknown';

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;

  return parsed.toLocaleString();
}

function shortSha(value: string | null | undefined) {
  if (!value || value === 'unknown') return 'unknown';
  return value.slice(0, 7);
}

function getStatusIcon(status: HealthStatus | ComponentStatus) {
  switch (status) {
    case 'healthy':
      return <CheckCircle className="h-6 w-6 text-matrix-green" />;
    case 'degraded':
      return <AlertCircle className="h-6 w-6 text-neon-pink" />;
    case 'unhealthy':
      return <XCircle className="h-6 w-6 text-red-500" />;
  }
}

function getStatusColor(status: HealthStatus | ComponentStatus) {
  switch (status) {
    case 'healthy':
      return 'border-matrix-green/50 bg-matrix-green/5';
    case 'degraded':
      return 'border-neon-pink/50 bg-neon-pink/5';
    case 'unhealthy':
      return 'border-red-500/50 bg-red-500/5';
  }
}

function getStatusText(status: HealthStatus | ComponentStatus) {
  switch (status) {
    case 'healthy':
      return 'Operational';
    case 'degraded':
      return 'Degraded';
    case 'unhealthy':
      return 'Unavailable';
  }
}

function CommitValue({
  commitSha,
  commitUrl,
}: {
  commitSha: string;
  commitUrl: string;
}) {
  const label = shortSha(commitSha);

  if (!commitUrl) {
    return <span>{label}</span>;
  }

  return (
    <a
      href={commitUrl}
      target="_blank"
      rel="noreferrer"
      className="transition-colors hover:text-neon-cyan"
    >
      {label}
    </a>
  );
}

/**
 * Monitoring Client Component
 * Displays control-plane health, build metadata, recap, and live activity.
 */
export function MonitoringClient() {
  const { data: healthData, isLoading: healthLoading } = useQuery({
    queryKey: ['monitoring', 'health'],
    queryFn: async () => {
      const response = await monitoringApi.health();
      return response.data;
    },
    staleTime: 30 * 1000,
    refetchInterval: pollingInterval(30 * 1000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  });

  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['monitoring', 'stats'],
    queryFn: async () => {
      const response = await monitoringApi.getStats();
      return response.data;
    },
    staleTime: 30 * 1000,
    refetchInterval: pollingInterval(30 * 1000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  });

  const { data: bandwidthData, isLoading: bandwidthLoading } = useQuery({
    queryKey: ['monitoring', 'bandwidth'],
    queryFn: async () => {
      const response = await monitoringApi.getBandwidth();
      return response.data;
    },
    staleTime: 30 * 1000,
    refetchInterval: pollingInterval(30 * 1000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  });

  const { data: metadataData, isLoading: metadataLoading } = useQuery({
    queryKey: ['monitoring', 'metadata'],
    queryFn: async () => {
      const response = await monitoringApi.getMetadata();
      return response.data;
    },
    staleTime: 60 * 1000,
    refetchInterval: pollingInterval(60 * 1000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  });

  const { data: recapData, isLoading: recapLoading } = useQuery({
    queryKey: ['monitoring', 'recap'],
    queryFn: async () => {
      const response = await monitoringApi.getRecap();
      return response.data;
    },
    staleTime: 60 * 1000,
    refetchInterval: pollingInterval(60 * 1000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  });

  const isLoading =
    healthLoading ||
    statsLoading ||
    bandwidthLoading ||
    metadataLoading ||
    recapLoading;

  if (
    isLoading ||
    !healthData ||
    !statsData ||
    !bandwidthData ||
    !metadataData ||
    !recapData
  ) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="h-16 w-16 animate-spin rounded-full border-b-2 border-neon-cyan" />
      </div>
    );
  }

  const health = healthData as HealthResponse;
  const stats = statsData as StatsResponse;
  const bandwidth = bandwidthData as BandwidthResponse;
  const metadata = metadataData as MetadataResponse;
  const recap = recapData as RecapResponse;

  const services = SERVICE_DEFINITIONS.map(({ key, ...definition }) => {
    const component = health.components?.[key];
    return {
      ...definition,
      status: component?.status ?? ('unhealthy' as ComponentStatus),
      message: component?.message ?? 'No component status available',
      responseTime: component?.response_time_ms ?? null,
    };
  });

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`cyber-card border-2 p-6 ${getStatusColor(health.status)}`}
      >
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-4">
            {getStatusIcon(health.status)}
            <div>
              <h2 className="text-2xl font-display text-matrix-green">
                All Systems {getStatusText(health.status)}
              </h2>
              <p className="mt-1 font-mono text-sm text-muted-foreground">
                Last updated: {formatTimestamp(health.timestamp)}
              </p>
            </div>
          </div>
          <div className="text-right font-mono text-sm text-muted-foreground">
            <div>
              {services.filter((service) => service.status === 'healthy').length} / {services.length} services healthy
            </div>
            <div>Remnawave {metadata.version}</div>
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
        {services.map((service) => (
          <motion.div
            key={service.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`cyber-card border p-6 ${getStatusColor(service.status)}`}
          >
            <div className="mb-4 flex items-start justify-between">
              <div className="flex items-center gap-3">
                <service.Icon className={`h-5 w-5 ${service.accentClass}`} />
                <h3 className="text-sm font-mono text-muted-foreground">{service.name}</h3>
              </div>
              {getStatusIcon(service.status)}
            </div>

            <div className="space-y-3">
              <div>
                <p className="mb-1 text-xs text-muted-foreground">Status</p>
                <p className="text-xl font-display text-foreground">{getStatusText(service.status)}</p>
              </div>

              <div>
                <p className="mb-1 text-xs text-muted-foreground">Details</p>
                <p className="text-sm font-mono text-muted-foreground">{service.message}</p>
              </div>

              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Latency</span>
                <span className="font-mono text-matrix-green">
                  {service.responseTime != null ? `${service.responseTime.toFixed(0)} ms` : 'n/a'}
                </span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="cyber-card p-6">
          <div className="mb-4 flex items-center gap-3">
            <Server className="h-5 w-5 text-neon-cyan" />
            <h3 className="text-sm font-mono text-muted-foreground">Panel Version</h3>
          </div>
          <p className="text-3xl font-display text-neon-cyan">{metadata.version}</p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="cyber-card p-6">
          <div className="mb-4 flex items-center gap-3">
            <Clock className="h-5 w-5 text-neon-purple" />
            <h3 className="text-sm font-mono text-muted-foreground">Build</h3>
          </div>
          <p className="text-3xl font-display text-neon-purple">#{metadata.build.number}</p>
          <p className="mt-2 font-mono text-xs text-muted-foreground">
            {formatTimestamp(metadata.build.time)}
          </p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="cyber-card p-6">
          <div className="mb-4 flex items-center gap-3">
            <Activity className="h-5 w-5 text-matrix-green" />
            <h3 className="text-sm font-mono text-muted-foreground">Backend Git</h3>
          </div>
          <p className="text-3xl font-display text-matrix-green">
            <CommitValue
              commitSha={metadata.git.backend.commit_sha}
              commitUrl={metadata.git.backend.commit_url}
            />
          </p>
          <p className="mt-2 font-mono text-xs text-muted-foreground">{metadata.git.backend.branch}</p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="cyber-card p-6">
          <div className="mb-4 flex items-center gap-3">
            <Zap className="h-5 w-5 text-neon-pink" />
            <h3 className="text-sm font-mono text-muted-foreground">Frontend Git</h3>
          </div>
          <p className="text-3xl font-display text-neon-pink">
            <CommitValue
              commitSha={metadata.git.frontend.commit_sha}
              commitUrl={metadata.git.frontend.commit_url}
            />
          </p>
          <p className="mt-2 font-mono text-xs text-muted-foreground">
            Captured {formatTimestamp(metadata.timestamp)}
          </p>
        </motion.div>
      </div>

      <div className="cyber-card p-6">
        <div className="mb-6 flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-lg font-display text-matrix-green">Remnawave Recap</h3>
            <p className="text-sm font-mono text-muted-foreground">
              Initialized {formatTimestamp(recap.init_date)}
            </p>
          </div>
          <div className="font-mono text-xs text-muted-foreground">
            Current month: {recap.this_month?.users.toLocaleString() ?? 0} users / {formatTraffic(recap.this_month?.traffic_bytes)}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-lg border border-grid-line/30 bg-terminal-surface/40 p-4">
            <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Total Users</p>
            <p className="text-3xl font-display text-neon-cyan">{recap.total.users.toLocaleString()}</p>
          </div>

          <div className="rounded-lg border border-grid-line/30 bg-terminal-surface/40 p-4">
            <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Nodes</p>
            <p className="text-3xl font-display text-matrix-green">{recap.total.nodes.toLocaleString()}</p>
          </div>

          <div className="rounded-lg border border-grid-line/30 bg-terminal-surface/40 p-4">
            <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Lifetime Traffic</p>
            <p className="text-3xl font-display text-neon-purple">{formatTraffic(recap.total.traffic_bytes)}</p>
          </div>

          <div className="rounded-lg border border-grid-line/30 bg-terminal-surface/40 p-4">
            <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Countries</p>
            <p className="text-3xl font-display text-neon-pink">
              {(recap.total.distinct_countries ?? 0).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="cyber-card p-6">
          <div className="mb-4 flex items-center gap-3">
            <Activity className="h-5 w-5 text-neon-cyan" />
            <h3 className="text-sm font-mono text-muted-foreground">Active Users</h3>
          </div>
          <p className="text-3xl font-display text-neon-cyan">{stats.active_users.toLocaleString()}</p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="cyber-card p-6">
          <div className="mb-4 flex items-center gap-3">
            <Server className="h-5 w-5 text-matrix-green" />
            <h3 className="text-sm font-mono text-muted-foreground">Nodes Online</h3>
          </div>
          <p className="text-3xl font-display text-matrix-green">
            {stats.online_servers.toLocaleString()} / {stats.total_servers.toLocaleString()}
          </p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="cyber-card p-6">
          <div className="mb-4 flex items-center gap-3">
            <Zap className="h-5 w-5 text-neon-purple" />
            <h3 className="text-sm font-mono text-muted-foreground">Traffic Today</h3>
          </div>
          <p className="text-3xl font-display text-neon-purple">{formatTraffic(bandwidth.bytes_out)}</p>
          <p className="mt-2 font-mono text-xs text-muted-foreground">
            Window: {bandwidth.period}
          </p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="cyber-card p-6">
          <div className="mb-4 flex items-center gap-3">
            <Clock className="h-5 w-5 text-neon-pink" />
            <h3 className="text-sm font-mono text-muted-foreground">Traffic Lifetime</h3>
          </div>
          <p className="text-3xl font-display text-neon-pink">{formatTraffic(stats.total_traffic_bytes)}</p>
        </motion.div>
      </div>
    </div>
  );
}
