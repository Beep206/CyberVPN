import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { createPartnerPortalScenarioState } from '@/features/partner-portal-state/lib/portal-state';

const apiMocks = vi.hoisted(() => ({
  listWorkspacePayoutHistory: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string, values?: Record<string, string>) => {
    if (!values) return key;
    return `${key}:${Object.entries(values).map(([name, value]) => `${name}=${value}`).join(',')}`;
  },
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({
    children,
    href,
    ...props
  }: {
    children: ReactNode;
    href: string;
    [key: string]: unknown;
  }) => <a href={href} {...props}>{children}</a>,
}));

vi.mock('@/features/auth/lib/passkey-fresh-auth', () => ({
  requestPasskeyFreshAuthGrant: vi.fn(),
}));

vi.mock('@/features/partner-portal-state/components/partner-route-guard', () => ({
  PartnerRouteGuard: ({
    children,
  }: {
    children: (access: 'read' | 'write' | 'admin' | 'none') => ReactNode;
  }) => <>{children('write')}</>,
}));

vi.mock('@/lib/api/partner-portal', () => ({
  partnerPortalApi: apiMocks,
}));

vi.mock('@/features/partner-portal-state/lib/use-partner-portal-runtime-state', () => ({
  usePartnerPortalRuntimeState: () => ({
    state: {
      ...createPartnerPortalScenarioState('active', 'creator_affiliate', 'workspace_owner', 'R4'),
      financeSnapshot: {
        availableEarnings: '€11.00',
        onHoldEarnings: '€2.00',
        reserves: '€4.00',
        nextPayoutForecast: '€7.00',
        currency: 'EUR',
      },
      financeCurrencySnapshots: [
        {
          availableEarnings: '€11.00',
          currency: 'EUR',
          eventCount: 1,
          lastEventAt: '2026-06-21T09:00:00Z',
          nextPayoutForecast: '€7.00',
          onHoldEarnings: '€2.00',
          paid: '€3.00',
          reserves: '€4.00',
          reversed: '€5.00',
          source: 'summary',
          total: '€25.00',
        },
        {
          availableEarnings: '$120.00',
          currency: 'USD',
          eventCount: 2,
          lastEventAt: '2026-06-21T09:10:00Z',
          nextPayoutForecast: '$70.00',
          onHoldEarnings: '$20.00',
          paid: '$30.00',
          reserves: '$40.00',
          reversed: '$50.00',
          source: 'summary',
          total: '$250.00',
        },
      ],
      financeStatements: [],
      payoutAccounts: [],
    },
    activeWorkspace: { id: 'workspace-1', display_name: 'Workspace One' },
    blockedReasons: [],
    queries: {
      payoutAccountsQuery: {
        data: [],
      },
    },
  }),
}));

import { FinanceOperationsPage } from './finance-operations-page';

function renderFinancePage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <FinanceOperationsPage />
    </QueryClientProvider>,
  );
}

describe('FinanceOperationsPage', () => {
  it('renders settlement finance amounts grouped by currency', async () => {
    apiMocks.listWorkspacePayoutHistory.mockResolvedValue({ data: [] });

    renderFinancePage();

    expect(await screen.findByText('snapshot.currencyBreakdown')).toBeInTheDocument();
    expect(screen.getByText('EUR')).toBeInTheDocument();
    expect(screen.getAllByText('€11.00').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('€25.00')).toBeInTheDocument();
    expect(screen.getByText('USD')).toBeInTheDocument();
    expect(screen.getByText('$120.00')).toBeInTheDocument();
    expect(screen.getByText('$250.00')).toBeInTheDocument();
    expect(screen.getAllByText('snapshot.source:value=summary')).toHaveLength(2);
  });
});
