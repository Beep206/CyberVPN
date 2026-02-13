'use client';

import { useTranslations } from 'next-intl';
import { ServerCard } from '@/shared/ui/molecules/server-card';
import { useServers } from '@/features/servers/hooks/useServers';

/**
 * Server grid component
 * Displays all VPN servers in a responsive grid with real-time status
 */
export function ServerGrid() {
  const t = useTranslations('Dashboard');
  const { data: servers, isPending, error } = useServers();

  if (error) {
    return (
      <div className="cyber-card p-8 text-center">
        <p className="text-red-500 font-mono">
          {t('errorLoadingServers') || 'Error loading servers'}
        </p>
        <p className="text-sm text-muted-foreground mt-2">
          {error instanceof Error ? error.message : 'Unknown error'}
        </p>
      </div>
    );
  }

  if (isPending) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="cyber-card p-6 rounded-xl animate-pulse">
            <div className="h-4 bg-grid-line/30 rounded w-3/4 mb-4" />
            <div className="h-3 bg-grid-line/20 rounded w-1/2 mb-2" />
            <div className="h-3 bg-grid-line/20 rounded w-2/3" />
          </div>
        ))}
      </div>
    );
  }

  if (!servers || servers.length === 0) {
    return (
      <div className="cyber-card p-8 text-center">
        <p className="text-muted-foreground font-mono">
          {t('noServers') || 'No servers available'}
        </p>
      </div>
    );
  }

  // Map canonical Server type to ServerCard format
  const transformedServers = servers.map((server) => ({
    id: server.id,
    name: server.name,
    location: server.location,
    status: server.status,
    ip: server.ip,
    load: server.load,
    protocol: server.protocol,
  }));

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {transformedServers.map((server) => (
        <ServerCard key={server.id} server={server} />
      ))}
    </div>
  );
}
