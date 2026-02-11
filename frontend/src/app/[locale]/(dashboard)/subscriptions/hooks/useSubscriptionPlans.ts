import { useQuery } from '@tanstack/react-query';
import { plansApi } from '@/lib/api/plans';

/**
 * Hook to fetch available subscription plans
 * Uses TanStack Query for caching and automatic refetching
 */
export function useSubscriptionPlans() {
  return useQuery({
    queryKey: ['subscription-plans'],
    queryFn: async () => {
      const response = await plansApi.list();
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // Consider data fresh for 5 minutes
  });
}
