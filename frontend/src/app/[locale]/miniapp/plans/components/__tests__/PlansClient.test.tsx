import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import MiniAppPlansPage from '../../page';
import {
  cleanupTelegramWebAppMock,
  setupTelegramWebAppMock,
} from '@/test/mocks/telegram-webapp';

const apiMocks = vi.hoisted(() => ({
  codesApi: {
    resolve: vi.fn(),
  },
  invitesApi: {
    redeem: vi.fn(),
  },
  miniappApi: {
    activateTrial: vi.fn(),
    commitCheckout: vi.fn(),
    getBootstrap: vi.fn(),
    getOffers: vi.fn(),
    getPayment: vi.fn(),
    quoteCheckout: vi.fn(),
  },
}));

const runtimeAnalyticsMocks = vi.hoisted(() => ({
  emitMiniAppRuntimeEvent: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('@/lib/api', () => apiMocks);

vi.mock('@/features/miniapp-runtime/lib/runtime-analytics', () => runtimeAnalyticsMocks);

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => (key: string, values?: Record<string, string | number>) => {
    const labels: Record<string, string> = {
      availablePlans: 'Available plans',
      catalogHint: 'Catalog hint',
      'periods.annual': 'Annual',
      'periods.monthly': 'Monthly',
      addonsTitle: 'Add-ons',
      addonsDescription: 'Add-ons description',
      addonUnavailable: 'Unavailable',
      havePromoCode: 'Have promo code',
      promoCodePlaceholder: 'Promo code',
      apply: 'Apply',
      checkoutCodeAccepted: 'Code accepted {code}',
      checkoutCodeAcceptedReferral: 'Referral accepted',
      haveInviteCode: 'Have invite code',
      inviteCodePlaceholder: 'Invite code',
      redeem: 'Redeem',
      quoteTitle: 'Quote',
      quoteSubtitle: 'Quote subtitle',
      selectPlanToQuote: 'Select plan to quote',
      processing: 'Processing',
      freeTrialTitle: 'Free trial',
      freeTrialDescription: 'Try CyberVPN before purchase',
      activateTrial: 'Activate trial',
      activating: 'Activating',
      trialActivated: 'Trial activated',
      inviteRedeemed: 'Invite redeemed {reward}',
      inviteRewardDays: '{count} free days',
      currentPlanTitle: 'Current plan',
      currentPlanNoExpiry: 'No expiry',
      'flow.checkout': 'Checkout',
      'flow.none': 'None',
      'flow.current': 'Current',
      'quote.basePrice': 'Base',
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
      'quote.serverPool': 'Servers',
      'quote.none': 'None',
      'actions.openPayment': 'Open payment',
    };
    const template = labels[key] ?? key;
    if (!values) return template;
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

const plusPlan = {
  uuid: 'plan-plus-365',
  name: 'plus_365',
  plan_code: 'plus',
  display_name: 'Plus',
  catalog_visibility: 'public',
  features: {},
  devices_included: 5,
  connection_modes: ['standard', 'stealth'],
  server_pool: ['shared_plus'],
  support_sla: 'standard',
  dedicated_ip: { included: 0, eligible: true },
  duration_days: 365,
  traffic_limit_bytes: null,
  traffic_policy: { mode: 'fair_use', display_label: 'Unlimited' },
  sale_channels: ['miniapp'],
  trial_eligible: true,
  price_usd: 79,
  price_rub: null,
  sort_order: 2,
  is_active: true,
  invite_bundle: { count: 2, friend_days: 14, expiry_days: 60 },
};

const basicPlan = {
  ...plusPlan,
  uuid: 'plan-basic-30',
  name: 'basic_30',
  plan_code: 'basic',
  display_name: 'Basic',
  devices_included: 2,
  connection_modes: ['standard'],
  server_pool: ['shared_basic'],
  duration_days: 30,
  price_usd: 9.99,
  sort_order: 1,
  invite_bundle: { count: 0, friend_days: 0, expiry_days: 0 },
};

function createQuoteResponse() {
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
      display_name: 'Plus',
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
  };
}

function createOffers(overrides: Record<string, unknown> = {}) {
  return {
    plans: [basicPlan, plusPlan],
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
      generatedAt: '2026-04-24T00:00:00Z',
    },
    ...overrides,
  };
}

function createBootstrap(overrides: Record<string, unknown> = {}) {
  return {
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
    ...overrides,
  };
}

describe('MiniApp Plans Page', () => {
  let telegramMock: ReturnType<typeof setupTelegramWebAppMock>;

  beforeEach(() => {
    telegramMock = setupTelegramWebAppMock();
    apiMocks.miniappApi.getOffers.mockResolvedValue({ data: createOffers() });
    apiMocks.miniappApi.getBootstrap.mockResolvedValue({ data: createBootstrap() });
    apiMocks.miniappApi.quoteCheckout.mockResolvedValue({ data: createQuoteResponse() });
    apiMocks.miniappApi.commitCheckout.mockResolvedValue({
      data: {
        status: 'pending',
        payment_id: 'payment-1',
        invoice: {
          payment_url: 'https://t.me/CryptoBot?start=pay_ABC123',
          currency: 'USD',
        },
      },
    });
    apiMocks.miniappApi.activateTrial.mockResolvedValue({
      data: {
        activated: true,
        trial_end: '2026-05-01T00:00:00Z',
        message: 'Trial activated',
      },
    });
    apiMocks.codesApi.resolve.mockResolvedValue({
      data: {
        accepted: true,
        code_type: 'promo',
        action_context: 'checkout',
        result: 'accepted',
        reject_reason: null,
        conflict_code: null,
        wrong_context_target: null,
        issuer_type: 'admin',
        owner_type: 'admin_campaign',
        resolved_code_id: 'promo-1',
        promo_code_id: 'promo-1',
        partner_code_id: null,
        user_message_key: 'growth_codes.promo.accepted',
      },
    });
    apiMocks.invitesApi.redeem.mockResolvedValue({
      data: {
        free_days: 14,
      },
    });
  });

  afterEach(() => {
    cleanupTelegramWebAppMock();
    vi.clearAllMocks();
  });

  it('test_displays_loading_spinner', () => {
    apiMocks.miniappApi.getOffers.mockReturnValue(new Promise(() => {}));

    render(<MiniAppPlansPage />, { wrapper: createWrapper() });

    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('test_displays_current_public_plans_and_pricing', async () => {
    render(<MiniAppPlansPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Available plans')).toBeInTheDocument();
      expect(screen.getByText('Basic')).toBeInTheDocument();
      expect(screen.getByText('Plus')).toBeInTheDocument();
      expect(screen.getByText('Annual')).toBeInTheDocument();
      expect(apiMocks.miniappApi.quoteCheckout).toHaveBeenCalledWith(
        expect.objectContaining({
          plan_id: 'plan-plus-365',
        }),
      );
    });
  });

  it('test_opens_payment_after_checkout_commit', async () => {
    const user = userEvent.setup();

    render(<MiniAppPlansPage />, { wrapper: createWrapper() });

    const openPaymentButton = await screen.findByRole('button', { name: /Open payment/ });

    await waitFor(() => {
      expect(openPaymentButton).toBeEnabled();
    });

    await user.click(openPaymentButton);

    await waitFor(() => {
      expect(apiMocks.miniappApi.commitCheckout).toHaveBeenCalledWith(
        expect.objectContaining({
          flow: 'checkout',
          plan_id: 'plan-plus-365',
          currency: 'USD',
        }),
      );
      expect(telegramMock.openTelegramLink).toHaveBeenCalledWith(
        'https://t.me/CryptoBot?start=pay_ABC123',
      );
    });
  });

  it('test_activate_trial_button_triggers_mutation', async () => {
    const user = userEvent.setup();
    apiMocks.miniappApi.getOffers.mockResolvedValue({
      data: createOffers({
        plans: [],
        trial: {
          is_trial_active: false,
          is_eligible: true,
          trial_end: null,
          days_remaining: 0,
        },
      }),
    });

    render(<MiniAppPlansPage />, { wrapper: createWrapper() });

    const activateButton = await screen.findByRole('button', { name: 'Activate trial' });
    await user.click(activateButton);

    await waitFor(() => {
      expect(apiMocks.miniappApi.activateTrial).toHaveBeenCalled();
      expect(telegramMock.showAlert).toHaveBeenCalledWith('Trial activated');
    });
  });

  it('test_resolves_uppercased_checkout_code', async () => {
    const user = userEvent.setup();

    render(<MiniAppPlansPage />, { wrapper: createWrapper() });

    await screen.findByText('Available plans');
    await user.type(screen.getByPlaceholderText('Promo code'), 'save5');
    await user.click(screen.getByRole('button', { name: 'Apply' }));

    await waitFor(() => {
      expect(apiMocks.codesApi.resolve).toHaveBeenCalledWith(
        expect.objectContaining({
          code: 'SAVE5',
          action_context: 'checkout',
          plan_id: 'plan-plus-365',
          channel: 'miniapp',
        }),
      );
      expect(screen.getByText('Code accepted SAVE5')).toBeInTheDocument();
    });
  });

  it('test_redeems_invite_code', async () => {
    const user = userEvent.setup();

    render(<MiniAppPlansPage />, { wrapper: createWrapper() });

    await screen.findByText('Have invite code');
    await user.type(screen.getByPlaceholderText('Invite code'), 'friend14');
    await user.click(screen.getByRole('button', { name: 'Redeem' }));

    await waitFor(() => {
      expect(apiMocks.invitesApi.redeem).toHaveBeenCalledWith({ code: 'FRIEND14' });
      expect(telegramMock.showAlert).toHaveBeenCalledWith('Invite redeemed 14 free days');
    });
  });
});
