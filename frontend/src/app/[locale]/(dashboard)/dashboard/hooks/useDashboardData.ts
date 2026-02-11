'use client';

import { useQuery } from '@tanstack/react-query';
import { serversApi, monitoringApi } from '@/lib/api';

/**
 * Hook to fetch server list
 * Refetches every 30 seconds to keep server status current
 */
export function useServers() {
  return useQuery({
    queryKey: ['servers'],
    queryFn: async () => {
      const response = await serversApi.list();
      return response.data;
    },
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 30 * 1000, // Auto-refetch every 30 seconds
  });
}

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
    staleTime: 30 * 1000,
    refetchInterval: 30 * 1000,
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
    staleTime: 30 * 1000,
    refetchInterval: 30 * 1000,
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
    staleTime: 10 * 1000, // 10 seconds - more frequent for real-time metrics
    refetchInterval: 10 * 1000,
  });
}
