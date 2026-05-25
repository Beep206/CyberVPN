'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import GlobalNetworkScene from '@/3d/scenes/GlobalNetwork';
import { publicNetworkApi } from '@/lib/api';
import {
  buildSceneConnections,
  buildSceneServers,
  pollingInterval,
} from '@/features/network-intelligence/lib/public-network';
import { ServerLocationsList } from './server-locations-list';
import { GlobalMetricsHud } from './global-metrics-hud';

export function NetworkDashboard() {
  const locale = useLocale();
  const t = useTranslations('Network');
  const [activeNodeId, setActiveNodeId] = useState<string | null>(null);

  const regionsQuery = useQuery({
    queryKey: ['public-network-regions'],
    queryFn: async () => {
      const { data } = await publicNetworkApi.getRegions();
      return data;
    },
    staleTime: 30_000,
    refetchInterval: pollingInterval(30_000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
  });

  const regions = useMemo(() => regionsQuery.data?.regions ?? [], [regionsQuery.data?.regions]);
  const sceneServers = useMemo(() => buildSceneServers(regions, locale), [locale, regions]);
  const sceneConnections = useMemo(() => buildSceneConnections(sceneServers), [sceneServers]);

  return (
    <div className="relative w-full min-h-[calc(100vh-4rem)] bg-background text-foreground overflow-hidden flex flex-col md:flex-row">
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,var(--background)_100%)] z-10 pointer-events-none dark:bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.85)_100%)]" />
        <div className="absolute inset-0 overflow-hidden opacity-60 mix-blend-multiply dark:opacity-80 dark:mix-blend-screen">
          <GlobalNetworkScene
            activeNodeId={activeNodeId}
            connections={sceneConnections}
            servers={sceneServers}
          />
        </div>
      </div>

      <div className="relative z-20 w-full h-full flex flex-col md:flex-row p-6 md:p-8 lg:p-12 gap-8 pointer-events-none">
        <div className="w-full md:w-[360px] lg:w-[420px] flex-shrink-0 flex flex-col pointer-events-auto">
          <div className="mb-8">
            <h1 className="font-display text-4xl font-black text-foreground uppercase tracking-tighter drop-shadow-[0_0_10px_rgba(255,255,255,0.3)] dark:text-white dark:mix-blend-difference">
              {t('title')}
            </h1>
            <p className="font-mono text-muted-foreground mt-4 text-sm max-w-sm">
              {t('description')}
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link
                href="/network/dpi-resistance"
                className="inline-flex items-center rounded-full border border-neon-cyan/35 bg-background/60 px-4 py-2 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:border-neon-cyan hover:text-foreground dark:bg-black/40 dark:hover:text-white"
              >
                {t('actions.dpiResistance')}
              </Link>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto no-scrollbar pb-24">
            <ServerLocationsList
              activeNodeId={activeNodeId}
              regions={regions}
              setActiveNodeId={setActiveNodeId}
            />
          </div>
        </div>

        <div className="flex-1 flex flex-col justify-end items-end pointer-events-none">
          <GlobalMetricsHud />
        </div>
      </div>
    </div>
  );
}
