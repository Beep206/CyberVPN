import { useQuery } from '@tanstack/react-query';
import { paymentsApi } from '@/lib/api';

/**
 * Fetch payment history
 */
export function usePaymentHistory() {
  return useQuery({
    queryKey: ['payments', 'history'],
    queryFn: async () => {
      const response = await paymentsApi.getHistory();
      return response.data;
    },
    staleTime: 30 * 1000,
  });
}
