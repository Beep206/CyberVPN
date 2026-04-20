import { useQuery } from '@tanstack/react-query';
import { entitlementsApi } from '@/lib/api/service-access';

export function useCurrentEntitlements() {
  return useQuery({
    queryKey: ['current-entitlements'],
    queryFn: async () => {
      const response = await entitlementsApi.getCurrent();
      return response.data;
    },
    staleTime: 30 * 1000,
  });
}
