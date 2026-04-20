'use client';

import {
  Cpu,
  Network,
  Route,
  ShieldCheck,
  TowerControl,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { monitoringApi } from '@/lib/api/monitoring';
import { serversApi } from '@/lib/api/servers';
import {
  configProfilesApi,
  helixApi,
  hostsApi,
  nodePluginsApi,
} from '@/lib/api/infrastructure';
import { InfrastructurePageShell } from '@/features/infrastructure/components/infrastructure-page-shell';
import { InfrastructureStatusChip } from '@/features/infrastructure/components/infrastructure-status-chip';
import { InfrastructureEmptyState } from '@/features/infrastructure/components/empty-state';
import {
  formatBytes,
  formatCompactNumber,
  formatDateTime,
  humanizeToken,
} from '@/features/infrastructure/lib/formatting';

function toneForHealth(status: string | undefined) {
  if (status === 'healthy') return 'success' as const;
  if (status === 'degraded') return 'warning' as const;
  return 'danger' as const;
}

function toneForServerStatus(status: string) {
  if (status === 'online') return 'success' as const;
  if (status === 'warning') return 'warning' as const;
  if (status === 'maintenance') return 'info' as const;
  return 'danger' as const;
}

export function InfrastructureOverview() {
  const t = useTranslations('Infrastructure');

  const healthQuery = useQuery({
    queryKey: ['infrastructure', 'health'],
    queryFn: async () => {
      const response = await monitoringApi.health();
      return response.data;
    },
    staleTime: 10_000,
  });

  const systemStatsQuery = useQuery({
    queryKey: ['infrastructure', 'system-stats'],
    queryFn: async () => {
      const response = await monitoringApi.getStats();
      return response.data;
    },
    staleTime: 15_000,
  });

  const bandwidthQuery = useQuery({
    queryKey: ['infrastructure', 'bandwidth'],
    queryFn: async () => {
      const response = await monitoringApi.getBandwidth({ period: 'today' });
      return response.data;
    },
    staleTime: 15_000,
  });

  const serverStatsQuery = useQuery({
    queryKey: ['infrastructure', 'server-stats'],
    queryFn: async () => {
      const response = await serversApi.getStats();
      return response.data;
    },
    staleTime: 15_000,
  });

  const serversQuery = useQuery({
    queryKey: ['infrastructure', 'servers'],
    queryFn: async () => {
      const response = await serversApi.list();
      return response.data;
    },
    staleTime: 30_000,
  });

  const hostsQuery = useQuery({
    queryKey: ['infrastructure', 'hosts'],
    queryFn: async () => {
      const response = await hostsApi.list();
      return response.data;
    },
    staleTime: 30_000,
  });

  const configProfilesQuery = useQuery({
    queryKey: ['infrastructure', 'config-profiles'],
    queryFn: async () => {
      const response = await configProfilesApi.list();
      return response.data;
    },
    staleTime: 30_000,
  });

  const nodePluginsQuery = useQuery({
    queryKey: ['infrastructure', 'node-plugins'],
    queryFn: async () => {
      const response = await nodePluginsApi.list();
      return response.data;
    },
    staleTime: 30_000,
  });

  const helixNodesQuery = useQuery({
    queryKey: ['infrastructure', 'helix', 'nodes'],
    queryFn: async () => {
      const response = await helixApi.listNodes();
      return response.data;
    },
    staleTime: 30_000,
    retry: false,
  });

  const health = healthQuery.data;
  const servers = serversQuery.data ?? [];
  const hosts = hostsQuery.data ?? [];
  const profiles = configProfilesQuery.data ?? [];
  const nodePlugins = nodePluginsQuery.data?.nodePlugins ?? [];
  const helixNodes = helixNodesQuery.data ?? [];

  return (
    <InfrastructurePageShell
      eyebrow={t('overview.eyebrow')}
      title={t('overview.title')}
      description={t('overview.description')}
      icon={TowerControl}
      metrics={[
        {
          label: t('overview.metrics.health'),
          value: health?.status ? humanizeToken(health.status) : '--',
          hint: t('overview.metrics.healthHint'),
          tone: toneForHealth(health?.status),
        },
        {
          label: t('overview.metrics.servers'),
          value: formatCompactNumber(serverStatsQuery.data?.total),
          hint: `${serverStatsQuery.data?.online ?? 0} ${t('overview.metrics.serversHint')}`,
          tone: 'info',
        },
        {
          label: t('overview.metrics.traffic'),
          value: formatBytes(systemStatsQuery.data?.total_traffic_bytes),
          hint: t('overview.metrics.trafficHint'),
          tone: 'warning',
        },
        {
          label: t('overview.metrics.plugins'),
          value: formatCompactNumber(nodePlugins.length),
          hint: `${helixNodes.length} ${t('overview.metrics.pluginsHint')}`,
          tone: 'success',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('overview.routesTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('overview.routesDescription')}
          </p>
          <div className="mt-5 grid gap-3">
            {[
              { href: '/infrastructure/servers', title: t('nav.servers'), description: t('overview.routes.servers') },
              { href: '/infrastructure/hosts', title: t('nav.hosts'), description: t('overview.routes.hosts') },
              { href: '/infrastructure/config-profiles', title: t('nav.configProfiles'), description: t('overview.routes.configProfiles') },
              { href: '/infrastructure/node-plugins', title: t('nav.nodePlugins'), description: t('overview.routes.nodePlugins') },
              { href: '/infrastructure/xray', title: t('nav.xray'), description: t('overview.routes.xray') },
              { href: '/infrastructure/helix', title: t('nav.helix'), description: t('overview.routes.helix') },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4 transition-colors hover:border-neon-cyan/35 hover:bg-terminal-bg/60"
              >
                <p className="text-sm font-display uppercase tracking-[0.18em] text-white">
                  {item.title}
                </p>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {item.description}
                </p>
              </Link>
            ))}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.healthTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('overview.healthDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-3">
            {health?.components ? (
              Object.entries(health.components).map(([key, component]) => (
                <div
                  key={key}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {humanizeToken(key)}
                    </p>
                    <InfrastructureStatusChip
                      label={humanizeToken(component.status)}
                      tone={toneForHealth(component.status)}
                    />
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {component.message}
                  </p>
                </div>
              ))
            ) : (
              <InfrastructureEmptyState label={t('common.empty')} />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <Network className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.serversTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('overview.serversDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {servers.length ? (
              servers.slice(0, 5).map((server) => (
                <div
                  key={server.uuid}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {server.name}
                      </p>
                      <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {server.address}:{server.port}
                      </p>
                    </div>
                    <InfrastructureStatusChip
                      label={humanizeToken(server.status)}
                      tone={toneForServerStatus(server.status)}
                    />
                  </div>
                  <p className="mt-3 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {server.users_online} {t('overview.usersOnline')}
                  </p>
                </div>
              ))
            ) : (
              <InfrastructureEmptyState label={t('common.empty')} />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <Cpu className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.helixTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('overview.helixDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2">
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('overview.helixNodes')}
              </p>
              <p className="mt-3 text-2xl font-display tracking-[0.12em] text-white">
                {formatCompactNumber(helixNodes.length)}
              </p>
            </div>
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('overview.hosts')}
              </p>
              <p className="mt-3 text-2xl font-display tracking-[0.12em] text-white">
                {formatCompactNumber(hosts.length)}
              </p>
            </div>
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('overview.profiles')}
              </p>
              <p className="mt-3 text-2xl font-display tracking-[0.12em] text-white">
                {formatCompactNumber(profiles.length)}
              </p>
            </div>
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('overview.bandwidth')}
              </p>
              <p className="mt-3 text-2xl font-display tracking-[0.12em] text-white">
                {formatBytes(
                  (bandwidthQuery.data?.bytes_in ?? 0) +
                    (bandwidthQuery.data?.bytes_out ?? 0),
                )}
              </p>
            </div>
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-12">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <Route className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.platformPulseTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('overview.platformPulseDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-4">
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('overview.activeUsers')}
              </p>
              <p className="mt-3 text-2xl font-display tracking-[0.12em] text-white">
                {formatCompactNumber(systemStatsQuery.data?.active_users)}
              </p>
            </div>
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('overview.totalUsers')}
              </p>
              <p className="mt-3 text-2xl font-display tracking-[0.12em] text-white">
                {formatCompactNumber(systemStatsQuery.data?.total_users)}
              </p>
            </div>
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('overview.totalServers')}
              </p>
              <p className="mt-3 text-2xl font-display tracking-[0.12em] text-white">
                {formatCompactNumber(systemStatsQuery.data?.total_servers)}
              </p>
            </div>
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('overview.lastHealthCheck')}
              </p>
              <p className="mt-3 text-sm font-mono leading-6 text-white">
                {formatDateTime(health?.timestamp)}
              </p>
            </div>
          </div>
        </article>
      </div>
    </InfrastructurePageShell>
  );
}
