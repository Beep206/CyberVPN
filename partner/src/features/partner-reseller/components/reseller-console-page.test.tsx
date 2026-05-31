import type { ReactNode } from 'react';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => {
  const mutate = vi.fn();
  const invalidateQueries = vi.fn();

  return {
    invalidateQueries,
    mutate,
    runtimeState: vi.fn(),
    useMutation: vi.fn(() => ({
      isPending: false,
      mutate,
    })),
    useQuery: vi.fn(({ queryKey }: { queryKey: readonly unknown[] }) => {
      if (queryKey[1] === 'reseller-voucher-plans') {
        return {
          data: [
            {
              display_name: 'Starter',
              duration_days: 30,
              name: 'starter',
              plan_code: 'starter',
              price_usd: '9.99',
              uuid: 'plan_001',
            },
          ],
          error: null,
          isLoading: false,
        };
      }

      return {
        data: null,
        error: null,
        isLoading: false,
      };
    }),
    useQueryClient: vi.fn(() => ({ invalidateQueries })),
    useTranslations: vi.fn(
      (namespace?: string) =>
        (key: string) =>
          `${namespace ?? 'default'}:${key}`,
    ),
  };
});

vi.mock('next-intl', () => ({
  useTranslations: mocks.useTranslations,
}));

vi.mock('@tanstack/react-query', () => ({
  useMutation: mocks.useMutation,
  useQuery: mocks.useQuery,
  useQueryClient: mocks.useQueryClient,
}));

vi.mock('@/features/partner-portal-state/components/partner-route-guard', () => ({
  PartnerRouteGuard: ({ children }: { children: (access: 'write') => ReactNode }) => (
    <>{children('write')}</>
  ),
}));

vi.mock('@/features/partner-portal-state/lib/use-partner-portal-runtime-state', () => ({
  usePartnerPortalRuntimeState: () => mocks.runtimeState(),
}));

vi.mock('@/features/partner-operations/lib/advanced-operational-capabilities', () => ({
  getPartnerResellerCapabilities: () => [],
  getPartnerResellerSurfaceMode: () => 'operational',
}));

import { ResellerConsolePage } from './reseller-console-page';

describe('ResellerConsolePage', () => {
  beforeEach(() => {
    mocks.invalidateQueries.mockClear();
    mocks.mutate.mockClear();
    mocks.runtimeState.mockReset();
    mocks.useMutation.mockClear();
    mocks.useQuery.mockClear();
    mocks.useQueryClient.mockClear();
    mocks.useTranslations.mockClear();

    mocks.runtimeState.mockReturnValue({
      activeWorkspace: {
        id: 'workspace_001',
      },
      state: {
        resellerSnapshot: {
          customerScope: 'Workspace-scoped customer view',
          pricebookLabel: 'Standard reseller pricebook',
          supportOwnership: 'Partner-assisted',
          technicalHealth: 'Healthy',
        },
        resellerStorefronts: [],
        resellerVoucherBatches: [],
        workspaceStatus: 'active',
      },
    });
  });

  it('renders accessible voucher request labels instead of relying on placeholders', () => {
    render(<ResellerConsolePage />);

    expect(
      screen.getByLabelText('Partner.reseller:voucherRequest.planLabel'),
    ).toHaveValue('');
    expect(
      screen.getByLabelText('Partner.reseller:voucherRequest.countLabel'),
    ).toHaveValue('10');
    expect(
      screen.getByLabelText('Partner.reseller:voucherRequest.recipientHintLabel'),
    ).toHaveValue('');
    expect(
      screen.getByLabelText('Partner.reseller:voucherRequest.messageLabel'),
    ).toHaveValue('');
  });
});
