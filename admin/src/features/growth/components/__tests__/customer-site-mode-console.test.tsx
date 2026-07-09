import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CustomerSiteModeConsole } from '../customer-site-mode-console';

const {
  mockExecuteCustomerSiteRuntimeAction,
  mockGetCustomerSiteRuntimeTimeline,
  mockGetCustomerSiteRuntime,
  mockUpdateCustomerSiteRuntime,
} = vi.hoisted(() => ({
  mockExecuteCustomerSiteRuntimeAction: vi.fn(),
  mockGetCustomerSiteRuntimeTimeline: vi.fn(),
  mockGetCustomerSiteRuntime: vi.fn(),
  mockUpdateCustomerSiteRuntime: vi.fn(),
}));

vi.mock('@/lib/api/growth', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/growth')>('@/lib/api/growth');
  return {
    ...actual,
    growthApi: {
      ...actual.growthApi,
      executeCustomerSiteRuntimeAction: (...args: unknown[]) => mockExecuteCustomerSiteRuntimeAction(...args),
      getCustomerSiteRuntimeTimeline: (...args: unknown[]) => mockGetCustomerSiteRuntimeTimeline(...args),
      getCustomerSiteRuntime: (...args: unknown[]) => mockGetCustomerSiteRuntime(...args),
      updateCustomerSiteRuntime: (...args: unknown[]) => mockUpdateCustomerSiteRuntime(...args),
    },
  };
});

function renderWithQueryClient(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  );
}

describe('CustomerSiteModeConsole', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetCustomerSiteRuntime.mockResolvedValue({
      data: {
        key: 'customer_site.runtime',
        site: {
          mode: 'cabinet_only',
          version: 6,
          cabinet_only: true,
          public_hosts: ['cyber-vpn.net'],
          cabinet_hosts: ['my.cyber-vpn.net'],
          cabinet_destination_path: '/dashboard',
          allowed_path_prefixes: ['/login', '/register'],
          cabinet_allowed_prefixes: ['/dashboard', '/subscriptions'],
          cabinet_marketing_route_action: 'redirect_public',
          public_marketing_destination_path: '/pricing',
          legal_path_prefixes: ['/privacy-policy', '/terms'],
          operational_path_prefixes: ['/status', '/.well-known'],
          preserve_query_keys: ['ref', 'code', 'utm_campaign'],
          registration_policy_independent: true,
        },
      },
    });
    mockUpdateCustomerSiteRuntime.mockResolvedValue({
      data: {
        key: 'customer_site.runtime',
        site: {
          mode: 'maintenance',
          version: 7,
          cabinet_only: false,
          public_hosts: ['cyber-vpn.net'],
          cabinet_hosts: ['my.cyber-vpn.net'],
          cabinet_destination_path: '/dashboard',
          allowed_path_prefixes: ['/login', '/register'],
          cabinet_allowed_prefixes: ['/dashboard', '/subscriptions'],
          cabinet_marketing_route_action: 'redirect_public',
          public_marketing_destination_path: '/pricing',
          legal_path_prefixes: ['/privacy-policy', '/terms'],
          operational_path_prefixes: ['/status', '/.well-known'],
          preserve_query_keys: ['ref', 'code', 'utm_campaign'],
          registration_policy_independent: true,
        },
      },
    });
    mockExecuteCustomerSiteRuntimeAction.mockResolvedValue({
      data: {
        key: 'customer_site.runtime',
        site: {
          mode: 'full_site',
          version: 7,
          cabinet_only: false,
          public_hosts: ['cyber-vpn.net'],
          cabinet_hosts: ['my.cyber-vpn.net'],
          cabinet_destination_path: '/dashboard',
          allowed_path_prefixes: ['/login', '/register'],
          cabinet_allowed_prefixes: ['/dashboard', '/subscriptions'],
          cabinet_marketing_route_action: 'redirect_public',
          public_marketing_destination_path: '/pricing',
          legal_path_prefixes: ['/privacy-policy', '/terms'],
          operational_path_prefixes: ['/status', '/.well-known'],
          preserve_query_keys: ['ref', 'code', 'utm_campaign'],
          registration_policy_independent: true,
        },
      },
    });
    mockGetCustomerSiteRuntimeTimeline.mockResolvedValue({
      data: [
        {
          id: '2bb06a93-9eb4-4465-94c8-6c9f5a779001',
          created_at: '2026-06-20T10:00:00Z',
          admin_id: '6e3349e7-f1ae-4118-aa2f-d5103dd20001',
          action: 'rollback_to_full_site',
          event_type: 'site_mode_action',
          resulting_mode: 'full_site',
          resulting_version: 7,
          change_reason: 'Marketing restored',
          entity_id: 'customer_site.runtime',
        },
      ],
    });
  });

  it('requires reason plus typed confirmation before updating the versioned runtime policy', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<CustomerSiteModeConsole />);

    expect((await screen.findAllByText('siteMode.modes.cabinet_only')).length).toBeGreaterThan(0);
    expect(screen.getByText('https://my.cyber-vpn.net/en/dashboard?ref=partner-001&code=PR-PRO100&utm_campaign=beta')).toBeInTheDocument();
    expect(screen.getAllByText('/dashboard, /subscriptions').length).toBeGreaterThan(0);
    expect(screen.getAllByText('siteMode.cabinetMarketingActions.redirect_public').length).toBeGreaterThan(0);
    expect(screen.getByText('/privacy-policy, /terms')).toBeInTheDocument();
    expect(mockGetCustomerSiteRuntime).toHaveBeenCalledTimes(1);
    expect(mockGetCustomerSiteRuntimeTimeline).toHaveBeenCalledWith({ limit: 8 });
    expect(await screen.findByText('Rollback To Full Site')).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('siteMode.fields.mode'), 'maintenance');
    fireEvent.change(screen.getByLabelText('siteMode.fields.reason'), {
      target: { value: 'Private beta freeze' },
    });
    const updateButton = screen.getByRole('button', { name: 'siteMode.updateAction' });
    expect(updateButton).toBeDisabled();
    fireEvent.change(screen.getByLabelText('siteMode.fields.confirmation'), {
      target: { value: 'maintenance' },
    });
    expect(updateButton).toBeEnabled();
    await user.click(updateButton);

    expect(mockUpdateCustomerSiteRuntime).toHaveBeenCalledWith({
      mode: 'maintenance',
      public_hosts: ['cyber-vpn.net'],
      cabinet_hosts: ['my.cyber-vpn.net'],
      cabinet_destination_path: '/dashboard',
      allowed_path_prefixes: ['/login', '/register'],
      cabinet_allowed_prefixes: ['/dashboard', '/subscriptions'],
      cabinet_marketing_route_action: 'redirect_public',
      public_marketing_destination_path: '/pricing',
      legal_path_prefixes: ['/privacy-policy', '/terms'],
      operational_path_prefixes: ['/status', '/.well-known'],
      preserve_query_keys: ['ref', 'code', 'utm_campaign'],
      expected_version: 6,
      change_reason: 'Private beta freeze',
    });
    expect(await screen.findByText('siteMode.feedback.updated')).toBeInTheDocument();
  });

  it('requires reason plus typed rollback confirmation before posting the authoritative version', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<CustomerSiteModeConsole />);

    expect((await screen.findAllByText('siteMode.modes.cabinet_only')).length).toBeGreaterThan(0);
    const rollback = screen.getByRole('button', { name: 'siteMode.rollbackAction' });
    expect(rollback).toBeDisabled();

    fireEvent.change(screen.getByLabelText('siteMode.fields.reason'), {
      target: { value: 'Marketing restored' },
    });
    expect(rollback).toBeDisabled();
    fireEvent.change(screen.getByLabelText('siteMode.fields.confirmation'), {
      target: { value: 'full_site' },
    });
    expect(rollback).toBeEnabled();
    await user.click(rollback);

    expect(mockExecuteCustomerSiteRuntimeAction).toHaveBeenCalledWith({
      action: 'rollback_to_full_site',
      expected_version: 6,
      change_reason: 'Marketing restored',
    });
  });
});
