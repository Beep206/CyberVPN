import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CustomerSubscriptionSummary } from '@/lib/api/customer-subscriptions';

const { contextMock } = vi.hoisted(() => ({
  contextMock: {
    defaultSubscriptionKey: 'grant:pro',
    isError: false,
    isLoading: false,
    limitations: [] as string[],
    refetch: vi.fn(),
    selectedSubscriptionKey: 'grant:pro',
    setSelectedSubscriptionKey: vi.fn(),
    subscriptions: [] as CustomerSubscriptionSummary[],
    selectedSubscription: null as CustomerSubscriptionSummary | null,
  },
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations:
    () =>
    (key: string) => {
      const messages: Record<string, string> = {
        'switcher.accountScoped':
          'VPN config is account-scoped for now; the selected subscription controls the commercial context.',
        'switcher.empty': 'No subscriptions found yet',
        'switcher.label': 'Subscription selector',
        'switcher.loading': 'Loading subscriptions',
        'switcher.refresh': 'Refresh',
        'switcher.selected': 'Selected',
        'switcher.status': 'Status',
      };

      return messages[key] ?? key;
    },
}));

vi.mock('../customer-subscription-context', () => ({
  useCustomerSubscriptions: () => contextMock,
}));

import { CustomerSubscriptionSwitcher } from '../customer-subscription-switcher';

function subscription(
  overrides: Partial<CustomerSubscriptionSummary> = {},
): CustomerSubscriptionSummary {
  return {
    addons: [],
    can_deliver_config: true,
    can_manage: true,
    created_at: '2026-04-18T10:00:00Z',
    display_name: 'Pro Plan',
    effective_entitlements: {
      display_traffic_label: 'Unlimited',
    },
    entitlement_grant_id: 'grant-1',
    expires_at: '2026-05-18T10:00:00Z',
    invite_bundle: {},
    is_trial: false,
    kind: 'entitlement_grant',
    management_scope: 'subscription_vpn_identity',
    plan_code: 'pro',
    plan_uuid: 'plan-pro',
    provider_name: 'remnawave',
    service_identity_id: 'service-1',
    source_order_id: 'order-1',
    source_type: 'order',
    status: 'active',
    subscription_key: 'grant:pro',
    ...overrides,
  };
}

describe('CustomerSubscriptionSwitcher', () => {
  beforeEach(() => {
    contextMock.defaultSubscriptionKey = 'grant:pro';
    contextMock.isError = false;
    contextMock.isLoading = false;
    contextMock.limitations = [];
    contextMock.refetch.mockClear();
    contextMock.selectedSubscription = subscription();
    contextMock.selectedSubscriptionKey = 'grant:pro';
    contextMock.setSelectedSubscriptionKey.mockClear();
    contextMock.subscriptions = [
      contextMock.selectedSubscription,
      subscription({
        display_name: 'Trial Plan',
        kind: 'trial',
        subscription_key: 'trial:trial-1',
      }),
    ];
  });

  it('renders localized shell labels and changes selected subscription', () => {
    render(<CustomerSubscriptionSwitcher />);

    const selector = screen.getByRole('combobox', { name: 'Subscription selector' });

    expect(selector).toBeInTheDocument();
    expect(selector).toHaveValue('grant:pro');
    expect(
      screen.getByRole('option', {
        name: 'Trial Plan / Unlimited / 2026-05-18',
      }),
    ).toHaveValue('trial:trial-1');
    expect(screen.getByText('Selected')).toBeInTheDocument();
    expect(
      screen.getAllByText(/Pro Plan \/ Unlimited \/ 2026-05-18/i).length,
    ).toBeGreaterThan(0);

    fireEvent.change(selector, {
      target: { value: 'trial:trial-1' },
    });

    expect(contextMock.setSelectedSubscriptionKey).toHaveBeenCalledWith('trial:trial-1');
  });

  it('keeps subscription navigation shell mounted when entitlements are degraded', () => {
    contextMock.selectedSubscription = subscription({
      effective_entitlements:
        undefined as unknown as CustomerSubscriptionSummary['effective_entitlements'],
    });
    contextMock.subscriptions = [contextMock.selectedSubscription];

    render(<CustomerSubscriptionSwitcher />);

    expect(
      screen.getByRole('combobox', { name: 'Subscription selector' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('option', {
        name: 'Pro Plan / 2026-05-18',
      }),
    ).toHaveValue('grant:pro');
    expect(
      screen.getAllByText(/Pro Plan \/ 2026-05-18/i).length,
    ).toBeGreaterThan(0);
  });

  it('explains account-scoped subscriptions while keeping status visible', () => {
    contextMock.limitations = ['account_scoped_config'];
    contextMock.selectedSubscription = subscription({
      can_manage: false,
      management_scope: 'account_vpn_identity',
    });
    contextMock.subscriptions = [contextMock.selectedSubscription];

    render(<CustomerSubscriptionSwitcher />);

    expect(
      screen.getByText(
        'VPN config is account-scoped for now; the selected subscription controls the commercial context.',
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/Status: active/i)).toBeVisible();
  });

  it('offers a localized refresh action when the list is empty', () => {
    contextMock.isError = true;
    contextMock.selectedSubscription = null;
    contextMock.subscriptions = [];

    render(<CustomerSubscriptionSwitcher />);

    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));
    expect(contextMock.refetch).toHaveBeenCalledTimes(1);
  });
});
