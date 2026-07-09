import { QueryClient } from '@tanstack/react-query';
import { describe, expect, it } from 'vitest';
import {
  invalidateAdminCommerceCatalogState,
  invalidateAdminSupportQueues,
  invalidateAdminWithdrawalQueues,
} from '../admin-query-invalidation';

describe('admin query invalidation helpers', () => {
  it('invalidates withdrawal console data and action-queue badge data together', async () => {
    const queryClient = new QueryClient();
    queryClient.setQueryData(['commerce', 'withdrawals', 'pending'], [{ id: 'withdrawal-1' }]);
    queryClient.setQueryData(['admin', 'action-queues', 'withdrawals', 'pending'], 1);

    await invalidateAdminWithdrawalQueues(queryClient);

    expect(queryClient.getQueryState(['commerce', 'withdrawals', 'pending'])?.isInvalidated).toBe(true);
    expect(
      queryClient.getQueryState(['admin', 'action-queues', 'withdrawals', 'pending'])?.isInvalidated,
    ).toBe(true);
  });

  it('invalidates support list, detail, and support action-queue badge data together', async () => {
    const queryClient = new QueryClient();
    queryClient.setQueryData(['support', 'admin', 'tickets'], [{ public_id: 'sup_1' }]);
    queryClient.setQueryData(['support', 'admin', 'tickets', 'sup_1', 'detail'], { public_id: 'sup_1' });
    queryClient.setQueryData(['admin', 'action-queues', 'support', 'tickets', { status: 'pending_support' }], 1);

    await invalidateAdminSupportQueues(queryClient, 'sup_1');

    expect(queryClient.getQueryState(['support', 'admin', 'tickets'])?.isInvalidated).toBe(true);
    expect(
      queryClient.getQueryState(['support', 'admin', 'tickets', 'sup_1', 'detail'])?.isInvalidated,
    ).toBe(true);
    expect(
      queryClient.getQueryState(['admin', 'action-queues', 'support', 'tickets', { status: 'pending_support' }])
        ?.isInvalidated,
    ).toBe(true);
  });

  it('invalidates plan, pricebook, catalog preview, and storefront preview caches together', async () => {
    const queryClient = new QueryClient();
    queryClient.setQueryData(['commerce', 'plans', 'admin'], [{ uuid: 'plan-1' }]);
    queryClient.setQueryData(['commerce', 'pricebooks', 'admin', 'lifecycle'], [{ id: 'pricebook-1' }]);
    queryClient.setQueryData(['commerce', 'catalog-preview', { currency: 'USD' }], { items: [] });
    queryClient.setQueryData(['commerce', 'storefront-preview', 'web', 'USD'], { items: [] });
    queryClient.setQueryData(['commerce', 'pricebooks', 'history', 'default'], { items: [] });
    queryClient.setQueryData(['commerce', 'pricebooks', 'audit', 'pricebook-1'], []);
    queryClient.setQueryData(['commerce', 'pricebooks', 'validation', 'pricebook-1'], { ok: true });

    await invalidateAdminCommerceCatalogState(queryClient);

    expect(queryClient.getQueryState(['commerce', 'plans', 'admin'])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(['commerce', 'pricebooks', 'admin', 'lifecycle'])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(['commerce', 'catalog-preview', { currency: 'USD' }])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(['commerce', 'storefront-preview', 'web', 'USD'])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(['commerce', 'pricebooks', 'history', 'default'])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(['commerce', 'pricebooks', 'audit', 'pricebook-1'])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(['commerce', 'pricebooks', 'validation', 'pricebook-1'])?.isInvalidated)
      .toBe(true);
  });
});
