import type { QueryClient } from '@tanstack/react-query';

export async function invalidateAdminWithdrawalQueues(queryClient: QueryClient): Promise<void> {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ['commerce', 'withdrawals', 'pending'] }),
    queryClient.invalidateQueries({ queryKey: ['admin', 'action-queues', 'withdrawals', 'pending'] }),
  ]);
}

export async function invalidateAdminSupportQueues(
  queryClient: QueryClient,
  ticketRef: string | null,
): Promise<void> {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ['support', 'admin', 'tickets'] }),
    queryClient.invalidateQueries({ queryKey: ['admin', 'action-queues', 'support', 'tickets'] }),
    ...(ticketRef
      ? [
          queryClient.invalidateQueries({
            queryKey: ['support', 'admin', 'tickets', ticketRef, 'detail'],
          }),
        ]
      : []),
  ]);
}

export async function invalidateAdminCommerceCatalogState(queryClient: QueryClient): Promise<void> {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ['commerce', 'plans'] }),
    queryClient.invalidateQueries({ queryKey: ['commerce', 'pricebooks'] }),
    queryClient.invalidateQueries({ queryKey: ['commerce', 'offers'] }),
    queryClient.invalidateQueries({ queryKey: ['commerce', 'catalog-preview'] }),
    queryClient.invalidateQueries({ queryKey: ['commerce', 'storefront-preview'] }),
    queryClient.invalidateQueries({ queryKey: ['commerce', 'pricebooks', 'history'] }),
    queryClient.invalidateQueries({ queryKey: ['commerce', 'pricebooks', 'audit'] }),
    queryClient.invalidateQueries({ queryKey: ['commerce', 'pricebooks', 'validation'] }),
  ]);
}
