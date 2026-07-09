import type { QueryClient } from '@tanstack/react-query';

export async function invalidatePartnerFinanceState(
  queryClient: QueryClient,
  workspaceId: string | null | undefined,
): Promise<void> {
  if (!workspaceId) {
    return;
  }

  await Promise.all([
    queryClient.invalidateQueries({
      queryKey: ['partner-portal', 'workspace-payout-accounts', workspaceId],
    }),
    queryClient.invalidateQueries({
      queryKey: ['partner-portal', 'workspace-payout-history', workspaceId],
    }),
    queryClient.invalidateQueries({
      queryKey: ['partner-portal', 'workspace-finance-summary', workspaceId],
    }),
    queryClient.invalidateQueries({
      queryKey: ['partner-portal', 'workspace-statements', workspaceId],
    }),
    queryClient.invalidateQueries({
      queryKey: ['partner-portal', 'workspace-notifications'],
    }),
    queryClient.invalidateQueries({
      queryKey: ['partner-portal', 'session-bootstrap'],
    }),
  ]);
}

export async function invalidatePartnerPayoutAccountEligibility(
  queryClient: QueryClient,
  workspaceId: string | null | undefined,
  payoutAccountId: string | null | undefined,
): Promise<void> {
  if (!workspaceId || !payoutAccountId) {
    return;
  }

  await queryClient.invalidateQueries({
    queryKey: [
      'partner-portal',
      'workspace-payout-account-eligibility',
      workspaceId,
      payoutAccountId,
    ],
  });
}
