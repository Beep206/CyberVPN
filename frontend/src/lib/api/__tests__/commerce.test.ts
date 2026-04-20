import { afterEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import {
  commerceApi,
  createClientIdempotencyKey,
  OFFICIAL_WEB_STOREFRONT_KEY,
} from '../commerce';
import { server } from '@/test/mocks/server';
import { CANONICAL_IDEMPOTENCY_HEADER } from '../client';

const API_BASE = 'http://localhost:8000/api/v1';

function createQuoteSessionResponse() {
  return {
    id: '11111111-1111-1111-1111-111111111111',
    user_id: '22222222-2222-2222-2222-222222222222',
    auth_realm_id: '33333333-3333-3333-3333-333333333333',
    storefront_id: '44444444-4444-4444-4444-444444444444',
    storefront_key: OFFICIAL_WEB_STOREFRONT_KEY,
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
    quote: {
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
        effective_entitlements: {},
        invite_bundle: {},
        is_trial: false,
        addons: [],
      },
    },
    created_at: '2026-04-18T10:00:00Z',
    updated_at: '2026-04-18T10:00:00Z',
  };
}

afterEach(() => {
  server.resetHandlers();
});

describe('commerceApi', () => {
  it('creates canonical quote sessions against /quotes/', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(`${API_BASE}/quotes/`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(createQuoteSessionResponse(), { status: 201 });
      }),
    );

    const response = await commerceApi.createQuoteSession({
      storefront_key: OFFICIAL_WEB_STOREFRONT_KEY,
      plan_id: 'plan-pro-001',
      addons: [],
      promo_code: undefined,
      partner_code: undefined,
      use_wallet: 0,
      currency: 'USD',
      channel: 'web',
    });

    expect(response.status).toBe(201);
    expect(response.data.storefront_key).toBe(OFFICIAL_WEB_STOREFRONT_KEY);
    expect(capturedBody).toMatchObject({
      storefront_key: OFFICIAL_WEB_STOREFRONT_KEY,
      plan_id: 'plan-pro-001',
      channel: 'web',
    });
  });

  it('sends idempotency key when creating checkout sessions', async () => {
    let capturedIdempotencyKey: string | null = null;

    server.use(
      http.post(`${API_BASE}/checkout-sessions/`, ({ request }) => {
        capturedIdempotencyKey = request.headers.get(CANONICAL_IDEMPOTENCY_HEADER);
        return HttpResponse.json({
          ...createQuoteSessionResponse(),
          id: '55555555-5555-5555-5555-555555555555',
          quote_session_id: '11111111-1111-1111-1111-111111111111',
          idempotency_key: 'checkout-session-1',
        }, { status: 201 });
      }),
    );

    const idempotencyKey = createClientIdempotencyKey('checkout-session');
    const response = await commerceApi.createCheckoutSession(
      { quote_session_id: '11111111-1111-1111-1111-111111111111' },
      idempotencyKey,
    );

    expect(response.status).toBe(201);
    expect(capturedIdempotencyKey).toBe(idempotencyKey);
  });

  it('sends idempotency key when creating payment attempts', async () => {
    let capturedIdempotencyKey: string | null = null;

    server.use(
      http.post(`${API_BASE}/payment-attempts/`, ({ request }) => {
        capturedIdempotencyKey = request.headers.get(CANONICAL_IDEMPOTENCY_HEADER);
        return HttpResponse.json({
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
          idempotency_key: 'payment-attempt-1',
          provider_snapshot: {},
          request_snapshot: {},
          invoice: null,
          terminal_at: null,
          created_at: '2026-04-18T10:03:00Z',
          updated_at: '2026-04-18T10:03:00Z',
        }, { status: 201 });
      }),
    );

    const idempotencyKey = createClientIdempotencyKey('payment-attempt');
    const response = await commerceApi.createPaymentAttempt(
      { order_id: '66666666-6666-6666-6666-666666666666' },
      idempotencyKey,
    );

    expect(response.status).toBe(201);
    expect(capturedIdempotencyKey).toBe(idempotencyKey);
  });
});
