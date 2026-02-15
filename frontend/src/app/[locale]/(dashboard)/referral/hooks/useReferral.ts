import { useQuery } from '@tanstack/react-query';
import { referralApi } from '@/lib/api';

function pollingInterval(intervalMs: number) {
  if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return false;
  if (typeof navigator !== 'undefined' && !navigator.onLine) return false;
  return intervalMs;
}

/**
 * Fetch referral program status
 */
export function useReferralStatus() {
  return useQuery({
    queryKey: ['referral', 'status'],
    queryFn: async () => {
      const response = await referralApi.getStatus();
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Fetch user's referral code
 */
export function useReferralCode() {
  return useQuery({
    queryKey: ['referral', 'code'],
    queryFn: async () => {
      const response = await referralApi.getCode();
      return response.data;
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Fetch referral statistics
 */
export function useReferralStats() {
  return useQuery({
    queryKey: ['referral', 'stats'],
    queryFn: async () => {
      const response = await referralApi.getStats();
      return response.data;
    },
    staleTime: 30 * 1000,
    refetchInterval: () => pollingInterval(30 * 1000),
    refetchIntervalInBackground: false,
  });
}

/**
 * Fetch recent referral commissions
 */
export function useRecentCommissions() {
  return useQuery({
    queryKey: ['referral', 'commissions'],
    queryFn: async () => {
      const response = await referralApi.getRecentCommissions();
      return response.data;
    },
    staleTime: 30 * 1000,
  });
}
