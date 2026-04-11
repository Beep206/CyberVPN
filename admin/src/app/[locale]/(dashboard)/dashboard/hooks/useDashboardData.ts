'use client';

import { useQuery } from '@tanstack/react-query';
import {
  adminWalletApi,
  governanceApi,
  monitoringApi,
  paymentsApi,
  serversApi,
} from '@/lib/api';

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

export function useSystemHealth() {
  return useQuery({
    queryKey: ['monitoring', 'health'],
    queryFn: async () => {
      const response = await monitoringApi.health();
      return response.data;
    },
    staleTime: 30_000,
    refetchInterval: pollingInterval(30_000),
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

export function usePendingWithdrawals() {
  return useQuery({
    queryKey: ['admin', 'withdrawals', 'pending'],
    queryFn: async () => {
      const response = await adminWalletApi.getPendingWithdrawals();
      return response.data;
    },
    staleTime: 30_000,
    refetchInterval: pollingInterval(30_000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
  });
}

export function useRecentPayments() {
  return useQuery({
    queryKey: ['payments', 'history', { limit: 5 }],
    queryFn: async () => {
      const response = await paymentsApi.getHistory({ offset: 0, limit: 5 });
      return response.data.payments;
    },
    staleTime: 30_000,
    refetchInterval: pollingInterval(30_000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
  });
}

export function useRecentAuditLogs() {
  return useQuery({
    queryKey: ['admin', 'audit-log', { page: 1, pageSize: 5 }],
    queryFn: async () => {
      const response = await governanceApi.getAuditLogs({ page: 1, page_size: 5 });
      return response.data;
    },
    staleTime: 30_000,
    refetchInterval: pollingInterval(30_000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
  });
}

export function useRecentWebhookLogs() {
  return useQuery({
    queryKey: ['admin', 'webhook-log', { page: 1, pageSize: 5 }],
    queryFn: async () => {
      const response = await governanceApi.getWebhookLogs({ page: 1, page_size: 5 });
      return response.data;
    },
    staleTime: 30_000,
    refetchInterval: pollingInterval(30_000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
  });
}
