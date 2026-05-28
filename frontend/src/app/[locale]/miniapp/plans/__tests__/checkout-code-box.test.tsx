import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MiniAppPlansPage from '../page';

const apiMocks = vi.hoisted(() => ({
  codesApi: {
    resolve: vi.fn(),
  },
  invitesApi: {
    redeem: vi.fn(),
  },
  miniappApi: {
    getBootstrap: vi.fn(),
    getOffers: vi.fn(),
    quoteCheckout: vi.fn(),
    commitCheckout: vi.fn(),
    activateTrial: vi.fn(),
    getPayment: vi.fn(),
  },
}));

const telegramMocks = vi.hoisted(() => ({
  haptic: vi.fn(),
  hapticNotification: vi.fn(),
  webApp: {
    showAlert: vi.fn(),
    openInvoice: vi.fn(),
    openTelegramLink: vi.fn(),
    openLink: vi.fn(),
  },
}));

const runtimeAnalyticsMocks = vi.hoisted(() => ({
  emitMiniAppRuntimeEvent: vi.fn().mockResolvedValue(undefined),
}));

const clientCapabilitiesMock = vi.hoisted(() => ({
  data: {
    auth: {
      email_password: true,
      magic_link: true,
      telegram: true,
    },
    payments: {
      web_checkout: false,
      telegram_stars: true,
      cryptobot: true,
      manual_invoice: false,
      autorenewal: false,
    },
    growth: {
      invites: true,
      referral: true,
      promo_codes: true,
      gift_codes: true,
      checkout_code_discounts: false,
      growth_hub: true,
    },
    subscriptions: {
      multi_subscription: true,
      selected_subscription_required: true,
      addons: true,
      upgrade: true,
      trial: true,
      paid_provisioning: true,
    },
    partner: {
      portal: false,
      applications: false,
      codes: false,
      attribution: false,
      storefronts: false,
      reporting: false,
      settlement_sandbox: false,
      webhooks: false,
      payouts: false,
      event_backbone: false,
    },
  },
  isError: false,
}));

vi.mock('@/lib/api', () => apiMocks);

vi.mock('../../hooks/useTelegramWebApp', () => ({
  useTelegramWebApp: () => ({
    ...telegramMocks,
    colorScheme: 'dark',
  }),
}));

vi.mock('@/features/miniapp-runtime/lib/runtime-analytics', () => runtimeAnalyticsMocks);

vi.mock('@/features/client-capabilities/useClientCapabilities', () => ({
  areCheckoutCodeDiscountsEnabled: (capabilities: typeof clientCapabilitiesMock.data | undefined) =>
    capabilities?.growth.checkout_code_discounts === true,
  areSubscriptionAddonsEnabled: (capabilities: typeof clientCapabilitiesMock.data | undefined) =>
    capabilities?.subscriptions.addons === true,
  isGenericCheckoutRailEnabled: (capabilities: typeof clientCapabilitiesMock.data | undefined) =>
    capabilities?.payments.web_checkout === true || capabilities?.payments.cryptobot === true,
  isMiniAppCheckoutRailEnabled: (capabilities: typeof clientCapabilitiesMock.data | undefined) =>
    capabilities?.payments.web_checkout === true ||
    capabilities?.payments.cryptobot === true ||
    capabilities?.payments.telegram_stars === true,
  isTelegramStarsRailEnabled: (capabilities: typeof clientCapabilitiesMock.data | undefined) =>
    capabilities?.payments.telegram_stars === true,
  useClientCapabilities: () => clientCapabilitiesMock,
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-US',
  useTranslations: () => (key: string, values?: Record<string, string | number>) => {
    const dictionary: Record<string, string> = {
      availablePlans: 'Available plans',
      catalogHint: 'Catalog hint',
      'periods.annual': '365 days',
      periodInviteBonus: '{count} invites · {days} friend days',
      addonsTitle: 'Add-ons',
      addonsDescription: 'Add-ons description',
      addonUnavailable: 'Unavailable',
      extraDeviceLimit: 'Limit {count}',
      dedicatedIpLocationHint: 'Location hint',
      havePromoCode: 'Have a Checkout Code?',
      promoCodePlaceholder: 'SAVE20',
      apply: 'Apply code',
      checkoutCodeEmpty: 'Enter a checkout code first.',
      checkoutCodeAccepted: 'Checkout code accepted: {code}',
      checkoutCodeAcceptedReferral: 'Referral friend discount accepted for this checkout.',
      haveInviteCode: 'Have an Invite Code?',
      inviteCodePlaceholder: 'INVITE123',
      redeem: 'Redeem',
      quoteTitle: 'Quote & entitlements',
      quoteSubtitle: 'Quote subtitle',
      billingCurrencyNotice: 'Charged in {currency}',
      localEstimate: 'Approx. {price} display only',
      quoteError: 'Unable to calculate a quote with the current selections.',
      selectPlanToQuote: 'Select a plan to quote first.',
      processing: 'Processing',
      'flow.checkout': 'Checkout',
      'flow.none': 'No flow',
      serviceMaintenanceTitle: 'Service notice',
      runtimeTemporarilyUnavailable: 'Mini App is temporarily unavailable.',
      trialTemporarilyUnavailable: 'Trial activation is temporarily unavailable.',
      checkoutTemporarilyUnavailable: 'Checkout is temporarily unavailable.',
      'quote.basePrice': 'Base plan',
      'quote.addonAmount': 'Add-ons',
      'quote.discount': 'Discount',
      'quote.walletAmount': 'Wallet',
      'quote.gatewayAmount': 'Gateway',
      'quote.total': 'Total',
      'quote.entitlements': 'Entitlements',
      'quote.devices': 'Devices',
      'quote.traffic': 'Traffic',
      'quote.dedicatedIp': 'Dedicated IP',
      'quote.modes': 'Modes',
      'quote.serverPool': 'Server pool',
      'quote.none': 'None',
      'actions.openPayment': 'Open payment',
    };
    const template = dictionary[key] ?? key;
    if (!values) {
      return template;
    }
    return Object.entries(values).reduce(
      (result, [name, value]) => result.replaceAll(`{${name}}`, String(value)),
      template,
    );
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

function createQuoteResponse(overrides: Record<string, unknown> = {}) {
  return {
    base_price: 79,
    addon_amount: 0,
    displayed_price: 79,
    discount_amount: 0,
    wallet_amount: 0,
    gateway_amount: 79,
    partner_markup: 0,
    is_zero_gateway: false,
    plan_id: 'plan-plus-365',
    promo_code_id: null,
    partner_code_id: null,
    code_input: null,
    code_resolution: null,
    discounts: [],
    addons: [],
    entitlements_snapshot: {
      status: 'active',
      plan_uuid: 'plan-plus-365',
      plan_code: 'plus',
      display_name: 'Plus 365',
      period_days: 365,
      expires_at: null,
      effective_entitlements: {
        device_limit: 5,
        display_traffic_label: 'Unlimited',
        connection_modes: ['standard', 'stealth'],
        server_pool: ['shared_plus'],
        support_sla: 'standard',
        dedicated_ip_count: 0,
      },
      invite_bundle: { count: 2, friend_days: 14, expiry_days: 60 },
      is_trial: false,
      addons: [],
    },
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  clientCapabilitiesMock.isError = false;
  clientCapabilitiesMock.data.payments.telegram_stars = true;
  clientCapabilitiesMock.data.payments.cryptobot = true;
  clientCapabilitiesMock.data.payments.web_checkout = false;
  clientCapabilitiesMock.data.growth.checkout_code_discounts = false;
  clientCapabilitiesMock.data.subscriptions.addons = true;

  apiMocks.miniappApi.getOffers.mockResolvedValue({
    data: {
      plans: [
        {
          uuid: 'plan-plus-365',
          name: 'plus_365',
          plan_code: 'plus',
          display_name: 'Plus 365',
          catalog_visibility: 'public',
          features: { telegram_stars_amount: 500 },
          devices_included: 5,
          connection_modes: ['standard', 'stealth'],
          server_pool: ['shared_plus'],
          support_sla: 'standard',
          dedicated_ip: { included: 0, eligible: true },
          duration_days: 365,
          traffic_limit_bytes: null,
          traffic_policy: { mode: 'fair_use', display_label: 'Unlimited' },
          sale_channels: ['miniapp'],
          trial_eligible: false,
          price_usd: 79,
          price_rub: null,
          sort_order: 2,
          is_active: true,
          invite_bundle: { count: 2, friend_days: 14, expiry_days: 60 },
        },
      ],
      addons: [],
      trial: {
        is_trial_active: false,
        is_eligible: false,
        trial_end: null,
        days_remaining: 0,
      },
      currentEntitlements: {
        status: 'none',
        plan_uuid: null,
        plan_code: null,
        display_name: null,
        period_days: null,
        expires_at: null,
        effective_entitlements: {},
        invite_bundle: {},
        is_trial: false,
        addons: [],
      },
      freshness: {
        generatedAt: '2026-04-22T12:00:00Z',
      },
    },
  });
  apiMocks.miniappApi.getBootstrap.mockResolvedValue({
    data: {
      rollout: {
        enabled: true,
        mode: 'live',
        trialEnabled: true,
        checkoutEnabled: true,
        configEnabled: true,
        accessGranted: true,
        isCanaryUser: false,
        gateReasonCode: null,
        maintenanceMessage: null,
      },
    },
  });
  apiMocks.miniappApi.quoteCheckout.mockResolvedValue({
    data: createQuoteResponse(),
  });
  apiMocks.miniappApi.commitCheckout.mockResolvedValue({
    data: {
      ...createQuoteResponse(),
      status: 'pending',
      payment_id: 'payment-stars-1',
      invoice: {
        invoice_id: 'payment-stars-1',
        payment_url: 'https://t.me/$stars_invoice',
        amount: 500,
        currency: 'XTR',
        status: 'pending',
        expires_at: '2026-04-21T10:00:00Z',
      },
    },
  });
  apiMocks.miniappApi.getPayment.mockResolvedValue({
    data: {
      payment_id: 'payment-stars-1',
      status: 'completed',
      provider: 'telegram_stars',
      external_id: 'charge-1',
      amount: 500,
      currency: 'XTR',
      created_at: '2026-04-21T09:50:00Z',
      updated_at: '2026-04-21T09:51:00Z',
    },
  });
  apiMocks.miniappApi.activateTrial.mockResolvedValue({
    data: {
      activated: true,
      trial_end: '2026-04-29T00:00:00Z',
      message: 'Trial activated successfully.',
    },
  });
  apiMocks.invitesApi.redeem.mockResolvedValue({
    data: {
      free_days: 14,
    },
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('MiniAppPlansPage checkout code box', () => {
  it('hides checkout code entry while S1 growth flows are disabled', async () => {
    render(<MiniAppPlansPage />, { wrapper: createWrapper() });

    await screen.findByText('Available plans');

    expect(screen.queryByPlaceholderText('SAVE20')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Apply code' })).not.toBeInTheDocument();
    expect(apiMocks.codesApi.resolve).not.toHaveBeenCalled();
  });

  it('does not send checkout code fields in S1 quote requests', async () => {
    render(<MiniAppPlansPage />, { wrapper: createWrapper() });

    await screen.findByText('Available plans');

    await waitFor(() => {
      expect(apiMocks.miniappApi.quoteCheckout).toHaveBeenCalledWith(
        expect.objectContaining({
          flow: 'checkout',
          plan_id: 'plan-plus-365',
          code_input: undefined,
          promo_code: undefined,
          currency: 'USD',
        }),
      );
    });
  });

  it('uses telegram stars checkout and polls for payment completion inside mini app', async () => {
    const user = userEvent.setup();
    telegramMocks.webApp.openInvoice.mockImplementation(
      (_url: string, callback?: (status: 'paid' | 'cancelled' | 'failed' | 'pending') => void) => {
        callback?.('paid');
      },
    );

    render(<MiniAppPlansPage />, { wrapper: createWrapper() });

    await screen.findByText('Available plans');
    const openPaymentButton = await screen.findByRole('button', { name: 'Open payment' });

    await waitFor(() => {
      expect(apiMocks.miniappApi.quoteCheckout).toHaveBeenCalledWith(
        expect.objectContaining({
          flow: 'checkout',
          plan_id: 'plan-plus-365',
        }),
      );
      expect(openPaymentButton).toBeEnabled();
    });

    await user.click(openPaymentButton);

    await waitFor(() => {
      expect(apiMocks.miniappApi.commitCheckout).toHaveBeenCalledWith(
        expect.objectContaining({
          flow: 'checkout',
          plan_id: 'plan-plus-365',
          addons: [],
          currency: 'XTR',
        }),
      );
    });

    await waitFor(() => {
      expect(telegramMocks.webApp.openInvoice).toHaveBeenCalledWith(
        'https://t.me/$stars_invoice',
        expect.any(Function),
      );
      expect(apiMocks.miniappApi.getPayment).toHaveBeenCalledWith('payment-stars-1');
      expect(telegramMocks.webApp.showAlert).toHaveBeenCalledWith('paymentSuccess');
    });

    expect(runtimeAnalyticsMocks.emitMiniAppRuntimeEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        event: 'miniapp_checkout_completed',
        page: 'plans',
        paymentRail: 'telegram_stars_xtr',
      }),
    );
    expect(runtimeAnalyticsMocks.emitMiniAppRuntimeEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        event: 'miniapp_payment_status_resolved',
        page: 'plans',
        paymentRail: 'telegram_stars_xtr',
        paymentStatus: 'completed',
      }),
    );
  });

  it('disables checkout actions when rollout gate pauses checkout', async () => {
    apiMocks.miniappApi.getBootstrap.mockResolvedValue({
      data: {
        rollout: {
          enabled: true,
          mode: 'rollback',
          trialEnabled: true,
          checkoutEnabled: false,
          configEnabled: true,
          accessGranted: true,
          isCanaryUser: false,
          gateReasonCode: null,
          maintenanceMessage: 'Checkout paused by operator',
        },
      },
    });
    render(<MiniAppPlansPage />, { wrapper: createWrapper() });

    const openPaymentButton = await screen.findByRole('button', { name: 'Open payment' });
    expect(openPaymentButton).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Apply code' })).not.toBeInTheDocument();

    expect(apiMocks.miniappApi.quoteCheckout).not.toHaveBeenCalled();
    expect(apiMocks.miniappApi.commitCheckout).not.toHaveBeenCalled();
  });
});
