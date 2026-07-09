import { QueryClient } from '@tanstack/react-query';
import { describe, expect, it } from 'vitest';
import {
  invalidateCustomerSettlementState,
  isMiniAppPrivateAuthQuery,
  resetMiniAppPrivateAuthQueries,
} from '../customer-query-invalidation';

describe('customer query invalidation helpers', () => {
  it('resets every private Mini App auth cache alias without clearing unrelated web caches', async () => {
    const queryClient = new QueryClient();

    queryClient.setQueryData(['miniapp-bootstrap'], { user: 'old-miniapp-user' });
    queryClient.setQueryData(['wallet'], { balance: 100 });
    queryClient.setQueryData(['wallet-transactions'], [{ id: 'old-tx' }]);
    queryClient.setQueryData(['active-devices'], [{ id: 'old-device' }]);
    queryClient.setQueryData(['twofa-status'], { enabled: true });
    queryClient.setQueryData(['antiphishing-code'], { code: 'old-code' });
    queryClient.setQueryData(['partner-dashboard'], { revenue: 10 });
    queryClient.setQueryData(['settings', 'profile'], { email: 'kept@example.test' });

    await resetMiniAppPrivateAuthQueries(queryClient);

    expect(queryClient.getQueryData(['miniapp-bootstrap'])).toBeUndefined();
    expect(queryClient.getQueryData(['wallet'])).toBeUndefined();
    expect(queryClient.getQueryData(['wallet-transactions'])).toBeUndefined();
    expect(queryClient.getQueryData(['active-devices'])).toBeUndefined();
    expect(queryClient.getQueryData(['twofa-status'])).toBeUndefined();
    expect(queryClient.getQueryData(['antiphishing-code'])).toBeUndefined();
    expect(queryClient.getQueryData(['partner-dashboard'])).toBeUndefined();
    expect(queryClient.getQueryData(['settings', 'profile'])).toEqual({
      email: 'kept@example.test',
    });
  });

  it('invalidates settlement and Mini App payment history after confirmed checkout state changes', async () => {
    const queryClient = new QueryClient();

    queryClient.setQueryData(['orders'], [{ id: 'old-order' }]);
    queryClient.setQueryData(['payments', 'history'], [{ id: 'old-payment' }]);
    queryClient.setQueryData(['payments-history', '30d'], [{ id: 'old-analytics-payment' }]);
    queryClient.setQueryData(['miniapp-order-history'], [{ id: 'old-miniapp-order' }]);
    queryClient.setQueryData(['current-entitlements'], { status: 'old' });
    queryClient.setQueryData(['customer-subscriptions'], [{ key: 'old-subscription' }]);
    queryClient.setQueryData(['wallet', 'balance'], { balance: 100 });
    queryClient.setQueryData(['wallet-transactions'], [{ id: 'old-tx' }]);
    queryClient.setQueryData(['miniapp-config'], { url: 'old-config' });

    await invalidateCustomerSettlementState(queryClient, { includeMiniApp: true });

    expect(queryClient.getQueryState(['orders'])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(['payments', 'history'])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(['payments-history', '30d'])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(['miniapp-order-history'])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(['current-entitlements'])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(['customer-subscriptions'])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(['wallet', 'balance'])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(['wallet-transactions'])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryData(['miniapp-config'])).toBeUndefined();
  });

  it('matches Mini App private auth query aliases by prefix or exact root key', () => {
    expect(isMiniAppPrivateAuthQuery(['miniapp-bootstrap'])).toBe(true);
    expect(isMiniAppPrivateAuthQuery(['wallet'])).toBe(true);
    expect(isMiniAppPrivateAuthQuery(['active-devices'])).toBe(true);
    expect(isMiniAppPrivateAuthQuery(['settings', 'profile'])).toBe(false);
  });
});
