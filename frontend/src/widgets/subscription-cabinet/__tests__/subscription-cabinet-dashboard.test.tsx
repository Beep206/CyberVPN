import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const {
  activateTrialMock,
  commitUpgradeMock,
  getAddonsMock,
  getEntitlementMock,
  getOrdersMock,
  getPlansMock,
  getServiceStateMock,
  getTrialMock,
  openMock,
  purchaseAddonsMock,
  quoteAddonsMock,
  quoteUpgradeMock,
} = vi.hoisted(() => ({
  activateTrialMock: vi.fn(),
  commitUpgradeMock: vi.fn(),
  getAddonsMock: vi.fn(),
  getEntitlementMock: vi.fn(),
  getOrdersMock: vi.fn(),
  getPlansMock: vi.fn(),
  getServiceStateMock: vi.fn(),
  getTrialMock: vi.fn(),
  openMock: vi.fn(),
  purchaseAddonsMock: vi.fn(),
  quoteAddonsMock: vi.fn(),
  quoteUpgradeMock: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations:
    () =>
    (key: string, values?: Record<string, string | number>) => {
      if (!values) {
        return key;
      }

      return `${key} ${Object.values(values).join(' ')}`;
    },
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({
    children,
    href,
    ...rest
  }: {
    children: ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock('@/app/[locale]/(dashboard)/subscriptions/components/CancelSubscriptionModal', () => ({
  CancelSubscriptionModal: () => null,
}));

vi.mock('@/app/[locale]/(dashboard)/subscriptions/components/PurchaseConfirmModal', () => ({
  PurchaseConfirmModal: ({ plan }: { plan: { display_name: string } | null }) =>
    plan ? <div data-testid="purchase-modal">{plan.display_name}</div> : null,
}));

vi.mock('@/lib/api', () => ({
  DEFAULT_SERVICE_STATE_REQUEST: {
    channel_type: 'shared_client',
    credential_subject_key: 'official-web-dashboard',
    credential_type: 'desktop_client',
    provider_name: 'remnawave',
  },
  addonsApi: {
    listCatalog: getAddonsMock,
  },
  commerceApi: {
    listOrders: getOrdersMock,
  },
  customerSubscriptionsApi: {
    commitUpgrade: commitUpgradeMock,
    getEntitlements: getEntitlementMock,
    getServiceState: getServiceStateMock,
    purchaseAddons: purchaseAddonsMock,
    quoteAddons: quoteAddonsMock,
    quoteUpgrade: quoteUpgradeMock,
  },
  entitlementsApi: {
    getCurrent: getEntitlementMock,
  },
  plansApi: {
    list: getPlansMock,
  },
  serviceAccessApi: {
    getCurrentServiceState: getServiceStateMock,
  },
  trialApi: {
    activate: activateTrialMock,
    getStatus: getTrialMock,
  },
}));

vi.mock('@/features/customer-subscriptions/customer-subscription-context', () => ({
  useCustomerSubscriptions: () => ({
    defaultSubscriptionKey: 'grant:test-grant',
    isError: false,
    isLoading: false,
    limitations: [],
    refetch: vi.fn(),
    selectedSubscription: {
      can_deliver_config: true,
      can_manage: true,
      display_name: 'Pro Plan',
      management_scope: 'subscription_vpn_identity',
      subscription_key: 'grant:test-grant',
    },
    selectedSubscriptionKey: 'grant:test-grant',
    setSelectedSubscriptionKey: vi.fn(),
    subscriptions: [],
  }),
}));

import { SubscriptionCabinetDashboard } from '../subscription-cabinet-dashboard';

const entitlement = {
  addons: [],
  display_name: 'Pro Plan',
  effective_entitlements: {
    connection_modes: ['standard', 'stealth'],
    device_limit: 5,
    display_traffic_label: 'Unlimited',
    support_sla: 'priority',
  },
  expires_at: '2026-05-24T00:00:00Z',
  invite_bundle: {},
  is_trial: false,
  period_days: 30,
  plan_code: 'pro',
  plan_uuid: 'plan-pro',
  status: 'active',
};

const plans = [
  {
    catalog_visibility: 'public',
    connection_modes: ['standard', 'stealth'],
    dedicated_ip: {
      eligible: true,
      included: 0,
    },
    devices_included: 5,
    display_name: 'Pro Plan',
    duration_days: 30,
    features: {},
    invite_bundle: {
      count: 0,
      expiry_days: 0,
      friend_days: 0,
    },
    is_active: true,
    name: 'PRO',
    plan_code: 'pro',
    price_rub: null,
    price_usd: 29,
    sale_channels: ['web'],
    server_pool: ['shared_plus'],
    sort_order: 10,
    support_sla: 'priority',
    traffic_limit_bytes: null,
    traffic_policy: {
      display_label: 'Unlimited',
      enforcement_profile: null,
      mode: 'fair_use',
    },
    uuid: 'plan-pro',
  },
  {
    catalog_visibility: 'public',
    connection_modes: ['standard', 'stealth', 'manual_config'],
    dedicated_ip: {
      eligible: true,
      included: 1,
    },
    devices_included: 10,
    display_name: 'Max Plan',
    duration_days: 90,
    features: {},
    invite_bundle: {
      count: 1,
      expiry_days: 30,
      friend_days: 7,
    },
    is_active: true,
    name: 'MAX',
    plan_code: 'max',
    price_rub: null,
    price_usd: 79,
    sale_channels: ['web'],
    server_pool: ['premium'],
    sort_order: 20,
    support_sla: 'vip',
    traffic_limit_bytes: null,
    traffic_policy: {
      display_label: 'Unlimited',
      enforcement_profile: null,
      mode: 'fair_use',
    },
    uuid: 'plan-max',
  },
];

const addon = {
  code: 'extra-device',
  delta_entitlements: {},
  display_name: 'Extra device',
  duration_mode: 'subscription_aligned',
  is_active: true,
  is_stackable: true,
  max_quantity_by_plan: {
    pro: 2,
  },
  price_rub: null,
  price_usd: 5,
  quantity_step: 1,
  requires_location: false,
  sale_channels: ['web'],
  uuid: 'addon-extra-device',
};

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

function mockSuccessfulResponses() {
  getEntitlementMock.mockResolvedValue({ data: entitlement });
  getServiceStateMock.mockResolvedValue({
    data: {
      access_delivery_channel: {
        channel_status: 'active',
        channel_type: 'shared_client',
        provider_name: 'remnawave',
      },
      provisioning_profile: {
        profile_key: 'default',
      },
      service_identity: {
        provider_name: 'remnawave',
      },
    },
  });
  getTrialMock.mockResolvedValue({
    data: {
      days_remaining: 0,
      is_eligible: false,
      is_trial_active: false,
      trial_end: null,
      trial_start: null,
    },
  });
  getPlansMock.mockResolvedValue({ data: plans });
  getAddonsMock.mockResolvedValue({ data: [addon] });
  getOrdersMock.mockResolvedValue({
    data: [
      {
        created_at: '2026-04-24T00:00:00Z',
        currency_code: 'USD',
        displayed_price: 29,
        id: 'order-paid-1',
        items: [{ display_name: 'Pro Plan' }],
        order_status: 'committed',
        settlement_status: 'paid',
        subscription_plan_id: 'plan-pro',
      },
    ],
  });
  quoteUpgradeMock.mockResolvedValue({
    data: {
      addon_amount: 0,
      base_price: 79,
      discount_amount: 0,
      displayed_price: 79,
      entitlements_snapshot: {},
      gateway_amount: 50,
      is_zero_gateway: false,
      partner_markup: 0,
      wallet_amount: 0,
    },
  });
  commitUpgradeMock.mockResolvedValue({
    data: {
      addon_amount: 0,
      base_price: 79,
      discount_amount: 0,
      displayed_price: 79,
      entitlements_snapshot: {},
      gateway_amount: 50,
      invoice: {
        amount: 50,
        currency: 'USD',
        expires_at: '2026-04-24T01:00:00Z',
        invoice_id: 'invoice-1',
        payment_url: 'https://pay.example/invoice-1',
        status: 'pending',
      },
      is_zero_gateway: false,
      partner_markup: 0,
      payment_id: 'payment-1',
      status: 'pending',
      wallet_amount: 0,
    },
  });
  quoteAddonsMock.mockResolvedValue({
    data: {
      addon_amount: 5,
      base_price: 0,
      discount_amount: 0,
      displayed_price: 5,
      entitlements_snapshot: {},
      gateway_amount: 5,
      is_zero_gateway: false,
      partner_markup: 0,
      wallet_amount: 0,
    },
  });
  purchaseAddonsMock.mockResolvedValue({
    data: {
      addon_amount: 5,
      base_price: 0,
      discount_amount: 0,
      displayed_price: 5,
      entitlements_snapshot: {},
      gateway_amount: 5,
      invoice: null,
      is_zero_gateway: false,
      partner_markup: 0,
      payment_id: null,
      status: 'completed',
      wallet_amount: 0,
    },
  });
  activateTrialMock.mockResolvedValue({ data: { ok: true } });
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal('open', openMock);
  mockSuccessfulResponses();
});

describe('SubscriptionCabinetDashboard', () => {
  it('renders entitlement, plans, add-ons, history, and customer-safe links', async () => {
    renderWithQueryClient(<SubscriptionCabinetDashboard />);

    expect((await screen.findAllByText('Pro Plan')).length).toBeGreaterThan(0);
    expect(screen.getByText('Max Plan')).toBeInTheDocument();
    expect(screen.getByText('Extra device')).toBeInTheDocument();
    expect(screen.getByText('remnawave')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /actions\.getConfig/i })).toHaveAttribute(
      'href',
      '/servers',
    );
    expect(screen.getByRole('link', { name: /actions\.wallet/i })).toHaveAttribute(
      'href',
      '/wallet',
    );
    expect(getPlansMock).toHaveBeenCalledWith({ channel: 'web' });
    expect(getAddonsMock).toHaveBeenCalledWith({ channel: 'web' });
  });

  it('quotes and commits a plan upgrade through backend subscription endpoints', async () => {
    renderWithQueryClient(<SubscriptionCabinetDashboard />);

    const maxPlanCard = (await screen.findByText('Max Plan')).closest('article');
    expect(maxPlanCard).not.toBeNull();

    fireEvent.click(within(maxPlanCard as HTMLElement).getByRole('button', { name: /planActions\.quote/i }));

    await waitFor(() => {
      expect(quoteUpgradeMock).toHaveBeenCalledWith('grant:test-grant', {
        channel: 'web',
        currency: 'USD',
        promo_code: null,
        target_plan_id: 'plan-max',
        use_wallet: 0,
      });
    });

    fireEvent.click(within(maxPlanCard as HTMLElement).getByRole('button', { name: /planActions\.commitCta/i }));

    await waitFor(() => {
      expect(commitUpgradeMock).toHaveBeenCalled();
      expect(commitUpgradeMock).toHaveBeenCalledWith('grant:test-grant', {
        channel: 'web',
        currency: 'USD',
        promo_code: null,
        target_plan_id: 'plan-max',
        use_wallet: 0,
      });
      expect(openMock).toHaveBeenCalledWith(
        'https://pay.example/invoice-1',
        '_blank',
        'noopener,noreferrer',
      );
    });
  });

  it('activates eligible trial and refreshes backend-backed state', async () => {
    getEntitlementMock.mockResolvedValueOnce({
      data: {
        ...entitlement,
        display_name: null,
        plan_code: null,
        plan_uuid: null,
        status: 'inactive',
      },
    });
    getTrialMock.mockResolvedValueOnce({
      data: {
        days_remaining: 0,
        is_eligible: true,
        is_trial_active: false,
        trial_end: null,
        trial_start: null,
      },
    });

    renderWithQueryClient(<SubscriptionCabinetDashboard />);

    fireEvent.click(await screen.findByRole('button', { name: /trial\.activate/i }));

    await waitFor(() => {
      expect(activateTrialMock).toHaveBeenCalledTimes(1);
    });
  });

  it('shows degraded sync while keeping subscription data usable when a dependency fails', async () => {
    getOrdersMock.mockRejectedValueOnce(new Error('orders unavailable'));

    renderWithQueryClient(<SubscriptionCabinetDashboard />);

    expect((await screen.findAllByText('Pro Plan')).length).toBeGreaterThan(0);
    expect(screen.getByText('Extra device')).toBeInTheDocument();
    expect(await screen.findByText('sync.degraded')).toBeInTheDocument();
  });

  it('quotes and purchases an add-on through backend subscription endpoints', async () => {
    renderWithQueryClient(<SubscriptionCabinetDashboard />);

    await screen.findByText('Extra device');
    fireEvent.click(screen.getByRole('button', { name: /addons\.quote/i }));

    await waitFor(() => {
      expect(quoteAddonsMock).toHaveBeenCalledWith('grant:test-grant', {
        addons: [
          {
            code: 'extra-device',
            qty: 1,
          },
        ],
        channel: 'web',
        currency: 'USD',
        promo_code: null,
        use_wallet: 0,
      });
    });
    expect(await screen.findByText('addons.quoteReady $5')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /addons\.purchaseCta/i }));

    await waitFor(() => {
      expect(purchaseAddonsMock).toHaveBeenCalledWith('grant:test-grant', {
        addons: [
          {
            code: 'extra-device',
            qty: 1,
          },
        ],
        channel: 'web',
        currency: 'USD',
        promo_code: null,
        use_wallet: 0,
      });
    });
    expect(await screen.findByText('addons.purchase.completed')).toBeInTheDocument();
    expect(openMock).not.toHaveBeenCalled();
  });

  it('shows add-on quote failure feedback and keeps purchase disabled', async () => {
    quoteAddonsMock.mockRejectedValueOnce(new Error('quote unavailable'));

    renderWithQueryClient(<SubscriptionCabinetDashboard />);

    await screen.findByText('Extra device');
    fireEvent.click(screen.getByRole('button', { name: /addons\.quote/i }));

    expect(await screen.findByText('addons.quoteError')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /addons\.purchaseCta/i })).toBeDisabled();
    expect(purchaseAddonsMock).not.toHaveBeenCalled();
  });

  it('shows upgrade commit failure feedback without opening an invoice', async () => {
    commitUpgradeMock.mockRejectedValueOnce(new Error('commit failed'));

    renderWithQueryClient(<SubscriptionCabinetDashboard />);

    const maxPlanCard = (await screen.findByText('Max Plan')).closest('article');
    expect(maxPlanCard).not.toBeNull();

    fireEvent.click(within(maxPlanCard as HTMLElement).getByRole('button', { name: /planActions\.quote/i }));
    await waitFor(() => {
      expect(quoteUpgradeMock).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(within(maxPlanCard as HTMLElement).getByRole('button', { name: /planActions\.commitCta/i }));

    expect(await screen.findByText('planActions.commitError')).toBeInTheDocument();
    expect(openMock).not.toHaveBeenCalled();
  });

  it('routes inactive customers to purchase flow and disables add-on purchases', async () => {
    getEntitlementMock.mockResolvedValueOnce({
      data: {
        ...entitlement,
        addons: [],
        display_name: null,
        effective_entitlements: {},
        expires_at: null,
        plan_code: null,
        plan_uuid: null,
        status: 'inactive',
      },
    });

    renderWithQueryClient(<SubscriptionCabinetDashboard />);

    const maxPlanCard = (await screen.findByText('Max Plan')).closest('article');
    expect(maxPlanCard).not.toBeNull();

    fireEvent.click(within(maxPlanCard as HTMLElement).getByRole('button', { name: /planActions\.purchase/i }));

    expect(await screen.findByTestId('purchase-modal')).toHaveTextContent('Max Plan');
    expect(screen.getByRole('button', { name: /addons\.quote/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /addons\.purchaseCta/i })).toBeDisabled();
  });

  it('shows trial activation failure feedback without marking trial as successful', async () => {
    getEntitlementMock.mockResolvedValueOnce({
      data: {
        ...entitlement,
        display_name: null,
        plan_code: null,
        plan_uuid: null,
        status: 'inactive',
      },
    });
    getTrialMock.mockResolvedValueOnce({
      data: {
        days_remaining: 0,
        is_eligible: true,
        is_trial_active: false,
        trial_end: null,
        trial_start: null,
      },
    });
    activateTrialMock.mockRejectedValueOnce(new Error('trial unavailable'));

    renderWithQueryClient(<SubscriptionCabinetDashboard />);

    fireEvent.click(await screen.findByRole('button', { name: /trial\.activate/i }));

    expect(await screen.findByText('trial.error')).toBeInTheDocument();
    expect(screen.queryByText('trial.success')).not.toBeInTheDocument();
  });
});
