'use client';

import { useQuery } from '@tanstack/react-query';
import { serversApi, monitoringApi } from '@/lib/api';

/**
 * Hook to fetch server statistics
 * Includes online/offline counts, average load, total bandwidth
 */
export function useServerStats() {
  return useQuery({
    queryKey: ['servers', 'stats'],
    queryFn: async () => {
      const response = await serversApi.getStats();
      return response.data;
    },
    staleTime: 60_000,
    refetchInterval: 60_000,
  });
}

/**
 * Hook to fetch system monitoring statistics
 * Includes active connections, user count, uptime
 */
export function useSystemStats() {
  return useQuery({
    queryKey: ['monitoring', 'stats'],
    queryFn: async () => {
      const response = await monitoringApi.getStats();
      return response.data;
    },
    staleTime: 60_000,
    refetchInterval: 60_000,
  });
}

/**
 * Hook to fetch bandwidth analytics
 * Includes current throughput, total transferred, peak usage
 */
export function useBandwidthAnalytics() {
  return useQuery({
    queryKey: ['monitoring', 'bandwidth'],
    queryFn: async () => {
      const response = await monitoringApi.getBandwidth();
      return response.data;
    },
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}
