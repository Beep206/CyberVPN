import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import PlansPage from '../page';
import { server } from '@/test/mocks/server';
import {
  cleanupTelegramWebAppMock,
  setupTelegramWebAppMock,
} from '@/test/mocks/telegram-webapp';

const runtimeAnalyticsMocks = vi.hoisted(() => ({
  emitMiniAppRuntimeEvent: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('@/features/miniapp-runtime/lib/runtime-analytics', () => runtimeAnalyticsMocks);

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => (key: string, values?: Record<string, string | number>) => {
    const labels: Record<string, string> = {
      availablePlans: 'Available plans',
      catalogHint: 'Catalog hint',
      'periods.annual': 'Annual',
      'periods.monthly': 'Monthly',
      planDevices: '{count} devices',
      periodInviteBonus: '{count} invites',
      addonsTitle: 'Add-ons',
      addonsDescription: 'Add-ons description',
      addonUnavailable: 'Unavailable',
      havePromoCode: 'Have promo code',
      promoCodePlaceholder: 'Promo code',
      apply: 'Apply',
      checkoutCodeAccepted: 'Code accepted {code}',
      haveInviteCode: 'Have invite code',
      inviteCodePlaceholder: 'Invite code',
      redeem: 'Redeem',
      quoteTitle: 'Quote',
      quoteSubtitle: 'Quote subtitle',
      billingCurrencyNotice: 'Charged in {currency}',
      localEstimate: 'Approx. {price} display only',
      selectPlanToQuote: 'Select plan to quote',
      processing: 'Processing',
      freeTrialTitle: 'Free trial',
      freeTrialDescription: 'Try CyberVPN before purchase',
      activateTrial: 'Activate trial',
      activating: 'Activating',
      trialActivated: 'Trial activated',
      trialError: 'Trial error',
      inviteRedeemed: 'Invite redeemed {reward}',
      inviteRewardDays: '{count} free days',
      inviteRewardDefault: 'default reward',
      currentPlanNoExpiry: 'No expiry',
      currentPlanTitle: 'Current plan',
      noPlans: 'No plans',
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
      'quote.benefitsPreview': 'Benefits after activation',
      'quote.inviteBenefitWithDays': '{count} invites · {days} friend days',
      'quote.inviteBenefit': '{count} invites after activation',
      'quote.benefitAvailableAfter': 'Available after {stage}',
      'quote.benefitExpiresAt': 'Expires {date}',
      'quote.benefitStages.settlement': 'settlement',
      'quote.benefitStages.activation': 'activation',
      'actions.openPayment': 'Open payment',
      'actions.activateFree': 'Activate for free',
      'actions.activatingFree': 'Activating subscription',
      paymentError: 'Payment error',
      'zeroGateway.activatedAlert': 'Free activation completed. Your subscription is active.',
      'zeroGateway.title': 'Subscription activated',
      'zeroGateway.description': 'Zero checkout completed.',
      'zeroGateway.noInvoice': 'No Telegram invoice or payment redirect was opened for this order.',
      'zeroGateway.rewardHint': 'Open rewards after activation.',
      'zeroGateway.openRewards': 'Open rewards',
      'privateOffer.title': 'Private offer access',
      'privateOffer.description': 'Enter a private access code',
      'privateOffer.codeLabel': 'Private access code',
      'privateOffer.codePlaceholder': 'Private code',
      'privateOffer.unlockCta': 'Unlock offer',
      'privateOffer.unlockingCta': 'Checking',
      'privateOffer.retryCta': 'Retry',
      'privateOffer.clearCta': 'Clear private offer',
      'privateOffer.availableLabel': 'Available by code',
      'privateOffer.selectedLabel': 'Private offer selected',
      'privateOffer.selectCta': 'Use this offer',
      'privateOffer.previewOnlyHint': 'Sign in before checkout',
      'privateOffer.validationError': 'Enter a private access code first',
      'privateOffer.noOffers': 'No private offers',
      'privateOffer.networkError': 'Network failed',
      'privateOffer.authorizationError': 'Session failed',
      'privateOffer.genericError': 'Private offer failed',
      'privateOffer.grantDegraded': 'Private grant degraded',
      'privateOffer.grantExpired': 'Private grant expired',
      'privateOffer.unlocked': 'Private offer unlocked',
      'privateOffer.priceLabel': 'Private price',
      'privateOffer.durationDays': '{days} days',
      'privateOffer.expiresAt': 'Grant expires {date}',
      'privateOffer.devices': '{count} devices',
      'privateOffer.traffic': 'Traffic: {label}',
      'privateOffer.modes': 'Modes: {modes}',
      'privateOffer.serverPool': 'Servers: {servers}',
      'privateOffer.support': 'Support: {support}',
      'privateOffer.quoteError': 'Private quote failed',
    };
    const template = labels[key] ?? key;
    if (!values) return template;
    return Object.entries(values).reduce(
      (result, [name, value]) => result.replaceAll(`{${name}}`, String(value)),
      template,
    );
  },
}));

const API_BASE = '*/api/v1';
const API_BASE_V3 = '*/api/v3';
const PRIVATE_GRANT_ID = '99999999-9999-4999-8999-999999999999';

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

function createBootstrap() {
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
  };
}

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

function createPrivatePreflight() {
  return {
    code_set_id: 'code-set-private',
    code_set_hash: 'hash-private',
    status: 'accepted',
    applications: [
      {
        client_slot_id: 'private-offer',
        masked_code: 'PRIV***',
        status: 'accepted',
        roles: ['private_catalog_access'],
        message_key: 'growth_codes.private.accepted',
      },
    ],
    private_catalog_grant: {
      id: PRIVATE_GRANT_ID,
      expires_at: '2099-04-18T12:00:00Z',
    },
    private_offers: [
      {
        plan_id: 'plan-private-90',
        offer_id: 'offer-private-90',
        display_name: 'Private 90',
        duration_days: 90,
        price: {
          amount: '19.00',
          currency: 'USD',
        },
        entitlement_summary: {
          device_limit: 3,
          display_traffic_label: 'Unlimited',
          connection_modes: ['stealth'],
          server_pool: ['premium'],
          support_sla: 'priority',
        },
        quote_handoff: {
          private_catalog_grant_id: PRIVATE_GRANT_ID,
        },
      },
    ],
    risk: {
      action: 'allow',
    },
  };
}

function createClientCapabilities() {
  return {
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
  };
}

describe('MiniAppPlansPage', () => {
  let telegramMock: ReturnType<typeof setupTelegramWebAppMock>;
  const requests: Array<{ url: string; body: unknown }> = [];

  beforeEach(() => {
    telegramMock = setupTelegramWebAppMock();
    requests.length = 0;
    vi.clearAllMocks();

    server.use(
      http.get(`${API_BASE}/client/capabilities`, () => HttpResponse.json(createClientCapabilities())),
      http.get(`${API_BASE}/miniapp/offers`, () => HttpResponse.json(createOffers())),
      http.get(`${API_BASE}/miniapp/bootstrap`, () => HttpResponse.json(createBootstrap())),
      http.post(`${API_BASE}/miniapp/trial/activate`, () =>
        HttpResponse.json({
          activated: true,
          trial_end: '2026-05-01T00:00:00Z',
          message: 'Trial activated',
        }),
      ),
      http.post(`${API_BASE}/miniapp/checkout/quote`, async ({ request }) => {
        requests.push({ url: request.url, body: await request.json() });
        return HttpResponse.json(createQuoteResponse());
      }),
      http.post(`${API_BASE}/miniapp/checkout/commit`, async ({ request }) => {
        requests.push({ url: request.url, body: await request.json() });
        return HttpResponse.json({
          status: 'pending',
          payment_id: 'payment-1',
          invoice: {
            payment_url: 'https://t.me/CryptoBot?start=pay_ABC123',
            currency: 'USD',
          },
        });
      }),
      http.post(`${API_BASE}/codes/resolve`, async ({ request }) => {
        requests.push({ url: request.url, body: await request.json() });
        return HttpResponse.json({
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
        });
      }),
      http.post(`${API_BASE}/invites/redeem`, async ({ request }) => {
        requests.push({ url: request.url, body: await request.json() });
        return HttpResponse.json({ free_days: 14 });
      }),
    );
  });

  afterEach(() => {
    cleanupTelegramWebAppMock();
  });

  it('test_shows_loading_spinner_while_fetching_offers', () => {
    server.use(
      http.get(`${API_BASE}/miniapp/offers`, async () => {
        await new Promise((resolve) => setTimeout(resolve, 100));
        return HttpResponse.json(createOffers());
      }),
    );

    render(<PlansPage />, { wrapper: createWrapper() });

    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('test_displays_public_plan_catalog_from_miniapp_offers', async () => {
    render(<PlansPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Available plans')).toBeInTheDocument();
      expect(screen.getByText('Basic')).toBeInTheDocument();
      expect(screen.getByText('Plus')).toBeInTheDocument();
      expect(screen.getByText('Annual')).toBeInTheDocument();
      expect(screen.queryByText(/display only/i)).not.toBeInTheDocument();
    });
  });

  it('test_activates_trial_through_miniapp_endpoint', async () => {
    const user = userEvent.setup();
    server.use(
      http.get(`${API_BASE}/miniapp/offers`, () =>
        HttpResponse.json(createOffers({
          plans: [],
          trial: {
            is_trial_active: false,
            is_eligible: true,
            trial_end: null,
            days_remaining: 0,
          },
        })),
      ),
    );

    render(<PlansPage />, { wrapper: createWrapper() });

    await user.click(await screen.findByRole('button', { name: 'Activate trial' }));

    await waitFor(() => {
      expect(telegramMock.showAlert).toHaveBeenCalledWith('Trial activated');
    });
  });

  it('test_commits_checkout_and_opens_telegram_payment_url', async () => {
    const user = userEvent.setup();

    render(<PlansPage />, { wrapper: createWrapper() });

    const openPaymentButton = await screen.findByRole('button', { name: /Open payment/ });
    await waitFor(() => expect(openPaymentButton).toBeEnabled());

    await user.click(openPaymentButton);

    await waitFor(() => {
      expect(requests).toContainEqual(
        expect.objectContaining({
          body: expect.objectContaining({
            flow: 'checkout',
            plan_id: 'plan-plus-365',
            currency: 'USD',
          }),
        }),
      );
      expect(telegramMock.openTelegramLink).toHaveBeenCalledWith(
        'https://t.me/CryptoBot?start=pay_ABC123',
      );
    });

  });

  it('test_zero_gateway_checkout_activates_without_opening_invoice_and_refreshes_rewards', async () => {
    const user = userEvent.setup();
    const invalidateSpy = vi.spyOn(QueryClient.prototype, 'invalidateQueries');
    const windowOpenSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
    let zeroGatewaySettled = false;

    try {
      server.use(
        http.get(`${API_BASE}/miniapp/offers`, () =>
          HttpResponse.json(createOffers(
            zeroGatewaySettled
              ? { currentEntitlements: createQuoteResponse().entitlements_snapshot }
              : {},
          )),
        ),
        http.post(`${API_BASE}/miniapp/checkout/quote`, async ({ request }) => {
          const body = await request.json();
          requests.push({ url: request.url, body });
          return HttpResponse.json({
            ...createQuoteResponse(),
            displayed_price: 0,
            discount_amount: 79,
            gateway_amount: 0,
            is_zero_gateway: true,
            requires_external_payment: false,
            settlement_mode: 'internal_zero',
            growth_effects: {
              benefits_preview: [
                {
                  type: 'issue_invites',
                  count: 10,
                  friend_days: 7,
                  available_after: 'settlement',
                },
              ],
            },
          });
        }),
        http.post(`${API_BASE}/quotes/`, async ({ request }) => {
          const body = await request.json();
          requests.push({ url: request.url, body });
          return HttpResponse.json({
            id: 'quote-zero-1',
            user_id: 'user-1',
            auth_realm_id: 'realm-1',
            storefront_id: 'storefront-1',
            storefront_key: 'cybervpn-web',
            sale_channel: 'miniapp',
            currency_code: 'USD',
            status: 'open',
            expires_at: '2030-01-01T00:00:00Z',
            quote: {
              ...createQuoteResponse(),
              displayed_price: 0,
              discount_amount: 79,
              gateway_amount: 0,
              is_zero_gateway: true,
              requires_external_payment: false,
              settlement_mode: 'internal_zero',
              growth_effects: {
                benefits_preview: [
                  {
                    type: 'issue_invites',
                    count: 10,
                    friend_days: 7,
                    available_after: 'settlement',
                  },
                ],
              },
            },
            created_at: '2026-06-01T00:00:00Z',
            updated_at: '2026-06-01T00:00:00Z',
          });
        }),
        http.post(`${API_BASE}/checkout-sessions/`, async ({ request }) => {
          requests.push({ url: request.url, body: await request.json() });
          return HttpResponse.json({ id: 'checkout-zero-1', quote_session_id: 'quote-zero-1' });
        }),
        http.post(`${API_BASE}/orders/commit`, async ({ request }) => {
          requests.push({ url: request.url, body: await request.json() });
          return HttpResponse.json({ id: 'order-zero-1', checkout_session_id: 'checkout-zero-1' });
        }),
        http.post(`${API_BASE}/payment-attempts/`, async ({ request }) => {
          requests.push({ url: request.url, body: await request.json() });
          zeroGatewaySettled = true;
          return HttpResponse.json({
            id: 'attempt-zero-1',
            order_id: 'order-zero-1',
            payment_id: 'payment-zero-1',
            provider: 'internal_zero',
            status: 'succeeded',
            gateway_amount: 0,
            invoice: null,
          });
        }),
      );

      render(<PlansPage />, { wrapper: createWrapper() });

      const activateButton = await screen.findByRole('button', { name: 'Activate for free' });
      await waitFor(() => expect(activateButton).toBeEnabled());
      expect(screen.getByText('10 invites · 7 friend days')).toBeInTheDocument();

      await user.click(activateButton);

      await waitFor(() => {
        expect(requests).toContainEqual(
          expect.objectContaining({
            url: expect.stringContaining('/payment-attempts/'),
            body: expect.objectContaining({
              order_id: 'order-zero-1',
            }),
          }),
        );
        expect(requests.some((entry) => entry.url.includes('/miniapp/checkout/commit'))).toBe(false);
        expect(telegramMock.showAlert).toHaveBeenCalledWith(
          'Free activation completed. Your subscription is active.',
        );
      });

      expect(telegramMock.openInvoice).not.toHaveBeenCalled();
      expect(telegramMock.openTelegramLink).not.toHaveBeenCalled();
      expect(telegramMock.openLink).not.toHaveBeenCalled();
      expect(windowOpenSpy).not.toHaveBeenCalled();
      await waitFor(() => {
        expect(screen.getByRole('status')).toHaveTextContent('Subscription activated');
      });
      expect(screen.getByText('No Telegram invoice or payment redirect was opened for this order.')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Open rewards/ })).toBeInTheDocument();

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['orders'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['payments', 'history'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['current-entitlements'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['subscriptions'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['growth', 'invites'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['growth', 'rewards'] });
      expect(runtimeAnalyticsMocks.emitMiniAppRuntimeEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          event: 'miniapp_checkout_completed',
          page: 'plans',
          paymentRail: 'zero_gateway',
          paymentStatus: 'completed',
        }),
      );
      expect(JSON.stringify(runtimeAnalyticsMocks.emitMiniAppRuntimeEvent.mock.calls)).not.toContain('payment-zero-1');
    } finally {
      invalidateSpy.mockRestore();
      windowOpenSpy.mockRestore();
    }
  });

  it('test_checkout_failure_telemetry_uses_stable_error_code_without_raw_detail', async () => {
    const user = userEvent.setup();

    server.use(
      http.post(`${API_BASE}/miniapp/checkout/commit`, async ({ request }) => {
        requests.push({ url: request.url, body: await request.json() });
        return HttpResponse.json(
          {
            detail: 'payment-zero-1 FREE100 https://pay.example.invalid/session-secret',
          },
          { status: 400 },
        );
      }),
    );

    render(<PlansPage />, { wrapper: createWrapper() });

    const openPaymentButton = await screen.findByRole('button', { name: /Open payment/ });
    await waitFor(() => expect(openPaymentButton).toBeEnabled());
    await user.click(openPaymentButton);

    await waitFor(() => {
      expect(runtimeAnalyticsMocks.emitMiniAppRuntimeEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          event: 'miniapp_checkout_failed',
          errorCode: 'checkout_commit_validation_failed',
        }),
      );
      expect(telegramMock.showAlert).toHaveBeenCalledWith('Payment error');
    });

    const telemetryCalls = JSON.stringify(runtimeAnalyticsMocks.emitMiniAppRuntimeEvent.mock.calls);
    expect(telemetryCalls).not.toContain('FREE100');
    expect(telemetryCalls).not.toContain('payment-zero-1');
    expect(telemetryCalls).not.toContain('pay.example.invalid');
  });

  it('test_carries_private_offer_grant_into_quote_and_commit', async () => {
    const user = userEvent.setup();
    let preflightBody: Record<string, unknown> | null = null;

    server.use(
      http.post(`${API_BASE_V3}/growth/code-sets/preflight`, async ({ request }) => {
        preflightBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(createPrivatePreflight());
      }),
    );

    render(<PlansPage />, { wrapper: createWrapper() });

    await screen.findByText('Available plans');
    await user.type(screen.getByLabelText('Private access code'), 'private2026');
    await user.click(screen.getByRole('button', { name: 'Unlock offer' }));
    await user.click(await screen.findByRole('button', { name: 'Use this offer' }));

    await waitFor(() => {
      expect(preflightBody).toMatchObject({
        storefront_key: 'cybervpn-web',
        channel: 'miniapp',
        currency: 'USD',
        codes: [
          {
            code: 'PRIVATE2026',
            client_slot_id: 'private-offer',
          },
        ],
      });
      expect(requests).toContainEqual(
        expect.objectContaining({
          url: expect.stringContaining('/miniapp/checkout/quote'),
          body: expect.objectContaining({
            flow: 'checkout',
            plan_id: 'plan-private-90',
            private_catalog_grant_id: PRIVATE_GRANT_ID,
          }),
        }),
      );
    });

    await user.click(screen.getByRole('button', { name: /Open payment/ }));

    await waitFor(() => {
      expect(requests).toContainEqual(
        expect.objectContaining({
          url: expect.stringContaining('/miniapp/checkout/commit'),
          body: expect.objectContaining({
            flow: 'checkout',
            plan_id: 'plan-private-90',
            private_catalog_grant_id: PRIVATE_GRANT_ID,
          }),
        }),
      );
    });

    requests.length = 0;
    await user.type(screen.getByLabelText('Private access code'), 'X');

    await waitFor(() => {
      expect(requests).toContainEqual(
        expect.objectContaining({
          url: expect.stringContaining('/miniapp/checkout/quote'),
          body: expect.objectContaining({
            flow: 'checkout',
            plan_id: 'plan-plus-365',
          }),
        }),
      );
    });
    expect(
      requests
        .filter((entry) => entry.url.includes('/miniapp/checkout/quote'))
        .every((entry) => (entry.body as Record<string, unknown>).private_catalog_grant_id == null),
    ).toBe(true);
  });

  it('test_applies_checkout_code_basket_and_commits_grouped_multi_code_payload', async () => {
    const user = userEvent.setup();

    server.use(
      http.get(`${API_BASE}/client/capabilities`, () => {
        const capabilities = createClientCapabilities();
        return HttpResponse.json({
          ...capabilities,
          growth: {
            ...capabilities.growth,
            checkout_code_discounts: true,
          },
        });
      }),
      http.post(`${API_BASE}/miniapp/checkout/quote`, async ({ request }) => {
        const body = await request.json() as Record<string, unknown>;
        requests.push({ url: request.url, body });
        const hasCodes = Array.isArray(body.codes) && body.codes.length > 0;
        const hasLegacyCode = Boolean(body.code_input);
        return HttpResponse.json({
          ...createQuoteResponse(),
          displayed_price: hasCodes || hasLegacyCode ? 63.2 : 79,
          discount_amount: hasCodes || hasLegacyCode ? 15.8 : 0,
        });
      }),
    );

    render(<PlansPage />, { wrapper: createWrapper() });

    await screen.findByText('growthCodeBasket.title');
    const codeInput = screen.getByLabelText('growthCodeBasket.inputLabel');
    await user.type(codeInput, 'save1500');
    await user.click(screen.getByRole('button', { name: 'growthCodeBasket.addCta' }));

    await waitFor(() => {
      expect(requests).toContainEqual(
        expect.objectContaining({
          url: expect.stringContaining('/codes/resolve'),
          body: expect.objectContaining({
            code: 'SAVE1500',
            action_context: 'checkout',
            plan_id: 'plan-plus-365',
            channel: 'miniapp',
          }),
        }),
      );
      expect(requests).toContainEqual(
        expect.objectContaining({
          url: expect.stringContaining('/miniapp/checkout/quote'),
          body: expect.objectContaining({
            code_input: 'SAVE1500',
          }),
        }),
      );
      expect(screen.queryByText('growthCodeBasket.contextChanged')).not.toBeInTheDocument();
    });

    await user.type(codeInput, 'loyal10');
    await user.click(screen.getByRole('button', { name: 'growthCodeBasket.addCta' }));

    await waitFor(() => {
      expect(screen.getByText('growthCodeBasket.degraded')).toBeInTheDocument();
      expect(requests).toContainEqual(
        expect.objectContaining({
          url: expect.stringContaining('/miniapp/checkout/quote'),
          body: expect.objectContaining({
            codes: [
              { code: 'SAVE1500', client_slot_id: 'miniapp-1' },
              { code: 'LOYAL10', client_slot_id: 'miniapp-2' },
            ],
          }),
        }),
      );
    });
    const openPaymentButton = screen.getByRole('button', { name: /Open payment/ });
    expect(openPaymentButton).toBeEnabled();
    await user.click(openPaymentButton);

    await waitFor(() => {
      expect(requests).toContainEqual(
        expect.objectContaining({
          url: expect.stringContaining('/miniapp/checkout/commit'),
          body: expect.objectContaining({
            flow: 'checkout',
            plan_id: 'plan-plus-365',
            codes: [
              { code: 'SAVE1500', client_slot_id: 'miniapp-1' },
              { code: 'LOYAL10', client_slot_id: 'miniapp-2' },
            ],
          }),
        }),
      );
    });
    const groupedCommit = requests.find((entry) =>
      entry.url.includes('/miniapp/checkout/commit')
      && Array.isArray((entry.body as Record<string, unknown>).codes)
    );
    expect(groupedCommit?.body).not.toHaveProperty('code_input');
  });

  it('test_hides_checkout_code_controls_during_s1_beta', async () => {
    render(<PlansPage />, { wrapper: createWrapper() });

    await screen.findByText('Available plans');

    expect(screen.queryByPlaceholderText('Promo code')).not.toBeInTheDocument();
    expect(requests).not.toContainEqual(
      expect.objectContaining({
        body: expect.objectContaining({
          action_context: 'checkout',
        }),
      }),
    );
  });

  it('test_redeems_invite_code_through_invites_endpoint', async () => {
    const user = userEvent.setup();
    const invalidateSpy = vi.spyOn(QueryClient.prototype, 'invalidateQueries');
    const resetSpy = vi.spyOn(QueryClient.prototype, 'resetQueries');

    try {
      render(<PlansPage />, { wrapper: createWrapper() });

      await screen.findByText('Have invite code');
      await user.type(screen.getByPlaceholderText('Invite code'), 'friend14');
      await user.click(screen.getByRole('button', { name: 'Redeem' }));

      await waitFor(() => {
        expect(requests).toContainEqual(
          expect.objectContaining({
            body: { code: 'FRIEND14' },
          }),
        );
        expect(telegramMock.showAlert).toHaveBeenCalledWith('Invite redeemed 14 free days');
      });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['miniapp-bootstrap'] });
      expect(resetSpy).toHaveBeenCalledWith({ queryKey: ['miniapp-config'], exact: true });
    } finally {
      invalidateSpy.mockRestore();
      resetSpy.mockRestore();
    }
  });
});
