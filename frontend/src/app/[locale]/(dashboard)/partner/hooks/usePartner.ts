import { useQuery } from '@tanstack/react-query';
import { partnerApi } from '@/lib/api/partner';

/**
 * Hook to fetch partner dashboard data
 */
export function usePartnerDashboard() {
  return useQuery({
    queryKey: ['partner-dashboard'],
    queryFn: async () => {
      const response = await partnerApi.getDashboard();
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // Consider data fresh for 2 minutes
    retry: false, // Don't retry if user is not a partner (403)
  });
}

/**
 * Hook to fetch partner codes
 */
export function usePartnerCodes() {
  return useQuery({
    queryKey: ['partner-codes'],
    queryFn: async () => {
      const response = await partnerApi.listCodes();
      return response.data;
    },
    staleTime: 1 * 60 * 1000,
  });
}

/**
 * Hook to fetch partner earnings
 */
export function usePartnerEarnings() {
  return useQuery({
    queryKey: ['partner-earnings'],
    queryFn: async () => {
      const response = await partnerApi.listEarnings();
      return response.data;
    },
    staleTime: 2 * 60 * 1000,
  });
}
