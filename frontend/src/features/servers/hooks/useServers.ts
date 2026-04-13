import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { serversApi } from '@/lib/api';
import type { operations } from '@/lib/api/generated/types';
import type {
  Server,
  VpnProtocol,
  ServerStatus,
  ServerGovernanceState,
} from '@/entities/server/model/types';

function pollingInterval(intervalMs: number) {
  return (query: { state: { error: unknown } }) => {
    if (query.state.error) return false;
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return false;
    if (typeof navigator !== 'undefined' && !navigator.onLine) return false;
    return intervalMs;
  };
}

type ServerApiResponse =
  operations['list_servers_api_v1_servers__get']['responses'][200]['content']['application/json'][number];

function normalizeProtocol(protocol?: string | null): VpnProtocol {
  const value = protocol?.trim().toLowerCase();
  if (!value) return 'unknown';
  if (value === 'hy2') return 'hysteria2';
  return value as VpnProtocol;
}

function normalizeOptionalValue(value?: string | null): string | null {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

function deriveGovernanceState(raw: ServerApiResponse): ServerGovernanceState {
  if (raw.is_disabled) return 'node-disabled';
  if (raw.active_plugin_uuid) return 'plugin-active';
  return 'no-plugin';
}

function mapServerResponse(raw: ServerApiResponse): Server {
  const statusMap: Record<string, ServerStatus> = {
    online: 'online',
    offline: 'offline',
    warning: 'warning',
    maintenance: 'maintenance',
  };

  return {
    id: raw.uuid,
    name: raw.name,
    location: raw.country_code || raw.address,
    ip: `${raw.address}:${raw.port}`,
    protocol: normalizeProtocol(raw.vpn_protocol),
    status: statusMap[raw.status] ?? 'offline',
    load: raw.users_online ? Math.min(Math.round((raw.users_online / 100) * 100), 100) : 0,
    uptime: raw.created_at ? formatUptime(raw.created_at) : '—',
    clients: raw.users_online ?? 0,
    nodeVersion: normalizeOptionalValue(raw.node_version),
    xrayVersion: normalizeOptionalValue(raw.xray_version),
    activePluginUuid: normalizeOptionalValue(raw.active_plugin_uuid),
    governanceState: deriveGovernanceState(raw),
  };
}

function formatUptime(createdAt: string): string {
  const diff = Date.now() - new Date(createdAt).getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  if (days > 0) return `${days}d ${hours}h`;
  return `${hours}h`;
}

/**
 * Fetches servers from the API using TanStack Query.
 * Uses serversApi.list() and `select` to share cache with dashboard hooks
 * (both use ['servers'] query key with raw API data in cache).
 */
export function useServers() {
  return useQuery({
    queryKey: ['servers'],
    queryFn: async () => {
      const response = await serversApi.list();
      return response.data;
    },
    select: (data) => (data as unknown as ServerApiResponse[]).map(mapServerResponse),
    staleTime: 30_000,
    refetchInterval: pollingInterval(30_000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  });
}
