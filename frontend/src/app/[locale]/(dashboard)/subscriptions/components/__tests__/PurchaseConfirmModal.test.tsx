import type { ReactElement, ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import type { SubscriptionPlan } from '../../lib/plan-presenter';
import { PurchaseConfirmModal } from '../PurchaseConfirmModal';
import { server } from '@/test/mocks/server';
import { CANONICAL_IDEMPOTENCY_HEADER } from '@/lib/api/client';

vi.mock('@/shared/ui/modal', () => ({
  Modal: ({ isOpen, children }: { isOpen: boolean; children: ReactNode }) =>
    isOpen ? <div data-testid="modal">{children}</div> : null,
}));

const API_BASE = 'http://localhost:8000/api/v1';

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

function renderWithProviders(ui: ReactElement) {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  );
}

function createPlan(overrides: Partial<SubscriptionPlan> = {}): SubscriptionPlan {
  return {
    uuid: 'plan-pro-001',
    name: 'PRO',
    plan_code: 'pro',
    display_name: 'Pro Plan',
    catalog_visibility: 'public',
    duration_days: 30,
    traffic_limit_bytes: null,
    devices_included: 5,
    price_usd: 29.99,
    price_rub: null,
    traffic_policy: {
      mode: 'fair_use',
      display_label: 'Unlimited',
      enforcement_profile: null,
    },
    connection_modes: ['standard', 'stealth'],
    server_pool: ['shared_plus'],
    support_sla: 'priority',
    dedicated_ip: {
      included: 0,
      eligible: true,
    },
    sale_channels: ['web'],
    invite_bundle: {
      count: 0,
      friend_days: 0,
      expiry_days: 0,
    },
    trial_eligible: false,
    features: {},
    is_active: true,
    sort_order: 10,
    ...overrides,
  };
}

function createQuote(overrides: Record<string, unknown> = {}) {
  return {
    base_price: 29.99,
    addon_amount: 0,
    displayed_price: 29.99,
    discount_amount: 0,
    wallet_amount: 0,
    gateway_amount: 29.99,
    partner_markup: 0,
    is_zero_gateway: false,
    plan_id: 'plan-pro-001',
    promo_code_id: null,
    partner_code_id: null,
    addons: [],
    entitlements_snapshot: {
      status: 'active',
      plan_uuid: 'plan-pro-001',
      plan_code: 'pro',
      display_name: 'Pro Plan',
      period_days: 30,
      expires_at: null,
      effective_entitlements: {
        device_limit: 5,
        display_traffic_label: 'Unlimited',
        connection_modes: ['standard', 'stealth'],
        server_pool: ['shared_plus'],
        support_sla: 'priority',
      },
      invite_bundle: {},
      is_trial: false,
      addons: [],
    },
    ...overrides,
  };
}

function createQuoteSession(overrides: Record<string, unknown> = {}) {
  return {
    id: '11111111-1111-1111-1111-111111111111',
    user_id: '22222222-2222-2222-2222-222222222222',
    auth_realm_id: '33333333-3333-3333-3333-333333333333',
    storefront_id: '44444444-4444-4444-4444-444444444444',
    storefront_key: 'cybervpn-web',
    merchant_profile_id: null,
    invoice_profile_id: null,
    billing_descriptor_id: null,
    pricebook_id: null,
    pricebook_key: 'official-web-usd',
    pricebook_entry_id: null,
    offer_id: null,
    offer_key: null,
    legal_document_set_id: null,
    legal_document_set_key: null,
    program_eligibility_policy_id: null,
    subscription_plan_id: 'plan-pro-001',
    sale_channel: 'web',
    currency_code: 'USD',
    status: 'open',
    expires_at: '2026-04-18T12:00:00Z',
    quote: createQuote(),
    created_at: '2026-04-18T10:00:00Z',
    updated_at: '2026-04-18T10:00:00Z',
    ...overrides,
  };
}

function createCheckoutSession(overrides: Record<string, unknown> = {}) {
  return {
    id: '55555555-5555-5555-5555-555555555555',
    quote_session_id: '11111111-1111-1111-1111-111111111111',
    user_id: '22222222-2222-2222-2222-222222222222',
    auth_realm_id: '33333333-3333-3333-3333-333333333333',
    storefront_id: '44444444-4444-4444-4444-444444444444',
    storefront_key: 'cybervpn-web',
    merchant_profile_id: null,
    invoice_profile_id: null,
    billing_descriptor_id: null,
    pricebook_id: null,
    pricebook_key: 'official-web-usd',
    pricebook_entry_id: null,
    offer_id: null,
    offer_key: null,
    legal_document_set_id: null,
    legal_document_set_key: null,
    program_eligibility_policy_id: null,
    subscription_plan_id: 'plan-pro-001',
    sale_channel: 'web',
    currency_code: 'USD',
    status: 'open',
    idempotency_key: 'checkout-session-test',
    expires_at: '2026-04-18T12:05:00Z',
    quote: createQuote(),
    created_at: '2026-04-18T10:01:00Z',
    updated_at: '2026-04-18T10:01:00Z',
    ...overrides,
  };
}

function createOrder(overrides: Record<string, unknown> = {}) {
  return {
    id: '66666666-6666-6666-6666-666666666666',
    quote_session_id: '11111111-1111-1111-1111-111111111111',
    checkout_session_id: '55555555-5555-5555-5555-555555555555',
    user_id: '22222222-2222-2222-2222-222222222222',
    auth_realm_id: '33333333-3333-3333-3333-333333333333',
    storefront_id: '44444444-4444-4444-4444-444444444444',
    merchant_profile_id: null,
    invoice_profile_id: null,
    billing_descriptor_id: null,
    pricebook_id: null,
    pricebook_entry_id: null,
    offer_id: null,
    legal_document_set_id: null,
    program_eligibility_policy_id: null,
    subscription_plan_id: 'plan-pro-001',
    promo_code_id: null,
    partner_code_id: null,
    sale_channel: 'web',
    currency_code: 'USD',
    order_status: 'committed',
    settlement_status: 'pending_payment',
    base_price: 29.99,
    addon_amount: 0,
    displayed_price: 29.99,
    discount_amount: 0,
    wallet_amount: 0,
    gateway_amount: 29.99,
    partner_markup: 0,
    commission_base_amount: 29.99,
    merchant_snapshot: {},
    pricing_snapshot: {},
    policy_snapshot: {},
    entitlements_snapshot: createQuote().entitlements_snapshot,
    items: [
      {
        id: '77777777-7777-7777-7777-777777777777',
        order_id: '66666666-6666-6666-6666-666666666666',
        item_type: 'plan',
        subject_id: 'plan-pro-001',
        subject_code: 'pro',
        display_name: 'Pro Plan',
        quantity: 1,
        unit_price: 29.99,
        total_price: 29.99,
        currency_code: 'USD',
        item_snapshot: {},
        created_at: '2026-04-18T10:02:00Z',
        updated_at: '2026-04-18T10:02:00Z',
      },
    ],
    created_at: '2026-04-18T10:02:00Z',
    updated_at: '2026-04-18T10:02:00Z',
    ...overrides,
  };
}

function createPaymentAttempt(overrides: Record<string, unknown> = {}) {
  return {
    id: '88888888-8888-8888-8888-888888888888',
    order_id: '66666666-6666-6666-6666-666666666666',
    payment_id: null,
    supersedes_attempt_id: null,
    attempt_number: 1,
    provider: 'crypto',
    sale_channel: 'web',
    currency_code: 'USD',
    status: 'pending',
    displayed_amount: 29.99,
    wallet_amount: 0,
    gateway_amount: 29.99,
    external_reference: 'invoice-001',
    idempotency_key: 'payment-attempt-test',
    provider_snapshot: {},
    request_snapshot: {},
    invoice: {
      invoice_id: 'invoice-001',
      payment_url: 'https://pay.cybervpn.test/invoice-001',
      amount: 29.99,
      currency: 'USD',
      status: 'pending',
      expires_at: '2026-04-18T12:10:00Z',
    },
    terminal_at: null,
    created_at: '2026-04-18T10:03:00Z',
    updated_at: '2026-04-18T10:03:00Z',
    ...overrides,
  };
}

describe('PurchaseConfirmModal', () => {
  afterEach(() => {
    server.resetHandlers();
  });

  it('loads a canonical quote session when the modal opens', async () => {
    const capturedBodies: Record<string, unknown>[] = [];

    server.use(
      http.post(`${API_BASE}/quotes/`, async ({ request }) => {
        capturedBodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(createQuoteSession(), { status: 201 });
      }),
    );

    renderWithProviders(
      <PurchaseConfirmModal
        isOpen={true}
        onClose={vi.fn()}
        plan={createPlan()}
      />,
    );

    expect(await screen.findByText('Pro Plan')).toBeInTheDocument();

    await waitFor(() => {
      expect(capturedBodies).toHaveLength(1);
    });

    expect(capturedBodies[0]).toMatchObject({
      storefront_key: 'cybervpn-web',
      plan_id: 'plan-pro-001',
      channel: 'web',
      currency: 'USD',
    });
    expect(screen.getByText('Checkout total')).toBeInTheDocument();
  });

  it('re-quotes against canonical quote sessions when a promo code is applied', async () => {
    const user = userEvent.setup({ delay: null });
    const capturedPromoCodes: Array<string | null> = [];

    server.use(
      http.post(`${API_BASE}/quotes/`, async ({ request }) => {
        const body = (await request.json()) as { promo_code?: string | null };
        capturedPromoCodes.push(body.promo_code ?? null);

        if (body.promo_code === 'SAVE20') {
          return HttpResponse.json(
            createQuoteSession({
              quote: createQuote({
                displayed_price: 24.99,
                discount_amount: 5,
                gateway_amount: 24.99,
              }),
            }),
            { status: 201 },
          );
        }

        return HttpResponse.json(createQuoteSession(), { status: 201 });
      }),
    );

    renderWithProviders(
      <PurchaseConfirmModal
        isOpen={true}
        onClose={vi.fn()}
        plan={createPlan()}
      />,
    );

    await screen.findByText('Checkout total');

    await user.type(screen.getByLabelText(/Promo Code/i), 'save20');
    await user.click(screen.getByRole('button', { name: /Apply Promo/i }));

    await waitFor(() => {
      expect(capturedPromoCodes).toContain('SAVE20');
    });

    expect(await screen.findByText(/SAVE20 applied/i)).toBeInTheDocument();
  });

  it('does not surface partner markup-only quote adjustments on official web', async () => {
    server.use(
      http.post(`${API_BASE}/quotes/`, async ({ request }) => {
        const body = (await request.json()) as { promo_code?: string | null };

        return HttpResponse.json(
          createQuoteSession({
            quote: createQuote({
              discount_amount: body.promo_code ? 0 : 0,
              partner_markup: body.promo_code ? 6.5 : 0,
            }),
          }),
        );
      }),
    );

    renderWithProviders(
      <PurchaseConfirmModal
        isOpen
        onClose={vi.fn()}
        plan={createPlan()}
      />,
    );

    await screen.findByText('Have a Promo Code?');

    const promoInput = screen.getByLabelText('Promo Code');
    await userEvent.type(promoInput, 'save20');
    await userEvent.click(screen.getByRole('button', { name: 'Apply Promo' }));

    await waitFor(() => {
      expect(screen.queryByText('Quote Updated')).not.toBeInTheDocument();
    });
  });

  it('commits canonical checkout flow and opens invoice from payment attempt', async () => {
    const user = userEvent.setup({ delay: null });
    const windowOpenSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
    let checkoutBody: Record<string, unknown> | null = null;
    let checkoutIdempotencyKey: string | null = null;
    let orderCommitBody: Record<string, unknown> | null = null;
    let paymentAttemptBody: Record<string, unknown> | null = null;
    let paymentAttemptIdempotencyKey: string | null = null;

    server.use(
      http.post(`${API_BASE}/quotes/`, async () =>
        HttpResponse.json(createQuoteSession(), { status: 201 })),
      http.post(`${API_BASE}/checkout-sessions/`, async ({ request }) => {
        checkoutBody = (await request.json()) as Record<string, unknown>;
        checkoutIdempotencyKey = request.headers.get(CANONICAL_IDEMPOTENCY_HEADER);
        return HttpResponse.json(createCheckoutSession(), { status: 201 });
      }),
      http.post(`${API_BASE}/orders/commit`, async ({ request }) => {
        orderCommitBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(createOrder(), { status: 201 });
      }),
      http.post(`${API_BASE}/payment-attempts/`, async ({ request }) => {
        paymentAttemptBody = (await request.json()) as Record<string, unknown>;
        paymentAttemptIdempotencyKey = request.headers.get(CANONICAL_IDEMPOTENCY_HEADER);
        return HttpResponse.json(createPaymentAttempt(), { status: 201 });
      }),
    );

    renderWithProviders(
      <PurchaseConfirmModal
        isOpen={true}
        onClose={vi.fn()}
        plan={createPlan()}
      />,
    );

    await screen.findByText('Checkout total');
    await user.click(screen.getByRole('button', { name: /Pay with Crypto/i }));

    await waitFor(() => {
      expect(windowOpenSpy).toHaveBeenCalledWith(
        'https://pay.cybervpn.test/invoice-001',
        '_blank',
        'noopener,noreferrer',
      );
    });

    expect(checkoutBody).toMatchObject({
      quote_session_id: '11111111-1111-1111-1111-111111111111',
    });
    expect(checkoutIdempotencyKey).toMatch(/^checkout-session-/);
    expect(orderCommitBody).toMatchObject({
      checkout_session_id: '55555555-5555-5555-5555-555555555555',
    });
    expect(paymentAttemptBody).toMatchObject({
      order_id: '66666666-6666-6666-6666-666666666666',
    });
    expect(paymentAttemptIdempotencyKey).toMatch(/^payment-attempt-/);
  });
});
