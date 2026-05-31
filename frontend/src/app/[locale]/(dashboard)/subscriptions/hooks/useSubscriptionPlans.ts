import { useQuery } from '@tanstack/react-query';
import { commercialCatalogApi } from '@/lib/api/commercial-catalog';
import { mapPublicCatalogToSubscriptionPlans } from '../lib/plan-presenter';

/**
 * Hook to fetch available subscription plans
 * Uses TanStack Query for caching and automatic refetching
 */
export function useSubscriptionPlans() {
  return useQuery({
    queryKey: ['subscription-plans', 'commercial-catalog', 'web'],
    queryFn: async () => {
      const response = await commercialCatalogApi.getCatalog({ channel: 'web' });
      return mapPublicCatalogToSubscriptionPlans(response.data);
    },
    staleTime: 5 * 60 * 1000, // Consider data fresh for 5 minutes
  });
}
