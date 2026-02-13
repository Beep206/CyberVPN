import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { serversApi } from '@/lib/api';
import type { Server, VpnProtocol, ServerStatus } from '@/entities/server/model/types';

interface ServerApiResponse {
  uuid: string;
  name: string;
  address: string;
  port: number;
  status: ServerStatus;
  is_connected: boolean;
  is_disabled: boolean;
  country_code?: string;
  city?: string;
  traffic_used_bytes?: number;
  users_online?: number;
  created_at?: string;
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
    location: [raw.city, raw.country_code].filter(Boolean).join(', ') || raw.address,
    ip: `${raw.address}:${raw.port}`,
    protocol: 'wireguard' as VpnProtocol,
    status: statusMap[raw.status] ?? 'offline',
    load: raw.users_online ? Math.min(Math.round((raw.users_online / 100) * 100), 100) : 0,
    uptime: raw.created_at ? formatUptime(raw.created_at) : '—',
    clients: raw.users_online ?? 0,
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
    refetchInterval: 30_000,
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  });
}
