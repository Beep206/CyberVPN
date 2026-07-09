import type { QueryClient, QueryKey } from '@tanstack/react-query';

const MINIAPP_ACCESS_INVALIDATE_KEYS = [
  ['miniapp-offers'],
  ['miniapp-bootstrap'],
  ['usage'],
  ['miniapp-profile-invites'],
] satisfies QueryKey[];

const CUSTOMER_SETTLEMENT_INVALIDATE_KEYS = [
  ['orders'],
  ['payments', 'history'],
  ['payments-history'],
  ['current-entitlements'],
  ['current-service-state'],
  ['subscriptions'],
  ['customer-subscriptions'],
  ['wallet'],
  ['trial-status'],
  ['subscription-cabinet'],
  ['customer-cabinet', 'entitlement'],
  ['customer-cabinet', 'service-state'],
  ['customer-cabinet', 'usage'],
  ['customer-cabinet', 'wallet'],
] satisfies QueryKey[];

const MINIAPP_SETTLEMENT_INVALIDATE_KEYS = [
  ['miniapp-order-history'],
  ['miniapp-pricing-quote'],
  ['wallet-transactions'],
  ['active-devices'],
  ['twofa-status'],
  ['antiphishing-code'],
  ['partner-dashboard'],
  ['growth', 'invites'],
  ['growth', 'gifts'],
  ['growth', 'rewards'],
  ['growth', 'notifications'],
  ['growth', 'notifications', 'counters'],
] satisfies QueryKey[];

const MINIAPP_AUTH_PRIVATE_KEY_NAMES = new Set([
  'wallet',
  'wallet-transactions',
  'active-devices',
  'twofa-status',
  'antiphishing-code',
  'partner-dashboard',
]);

export function isMiniAppPrivateAuthQuery(queryKey: readonly unknown[]): boolean {
  const [root] = queryKey;

  return (
    typeof root === 'string'
    && (root.startsWith('miniapp-') || MINIAPP_AUTH_PRIVATE_KEY_NAMES.has(root))
  );
}

function invalidateKeys(queryClient: QueryClient, keys: readonly QueryKey[]) {
  return keys.map((queryKey) => queryClient.invalidateQueries({ queryKey }));
}

export async function invalidateMiniAppAccessState(queryClient: QueryClient): Promise<void> {
  await Promise.all([
    ...invalidateKeys(queryClient, MINIAPP_ACCESS_INVALIDATE_KEYS),
    queryClient.resetQueries({ queryKey: ['miniapp-config'], exact: true }),
  ]);
}

export async function invalidateCustomerSettlementState(
  queryClient: QueryClient,
  options: { includeMiniApp?: boolean } = {},
): Promise<void> {
  await Promise.all([
    ...invalidateKeys(queryClient, CUSTOMER_SETTLEMENT_INVALIDATE_KEYS),
    ...(options.includeMiniApp
      ? [
          invalidateMiniAppAccessState(queryClient),
          ...invalidateKeys(queryClient, MINIAPP_SETTLEMENT_INVALIDATE_KEYS),
        ]
      : []),
  ]);
}

export async function resetMiniAppPrivateAuthQueries(queryClient: QueryClient): Promise<void> {
  await queryClient.resetQueries({
    predicate: (query: { queryKey: readonly unknown[] }) => isMiniAppPrivateAuthQuery(query.queryKey),
  });
}
