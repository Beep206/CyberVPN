'use client';

import { useQuery } from '@tanstack/react-query';
import { serversApi, monitoringApi } from '@/lib/api';

function pollingInterval(intervalMs: number) {
  return (query: { state: { error: unknown } }) => {
    if (query.state.error) return false;
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return false;
    if (typeof navigator !== 'undefined' && !navigator.onLine) return false;
    return intervalMs;
  };
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
    staleTime: 60_000,
    refetchInterval: pollingInterval(60_000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
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
    refetchInterval: pollingInterval(60_000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
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
    refetchInterval: pollingInterval(30_000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
  });
}

/**
 * Hook to fetch Remnawave build and git metadata
 * Includes panel version, build info, and backend/frontend commits
 */
export function useMonitoringMetadata() {
  return useQuery({
    queryKey: ['monitoring', 'metadata'],
    queryFn: async () => {
      const response = await monitoringApi.getMetadata();
      return response.data;
    },
    staleTime: 60_000,
    refetchInterval: pollingInterval(60_000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
  });
}

/**
 * Hook to fetch Remnawave recap metrics
 * Includes users, nodes, lifetime traffic, and country coverage
 */
export function useMonitoringRecap() {
  return useQuery({
    queryKey: ['monitoring', 'recap'],
    queryFn: async () => {
      const response = await monitoringApi.getRecap();
      return response.data;
    },
    staleTime: 60_000,
    refetchInterval: pollingInterval(60_000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
  });
}
