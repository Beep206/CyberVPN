import { QueryClient } from '@tanstack/react-query';
import { describe, expect, it } from 'vitest';
import {
  invalidatePartnerFinanceState,
  invalidatePartnerPayoutAccountEligibility,
} from '../partner-query-invalidation';

describe('partner query invalidation helpers', () => {
  it('invalidates payout lists plus finance summary and statements for a workspace', async () => {
    const queryClient = new QueryClient();
    const workspaceId = 'workspace-1';

    queryClient.setQueryData(['partner-portal', 'workspace-payout-accounts', workspaceId], []);
    queryClient.setQueryData(['partner-portal', 'workspace-payout-history', workspaceId], []);
    queryClient.setQueryData(['partner-portal', 'workspace-finance-summary', workspaceId], { total: 'EUR 10.00' });
    queryClient.setQueryData(['partner-portal', 'workspace-statements', workspaceId], []);
    queryClient.setQueryData(['partner-portal', 'workspace-notifications'], []);
    queryClient.setQueryData(['partner-portal', 'session-bootstrap'], { ok: true });

    await invalidatePartnerFinanceState(queryClient, workspaceId);

    expect(
      queryClient.getQueryState(['partner-portal', 'workspace-payout-accounts', workspaceId])?.isInvalidated,
    ).toBe(true);
    expect(
      queryClient.getQueryState(['partner-portal', 'workspace-payout-history', workspaceId])?.isInvalidated,
    ).toBe(true);
    expect(
      queryClient.getQueryState(['partner-portal', 'workspace-finance-summary', workspaceId])?.isInvalidated,
    ).toBe(true);
    expect(
      queryClient.getQueryState(['partner-portal', 'workspace-statements', workspaceId])?.isInvalidated,
    ).toBe(true);
    expect(queryClient.getQueryState(['partner-portal', 'workspace-notifications'])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(['partner-portal', 'session-bootstrap'])?.isInvalidated).toBe(true);
  });

  it('invalidates payout account eligibility only when the workspace and account are known', async () => {
    const queryClient = new QueryClient();
    const key = [
      'partner-portal',
      'workspace-payout-account-eligibility',
      'workspace-1',
      'account-1',
    ];
    queryClient.setQueryData(key, { eligible: true });

    await invalidatePartnerPayoutAccountEligibility(queryClient, null, 'account-1');
    expect(queryClient.getQueryState(key)?.isInvalidated).toBe(false);

    await invalidatePartnerPayoutAccountEligibility(queryClient, 'workspace-1', 'account-1');
    expect(queryClient.getQueryState(key)?.isInvalidated).toBe(true);
  });
});
