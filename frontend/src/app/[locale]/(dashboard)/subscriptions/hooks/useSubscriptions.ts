'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { subscriptionsApi, paymentsApi } from '@/lib/api';

/**
 * Hook to fetch user's subscription list
 */
export function useSubscriptions() {
  return useQuery({
    queryKey: ['subscriptions'],
    queryFn: async () => {
      const response = await subscriptionsApi.list();
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch a specific subscription by UUID
 */
export function useSubscription(uuid: string | null) {
  return useQuery({
    queryKey: ['subscriptions', uuid],
    queryFn: async () => {
      if (!uuid) throw new Error('UUID required');
      const response = await subscriptionsApi.get(uuid);
      return response.data;
    },
    enabled: !!uuid, // Only fetch if UUID is provided
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Hook to create a payment invoice for subscription purchase
 * Returns mutation for initiating payment
 */
export function useCreateInvoice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: {
      user_uuid: string;
      plan_id: string;
      currency: string;
    }) => {
      const response = await paymentsApi.createInvoice(data);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate subscriptions query to refetch after successful payment
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
    },
  });
}

/**
 * Hook to check payment invoice status
 * Polls every 5 seconds while pending
 */
export function useInvoiceStatus(invoiceId: string | null) {
  return useQuery({
    queryKey: ['invoice', invoiceId],
    queryFn: async () => {
      if (!invoiceId) throw new Error('Invoice ID required');
      const response = await paymentsApi.getInvoiceStatus(invoiceId);
      return response.data;
    },
    enabled: !!invoiceId,
    refetchInterval: (query) => {
      // Stop polling if payment is completed or failed
      const status = query.state.data?.status;
      if (status && (status === 'paid' || status === 'failed' || status === 'expired')) {
        return false;
      }
      return 5000; // Poll every 5 seconds while pending
    },
  });
}
