import { useQuery } from '@tanstack/react-query';
import { commerceApi } from '@/lib/api/commerce';

export function useOrders() {
  return useQuery({
    queryKey: ['orders'],
    queryFn: async () => {
      const response = await commerceApi.listOrders({ limit: 20, offset: 0 });
      return response.data;
    },
    staleTime: 30 * 1000,
  });
}
